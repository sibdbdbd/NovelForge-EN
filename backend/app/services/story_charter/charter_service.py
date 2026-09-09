"""Story Charter persistence, seeding, rendering and conflict checks.

Storage: one ``Story Charter`` card per project (singleton card type, no
migration). The card is the single source of truth for author requirements;
``AutonomousNovelJob.options`` only seeds it once and is never read again by
generation after the charter exists.

Rendering (``render_charter``) is deterministic and scope-aware so each prompt
receives only what applies to it, with fixed requirements, preferences, open
choices and boundaries in clearly labelled blocks. Interpretation of a
free-text brief is the only model call in this module and is optional.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from loguru import logger
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.db.models import Card, CardType
from app.schemas.card import CardCreate
from app.schemas.story_charter import (
    STORY_CHARTER_VERSION,
    CharterCheckReport,
    CharterConflict,
    CharterInterpretation,
    CharterRequirement,
    CharterSummary,
    OpenChoice,
    ReferenceUsage,
    StoryCharter,
)

CHARTER_TYPE = "Story Charter"
CHARTER_TITLE = "Story Charter"
INTERPRET_PROMPT_NAME = "Story Charter Interpretation"
INTERPRET_PROMPT_VERSION = "story-charter-interpret-1"

# Which charter scopes each prompt consumer cares about (besides whole_novel). Drafting and review
# also see planning-scope entries: a "no romance" or "the antagonist is never redeemed" rule is
# broken in prose, not only in plans.
CONSUMER_SCOPES: Dict[str, Sequence[str]] = {
    "storylines": ("planning", "characters", "world", "ending", "structure"),
    "architecture": ("planning", "characters", "world", "ending", "structure", "relationships"),
    "chapter_plan": ("planning", "structure", "pacing", "chapter", "ending"),
    "draft": ("prose", "chapter", "characters", "planning", "world"),
    "review": ("prose", "chapter", "characters", "planning", "ending"),
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()[:16]


def _content(card: Optional[Card]) -> Dict[str, Any]:
    return card.content if card is not None and isinstance(card.content, dict) else {}


def _next_id(prefix: str, existing: Iterable[str]) -> str:
    used = set(existing)
    n = 1
    while f"{prefix}-{n}" in used:
        n += 1
    return f"{prefix}-{n}"


# --------------------------------------------------------------------- seeding

_PREF_LABELS = {
    "genre": ("premise", "Genre: {v}", "must", "whole_novel"),
    "tags": ("premise", "Tropes / tags the novel must deliver: {v}", "must", "planning"),
    "genre_intensity": ("tone", "Genre intensity: {v}", "prefer", "prose"),
    "content_rating": ("content", "Content rating: {v}", "must", "whole_novel"),
    "romance_level": ("romance", "Romance: {v}", "must", "planning"),
    "ending_preference": ("ending", "Ending: {v}", "must", "ending"),
    "protagonist_name": ("protagonist", "The protagonist is named {v}", "must", "characters"),
    "title": ("premise", "Working title: {v}", "prefer", "whole_novel"),
}


def charter_from_job_options(options: Dict[str, Any], *, reference_title: str = "", job_id: Optional[int] = None) -> StoryCharter:
    """Seed a charter from the Create Novel form. Only fields the author actually filled in become entries."""
    opts = {k: v for k, v in (options or {}).items() if v not in (None, "", [], {})}
    charter = StoryCharter(
        working_title=str(opts.get("title") or ""),
        brief=str(opts.get("summary") or "").strip(),
        target_chapters=int(opts["target_chapters"]) if str(opts.get("target_chapters") or "").isdigit() else None,
        words_per_chapter=int(opts["words_per_chapter"]) if str(opts.get("words_per_chapter") or "").isdigit() else None,
        source_job_id=job_id,
        updated_at=_now(),
    )
    reqs: List[CharterRequirement] = []
    for key, (category, template, strength, scope) in _PREF_LABELS.items():
        val = opts.get(key)
        if val in (None, "", "no preference"):
            continue
        if key == "title":
            continue  # working_title already carries it
        if key == "romance_level" and str(val).lower() == "none":
            reqs.append(CharterRequirement(id=_next_id("req", (r.id for r in reqs)), text="No romance plot", category="romance", strength="must", scope="planning", source="author"))
            continue
        reqs.append(CharterRequirement(id=_next_id("req", (r.id for r in reqs)), text=template.format(v=val), category=category, strength=strength, scope=scope, source="author"))
    notes = str(opts.get("notes") or "").strip()
    if notes:
        reqs.append(CharterRequirement(id=_next_id("req", (r.id for r in reqs)), text=notes[:600], category="other", strength="must", scope="whole_novel", source="author"))
    charter.requirements = reqs
    # Deliberately open: anything the form offers that the author left blank.
    open_topics = {"ending_preference": "the kind of ending", "romance_level": "whether there is a romance plot", "protagonist_name": "the protagonist's name"}
    for key, topic in open_topics.items():
        if opts.get(key) in (None, "", "no preference"):
            charter.open_choices.append(OpenChoice(id=_next_id("open", (o.id for o in charter.open_choices)), topic=topic, decide_by="planner", guidance="Choose what best serves the premise; keep it consistent once chosen.", source="interpreted"))
    if reference_title or opts.get("similarity_to_original"):
        sim = str(opts.get("similarity_to_original") or "moderate")
        charter.reference = ReferenceUsage(reference_title=reference_title, similarity=sim if sim in ("loose", "moderate", "close") else "moderate", learn=["momentum and chapter-ending hooks", "reward cadence and progression rhythm", "structure and emotional pacing"], never_reuse=["names", "settings", "scenes", "distinctive objects", "phrasing"])
    return charter


# ------------------------------------------------------------------- rendering

def render_charter(charter: Optional[StoryCharter], *, consumer: str = "draft", max_chars: int = 3500, include_brief: bool = True) -> str:
    """Prompt-ready block. Deterministic; empty string when there is nothing to say."""
    if charter is None or charter.is_empty():
        return ""
    scopes = set(CONSUMER_SCOPES.get(consumer, ())) | {"whole_novel"}
    lines: List[str] = []
    head = []
    if charter.working_title:
        head.append(f"title: {charter.working_title}")
    if charter.one_line_pitch:
        head.append(f"pitch: {charter.one_line_pitch}")
    if charter.audience:
        head.append(f"audience: {charter.audience}")
    if charter.target_chapters:
        head.append(f"planned length: ~{charter.target_chapters} chapters" + (f" × ~{charter.words_per_chapter} words" if charter.words_per_chapter else ""))
    if head:
        lines.append(" | ".join(head))
    if include_brief and charter.brief.strip() and consumer in ("storylines", "architecture", "chapter_plan", "interpret"):
        lines.append("Author's brief (verbatim):\n" + charter.brief.strip()[:1800])
    musts = [r for r in charter.requirements if r.strength == "must" and r.scope in scopes]
    prefers = [r for r in charter.requirements if r.strength == "prefer" and r.scope in scopes]
    if musts:
        lines.append("FIXED REQUIREMENTS (non-negotiable; every plan and chapter must honour them):\n" + "\n".join(f"- [{r.id}] {r.text}" for r in musts))
    if prefers:
        lines.append("PREFERENCES (follow unless a fixed requirement or established canon conflicts):\n" + "\n".join(f"- [{r.id}] {r.text}" for r in prefers))
    if charter.open_choices:
        oc = []
        for o in charter.open_choices:
            who = {"author": "only the author may settle this", "planner": "the planner may settle this during architecture", "either": "may be settled if the story needs it"}[o.decide_by]
            opt = f" (acceptable: {'; '.join(o.options)})" if o.options else ""
            oc.append(f"- [{o.id}] {o.topic}{opt} — {who}." + (f" {o.guidance}" if o.guidance else ""))
        title = "OPEN CHOICES (left undecided on purpose; do not turn them into permanent facts unless allowed):"
        if consumer in ("draft", "review"):
            title = "OPEN CHOICES (the author has not decided these; keep them open — no permanent facts, backstory or reveals that settle them):"
        lines.append(title + "\n" + "\n".join(oc))
    if charter.boundaries:
        lines.append("NEVER (content boundaries):\n" + "\n".join(f"- [{b.id}] {b.text}" + (" (soft)" if b.severity == "soft" else "") for b in charter.boundaries))
    if charter.reference and consumer in ("storylines", "architecture", "chapter_plan"):
        r = charter.reference
        lines.append(f"REFERENCE USE: learn {', '.join(r.learn) or 'structure and rhythm'} at '{r.similarity}' similarity; never reuse {', '.join(r.never_reuse) or 'any content'}.")
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


# --------------------------------------------------------------------- service

class CharterService:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------ persistence
    def _type(self) -> Optional[CardType]:
        return self.session.exec(select(CardType).where(CardType.name == CHARTER_TYPE)).first()

    def card(self, project_id: int) -> Optional[Card]:
        ct = self._type()
        if ct is None:
            return None
        return self.session.exec(select(Card).where(Card.project_id == project_id, Card.card_type_id == ct.id).order_by(Card.id)).first()

    def get(self, project_id: int) -> Optional[StoryCharter]:
        card = self.card(project_id)
        if card is None:
            return None
        try:
            return StoryCharter.model_validate(_content(card))
        except Exception as exc:  # corrupted content must never break generation
            logger.warning(f"[Charter] project {project_id}: invalid charter content ({exc}); treating as empty")
            return None

    def save(self, project_id: int, charter: StoryCharter, *, commit: bool = True) -> Card:
        from app.services.card_service import CardService

        charter.version = STORY_CHARTER_VERSION
        charter.updated_at = _now()
        self._assign_ids(charter)
        payload = charter.model_dump(mode="json")
        card = self.card(project_id)
        if card is None:
            ct = self._type()
            if ct is None:
                raise ValueError(f"Card type not found: {CHARTER_TYPE}")
            card = CardService(self.session).create(CardCreate(title=CHARTER_TITLE, content=payload, card_type_id=ct.id, parent_id=None), project_id, commit=False)
        else:
            card.content = payload
            flag_modified(card, "content")
            self.session.add(card)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return card

    @staticmethod
    def _assign_ids(charter: StoryCharter) -> None:
        for prefix, items in (("req", charter.requirements), ("open", charter.open_choices), ("no", charter.boundaries)):
            seen: List[str] = []
            for it in items:
                if not it.id or it.id in seen:
                    it.id = _next_id(prefix, seen)
                seen.append(it.id)

    def ensure_from_job(self, project_id: int, options: Dict[str, Any], *, reference_title: str = "", job_id: Optional[int] = None) -> StoryCharter:
        """Seed the charter from job options once; an existing charter is authoritative and left untouched."""
        existing = self.get(project_id)
        if existing is not None and not existing.is_empty():
            return existing
        charter = charter_from_job_options(options, reference_title=reference_title, job_id=job_id)
        self.save(project_id, charter, commit=False)
        return charter

    def summary(self, project_id: int) -> CharterSummary:
        c = self.get(project_id)
        if c is None:
            return CharterSummary(project_id=project_id, exists=False)
        cats: Dict[str, int] = {}
        for r in c.requirements:
            cats[r.category] = cats.get(r.category, 0) + 1
        return CharterSummary(
            project_id=project_id, exists=True, working_title=c.working_title, one_line_pitch=c.one_line_pitch,
            musts=len(c.musts()), prefers=len(c.prefers()), open_choices=len(c.open_choices), boundaries=len(c.boundaries),
            interpreted=bool(c.interpreted_at), brief_changed_since_interpretation=bool(c.interpreted_at) and _hash(c.brief) != c.interpreted_brief_hash,
            questions_for_author=list(c.questions_for_author), categories=cats,
        )

    def render(self, project_id: int, *, consumer: str, max_chars: int = 3500) -> str:
        return render_charter(self.get(project_id), consumer=consumer, max_chars=max_chars)

    # ---------------------------------------------------------- interpretation
    async def interpret(self, project_id: int, *, llm_config_id: int, brief: Optional[str] = None, replace_interpreted: bool = True) -> StoryCharter:
        """Turn the free-text brief into structured entries. Author-authored entries are never touched."""
        from app.services import prompt_service
        from app.services.ai.core import llm_service
        from app.utils.schema_utils import filter_schema_for_ai

        charter = self.get(project_id) or StoryCharter()
        if brief is not None:
            charter.brief = brief.strip()
        if not charter.brief.strip():
            raise ValueError("The charter has no brief to interpret")
        prompt = prompt_service.get_prompt_by_name(self.session, INTERPRET_PROMPT_NAME)
        if prompt is None or not prompt.template:
            raise ValueError(f"Prompt '{INTERPRET_PROMPT_NAME}' is missing; it is a required runtime dependency")
        schema = filter_schema_for_ai(CharterInterpretation.model_json_schema())
        system_prompt = prompt_service.inject_knowledge(self.session, str(prompt.template)) + "\n\nReturn ONLY one JSON object that validates against this schema:\n" + json.dumps(schema, ensure_ascii=False)
        author_entries = [r for r in charter.requirements if r.source == "author"] + [o for o in charter.open_choices if o.source == "author"] + [b for b in charter.boundaries if b.source == "author"]
        user_prompt = "\n".join([
            "[AUTHOR'S BRIEF]", charter.brief.strip(),
            "", "[ALREADY FIXED BY THE AUTHOR — do not restate these; only add what the brief adds]",
            "\n".join(f"- {getattr(e, 'text', None) or getattr(e, 'topic', '')}" for e in author_entries) or "(none)",
            "", f"[PLANNED LENGTH] {charter.target_chapters or 'undecided'} chapters" + (f", ~{charter.words_per_chapter} words each" if charter.words_per_chapter else ""),
        ])
        result = await llm_service.generate_structured(session=self.session, llm_config_id=int(llm_config_id), user_prompt=user_prompt, output_type=CharterInterpretation, system_prompt=system_prompt, temperature=0.2)
        interp = result if isinstance(result, CharterInterpretation) else CharterInterpretation.model_validate(result)
        return self.apply_interpretation(project_id, charter, interp, replace_interpreted=replace_interpreted)

    def apply_interpretation(self, project_id: int, charter: StoryCharter, interp: CharterInterpretation, *, replace_interpreted: bool = True) -> StoryCharter:
        """Merge model output: interpreted entries may be replaced, author entries are kept verbatim."""
        if replace_interpreted:
            charter.requirements = [r for r in charter.requirements if r.source == "author"]
            charter.open_choices = [o for o in charter.open_choices if o.source == "author"]
            charter.boundaries = [b for b in charter.boundaries if b.source == "author"]
        known_texts = {_norm(r.text) for r in charter.requirements}
        for r in interp.requirements:
            if _norm(r.text) in known_texts or not r.text.strip():
                continue
            r.source = "interpreted"
            r.locked = False
            r.id = _next_id("req", (x.id for x in charter.requirements))
            charter.requirements.append(r)
            known_texts.add(_norm(r.text))
        known_topics = {_norm(o.topic) for o in charter.open_choices}
        for o in interp.open_choices:
            if _norm(o.topic) in known_topics or not o.topic.strip():
                continue
            o.source = "interpreted"
            o.id = _next_id("open", (x.id for x in charter.open_choices))
            charter.open_choices.append(o)
            known_topics.add(_norm(o.topic))
        known_b = {_norm(b.text) for b in charter.boundaries}
        for b in interp.boundaries:
            if _norm(b.text) in known_b or not b.text.strip():
                continue
            b.source = "interpreted"
            b.id = _next_id("no", (x.id for x in charter.boundaries))
            charter.boundaries.append(b)
            known_b.add(_norm(b.text))
        if interp.working_title and not charter.working_title:
            charter.working_title = interp.working_title
        if interp.one_line_pitch:
            charter.one_line_pitch = interp.one_line_pitch
        charter.questions_for_author = list(interp.questions_for_author)[:5]
        charter.interpretation_notes = interp.interpretation_thinking.strip()
        charter.interpreted_at = _now()
        charter.interpreted_brief_hash = _hash(charter.brief)
        self.save(project_id, charter)
        return charter

    # ------------------------------------------------------------------ checks
    def check_text(self, project_id: int, text: str, *, chapter_number: Optional[int] = None) -> CharterCheckReport:
        """Deterministic conflict scan: hard boundaries and 'never'/'no' requirements whose key terms appear in the text."""
        charter = self.get(project_id)
        report = CharterCheckReport(project_id=project_id, chapter_number=chapter_number)
        if charter is None:
            return report
        low = (text or "").lower()
        checked = 0
        for b in charter.boundaries:
            checked += 1
            hit = _find_terms(low, b.text)
            if hit:
                report.conflicts.append(CharterConflict(entry_id=b.id, entry_text=b.text, kind="boundary", message=f"Boundary '{b.text}' may be violated: found {', '.join(repr(h) for h in hit[:3])}", severity="critical" if b.severity == "hard" else "medium", span=_span(low, hit[0]), evidence=hit[0]))
        for r in charter.requirements:
            neg = _negated_subject(r.text)
            if not neg:
                continue
            checked += 1
            hit = _find_terms(low, neg)
            if hit:
                report.conflicts.append(CharterConflict(entry_id=r.id, entry_text=r.text, kind="requirement", message=f"Requirement '{r.text}' excludes this, but the text mentions {', '.join(repr(h) for h in hit[:3])}", severity="high" if r.strength == "must" else "low", span=_span(low, hit[0]), evidence=hit[0]))
        report.checked_entries = checked
        if any(c.severity == "critical" for c in report.conflicts):
            report.verdict = "block"
        elif report.conflicts:
            report.verdict = "review"
        return report


# ------------------------------------------------------------------- helpers

_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "no", "not", "never", "any", "with", "without", "for", "is", "are", "be", "should", "must", "avoid", "plot", "content", "scenes", "scene", "explicit", "graphic", "detailed", "depiction", "depictions", "kind", "sort", "at", "all"}


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _negated_subject(text: str) -> str:
    """'No romance plot' -> 'romance'; 'Never kill the dog' -> 'kill the dog'; '' when not a negation."""
    m = re.match(r"^\s*(?:no|never|avoid|without|do not|don't|must not|never include)\b\s*(.+)$", text.strip(), flags=re.I)
    return m.group(1).strip() if m else ""


def _terms(phrase: str) -> List[str]:
    return [t for t in re.findall(r"[a-z][a-z'\-]{2,}", phrase.lower()) if t not in _STOP]


def _stem(t: str) -> str:
    """Tiny English stemmer for matching (triangles -> triangle, kisses -> kiss, killed -> kill)."""
    for suf in ("ings", "ing", "ies", "sses", "ses", "es", "ed", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            base = t[: -len(suf)]
            return base + ("y" if suf == "ies" else "s" if suf in ("sses", "ses") else "")
    return t


def _term_rx(term: str) -> str:
    return rf"\b{re.escape(_stem(term))}[a-z]{{0,3}}\b"


def _find_terms(low_text: str, phrase: str) -> List[str]:
    """Words of the phrase (minus stop words) that appear in the text (stem-tolerant); all must appear when the phrase has ≤ 2 terms."""
    terms = _terms(phrase)
    if not terms:
        return []
    hits = [t for t in terms if re.search(_term_rx(t), low_text)]
    if len(terms) <= 2:
        return hits if len(hits) == len(terms) else []
    return hits if len(hits) >= max(2, (len(terms) + 1) // 2) else []


def _span(low_text: str, term: str) -> Optional[List[int]]:
    m = re.search(_term_rx(term), low_text)
    return [m.start(), m.end()] if m else None


__all__ = ["CHARTER_TITLE", "CHARTER_TYPE", "CONSUMER_SCOPES", "CharterService", "INTERPRET_PROMPT_NAME", "INTERPRET_PROMPT_VERSION", "charter_from_job_options", "render_charter"]
