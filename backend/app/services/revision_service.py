"""Card revision snapshots: never lose the previous text.

``snapshot_before_overwrite`` is called by every path that replaces a card's
content — the editor's PUT, the Forge pipeline commit/regenerate, global
repair, Bible sync, Living Bible accept — *before* the new content is written.
It is a no-op when the content is unchanged, so saving without edits does not
spam history. History is bounded per card and oldest entries are pruned.

``restore`` writes an old snapshot back as the current content, taking a
snapshot of the present content first (a restore is itself undoable).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import Card, CardRevision

TEXT_TYPES = ("Chapter Text",)


def content_hash(content: Any) -> str:
    try:
        payload = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        payload = str(content)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _word_count(content: Any) -> int:
    if isinstance(content, dict):
        text = content.get("content")
        if isinstance(text, str):
            return len(text.split())
    return 0


def _chapter_number(content: Any) -> Optional[int]:
    if isinstance(content, dict):
        try:
            n = int(content.get("chapter_number") or 0)
            return n or None
        except (TypeError, ValueError):
            return None
    return None


def snapshot_before_overwrite(session: Session, card: Card, *, reason: str, actor: str = "user", note: Optional[str] = None, new_content: Any = None, flush: bool = True) -> Optional[CardRevision]:
    """Record the card's *current* content. Returns None when disabled, empty, or unchanged vs ``new_content``."""
    limit = int(settings.data_safety.max_revisions_per_card)
    if limit <= 0 or card is None or card.id is None:
        return None
    current = card.content
    if current in (None, {}, ""):
        return None
    current_hash = content_hash(current)
    if new_content is not None and content_hash(new_content) == current_hash:
        return None
    latest = session.exec(select(CardRevision).where(CardRevision.card_id == card.id).order_by(CardRevision.id.desc())).first()
    if latest is not None and latest.content_hash == current_hash:
        return None  # already captured (e.g. two overwrites in a row without a change in between)
    type_name = getattr(getattr(card, "card_type", None), "name", "") or ""
    rev = CardRevision(
        card_id=int(card.id), project_id=int(card.project_id), card_type_name=type_name, title=card.title or "", content=current, content_hash=current_hash,
        reason=reason, actor=actor, chapter_number=_chapter_number(current), word_count=_word_count(current), note=note, created_at=datetime.now(),
    )
    session.add(rev)
    if flush:
        session.flush()
    prune(session, int(card.id), keep=limit)
    return rev


def prune(session: Session, card_id: int, *, keep: int) -> int:
    rows = session.exec(select(CardRevision).where(CardRevision.card_id == card_id).order_by(CardRevision.id.desc())).all()
    extra = rows[keep:] if keep > 0 else rows
    for r in extra:
        session.delete(r)
    return len(extra)


def list_revisions(session: Session, card_id: int, *, limit: int = 50) -> List[CardRevision]:
    return list(session.exec(select(CardRevision).where(CardRevision.card_id == card_id).order_by(CardRevision.id.desc()).limit(max(1, min(limit, 200)))).all())


def restore(session: Session, card: Card, revision: CardRevision, *, actor: str = "user") -> Card:
    """Make ``revision`` the current content; the content being replaced is snapshotted first."""
    if revision.card_id != card.id:
        raise ValueError("Revision does not belong to this card")
    snapshot_before_overwrite(session, card, reason="restore", actor=actor, note=f"before restoring revision {revision.id}", new_content=revision.content)
    card.content = revision.content
    flag_modified(card, "content")
    card.last_modified_by = actor
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def revision_dict(r: CardRevision, *, include_content: bool = False) -> Dict[str, Any]:
    d = {
        "id": r.id, "card_id": r.card_id, "project_id": r.project_id, "card_type_name": r.card_type_name, "title": r.title, "content_hash": r.content_hash, "reason": r.reason, "actor": r.actor,
        "chapter_number": r.chapter_number, "word_count": r.word_count, "note": r.note, "created_at": r.created_at.isoformat() if r.created_at else None,
    }
    if include_content:
        d["content"] = r.content
    return d


__all__ = ["TEXT_TYPES", "content_hash", "list_revisions", "prune", "restore", "revision_dict", "snapshot_before_overwrite"]
