"""Persistence for the Webnovel Style Profile and the author's Directive Book.

Both are singleton cards on the *original* project (the one the novel is written
into), next to the Story Charter. Card storage keeps them visible and editable in
the Novel Bible and gives them server-side revision history for free.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.db.models import Card, CardType
from app.schemas.card import CardCreate
from app.schemas.webnovel import WEBNOVEL_STYLE_VERSION, AuthorDirective, DirectiveBook, WebnovelStyleProfile
from app.services.forge.webnovel.detect import detect_profile
from app.services.forge.webnovel.render import directives_for, render_directives

STYLE_TYPE = "Webnovel Style Profile"
STYLE_TITLE = "Webnovel Style Profile"
DIRECTIVE_TYPE = "Author Directives"
DIRECTIVE_TITLE = "Author Directives"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _content(card: Optional[Card]) -> Dict[str, Any]:
    return card.content if card is not None and isinstance(card.content, dict) else {}


class _SingletonCardStore:
    type_name: str = ""
    title: str = ""

    def __init__(self, session: Session):
        self.session = session

    def _type(self) -> Optional[CardType]:
        return self.session.exec(select(CardType).where(CardType.name == self.type_name)).first()

    def card(self, project_id: int) -> Optional[Card]:
        ct = self._type()
        if ct is None:
            return None
        return self.session.exec(select(Card).where(Card.project_id == project_id, Card.card_type_id == ct.id).order_by(Card.id)).first()

    def _write(self, project_id: int, payload: Dict[str, Any], *, commit: bool, reason: str) -> Card:
        from app.services import revision_service
        from app.services.card_service import CardService

        card = self.card(project_id)
        if card is None:
            ct = self._type()
            if ct is None:
                raise ValueError(f"Card type not found: {self.type_name}")
            card = CardService(self.session).create(CardCreate(title=self.title, content=payload, card_type_id=ct.id, parent_id=None), project_id, commit=False)
        else:
            try:
                revision_service.snapshot_before_overwrite(self.session, card, reason=reason, actor="ai" if reason.startswith("auto") else "user", new_content=payload)
            except Exception as exc:  # noqa: BLE001 - history is best effort
                logger.warning(f"[Webnovel] revision snapshot skipped for {self.type_name}: {exc}")
            card.content = payload
            flag_modified(card, "content")
            self.session.add(card)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return card


class WebnovelStyleService(_SingletonCardStore):
    type_name = STYLE_TYPE
    title = STYLE_TITLE

    def get(self, project_id: int) -> Optional[WebnovelStyleProfile]:
        card = self.card(project_id)
        if card is None:
            return None
        try:
            return WebnovelStyleProfile.model_validate(_content(card))
        except Exception as exc:  # corrupted content must never break generation
            logger.warning(f"[Webnovel] project {project_id}: invalid style profile ({exc}); ignoring")
            return None

    def save(self, project_id: int, profile: WebnovelStyleProfile, *, commit: bool = True, reason: str = "style_profile_edit") -> Card:
        profile.version = WEBNOVEL_STYLE_VERSION
        profile.updated_at = _now()
        return self._write(project_id, profile.model_dump(mode="json"), commit=commit, reason=reason)

    def ensure(self, project_id: int, *, options: Optional[Dict[str, Any]] = None, brief: str = "", fingerprint: Optional[Dict[str, Any]] = None, source_scene_functions: Iterable[str] = (), source_genre_hint: str = "", words_per_chapter: Optional[int] = None, commit: bool = True) -> WebnovelStyleProfile:
        """Return the stored profile, or detect + persist one exactly once (an author-edited profile always wins)."""
        existing = self.get(project_id)
        if existing is not None:
            return existing
        profile = detect_profile(options=options, brief=brief, fingerprint=fingerprint, source_scene_functions=list(source_scene_functions), source_genre_hint=source_genre_hint, words_per_chapter=words_per_chapter)
        self.save(project_id, profile, commit=commit, reason="auto_detect")
        return profile

    def get_or_default(self, project_id: int) -> WebnovelStyleProfile:
        return self.get(project_id) or detect_profile()


class DirectiveService(_SingletonCardStore):
    type_name = DIRECTIVE_TYPE
    title = DIRECTIVE_TITLE

    def book(self, project_id: int) -> DirectiveBook:
        card = self.card(project_id)
        if card is None:
            return DirectiveBook()
        try:
            return DirectiveBook.model_validate(_content(card))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Webnovel] project {project_id}: invalid directive book ({exc}); treating as empty")
            return DirectiveBook()

    def save(self, project_id: int, book: DirectiveBook, *, commit: bool = True) -> Card:
        book.version = WEBNOVEL_STYLE_VERSION
        book.updated_at = _now()
        used = set()
        n = 0
        for d in book.directives:
            if not d.id or d.id in used:
                n += 1
                while f"dir-{n}" in used:
                    n += 1
                d.id = f"dir-{n}"
            used.add(d.id)
            if not d.created_at:
                d.created_at = _now()
        return self._write(project_id, book.model_dump(mode="json"), commit=commit, reason="directives_edit")

    def add(self, project_id: int, directive: AuthorDirective, *, commit: bool = True) -> AuthorDirective:
        book = self.book(project_id)
        directive.id = ""
        book.directives.append(directive)
        self.save(project_id, book, commit=commit)
        return book.directives[-1]

    def update(self, project_id: int, directive_id: str, patch: Dict[str, Any], *, commit: bool = True) -> Optional[AuthorDirective]:
        book = self.book(project_id)
        for i, d in enumerate(book.directives):
            if d.id == directive_id:
                data = d.model_dump()
                data.update({k: v for k, v in patch.items() if k in AuthorDirective.model_fields and k not in ("id", "created_at", "consumed_by_chapters")})
                book.directives[i] = AuthorDirective.model_validate(data)
                self.save(project_id, book, commit=commit)
                return book.directives[i]
        return None

    def remove(self, project_id: int, directive_id: str, *, commit: bool = True) -> bool:
        book = self.book(project_id)
        before = len(book.directives)
        book.directives = [d for d in book.directives if d.id != directive_id]
        if len(book.directives) == before:
            return False
        self.save(project_id, book, commit=commit)
        return True

    def for_chapter(self, project_id: int, chapter: int, *, consumer: str = "drafting") -> List[AuthorDirective]:
        return directives_for(self.book(project_id).directives, chapter=chapter, consumer=consumer)

    def render(self, project_id: int, *, chapter: Optional[int] = None, consumer: str = "drafting", max_chars: int = 2400) -> str:
        return render_directives(self.book(project_id).directives, chapter=chapter, consumer=consumer, max_chars=max_chars)

    def mark_consumed(self, project_id: int, chapter: int, *, commit: bool = True) -> int:
        """Record that chapter ``chapter``'s draft received the directives that applied to it."""
        book = self.book(project_id)
        changed = 0
        for d in directives_for(book.directives, chapter=chapter, consumer="drafting"):
            if chapter not in d.consumed_by_chapters:
                d.consumed_by_chapters.append(chapter)
                changed += 1
        if changed:
            self.save(project_id, book, commit=commit)
        return changed


__all__ = ["DIRECTIVE_TITLE", "DIRECTIVE_TYPE", "STYLE_TITLE", "STYLE_TYPE", "DirectiveService", "WebnovelStyleService"]
