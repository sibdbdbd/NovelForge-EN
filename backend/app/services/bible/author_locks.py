"""Author locks: fields the system may never rewrite on a Bible card.

A card's ``content["author_locks"]`` lists field names (or ``"*"`` for the whole
card) the author has marked as their decision. Automatic writers — post-chapter
sync, architecture re-runs, autonomous rebuilds — must call ``guard`` before
writing so an author's edit is never silently replaced by generated data. The
author's own edits and the review-and-accept path of the Living Bible are not
subject to locks: they *are* the author deciding.

Locked writes are not errors: the writer records what it wanted to change on
the card's ``suppressed_updates`` list so the author can see the disagreement
and decide.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

LOCKS_KEY = "author_locks"
SUPPRESSED_KEY = "suppressed_updates"
ALL = "*"
MAX_SUPPRESSED = 40


def locks_of(content: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(content, dict):
        return []
    raw = content.get(LOCKS_KEY)
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if str(x).strip()]


def is_locked(content: Optional[Dict[str, Any]], field: str) -> bool:
    locks = locks_of(content)
    if not locks:
        return False
    if ALL in locks:
        return True
    top = str(field).split(".")[0]
    return field in locks or top in locks


def set_locks(content: Dict[str, Any], fields: Iterable[str]) -> Dict[str, Any]:
    content[LOCKS_KEY] = sorted({str(f) for f in fields if str(f).strip()})
    if not content[LOCKS_KEY]:
        content.pop(LOCKS_KEY, None)
    return content


def guard(content: Dict[str, Any], updates: Dict[str, Any], *, source: str, chapter_number: Optional[int] = None, reason: str = "") -> Dict[str, Any]:
    """Return the subset of ``updates`` allowed by the card's locks; record the rest on the card.

    ``content`` is mutated only to append suppressed entries. The caller applies the returned dict.
    """
    if not locks_of(content):
        return dict(updates)
    allowed: Dict[str, Any] = {}
    suppressed: List[Dict[str, Any]] = list(content.get(SUPPRESSED_KEY) or [])
    now = datetime.now().isoformat(timespec="seconds")
    for field, value in updates.items():
        if field in (LOCKS_KEY, SUPPRESSED_KEY):
            continue
        if is_locked(content, field):
            if content.get(field) != value:
                suppressed.append({"field": field, "proposed": value, "current": content.get(field), "source": source, "chapter_number": chapter_number, "reason": reason, "at": now})
        else:
            allowed[field] = value
    if suppressed:
        content[SUPPRESSED_KEY] = suppressed[-MAX_SUPPRESSED:]
    return allowed


def merge_guarded(existing: Dict[str, Any], incoming: Dict[str, Any], *, source: str, reason: str = "") -> Dict[str, Any]:
    """Whole-card replacement that respects locks: locked fields keep their current value."""
    if not locks_of(existing):
        return dict(incoming)
    allowed = guard(existing, incoming, source=source, reason=reason)
    merged = dict(incoming)
    for field in locks_of(existing):
        if field == ALL:
            merged = {**incoming, **{k: v for k, v in existing.items() if k not in (SUPPRESSED_KEY,)}}
            break
        if field in existing:
            merged[field] = existing[field]
    for k in (LOCKS_KEY, SUPPRESSED_KEY):
        if k in existing:
            merged[k] = existing[k]
    merged.update({k: v for k, v in allowed.items() if k not in locks_of(existing)})
    return merged


__all__ = ["ALL", "LOCKS_KEY", "SUPPRESSED_KEY", "guard", "is_locked", "locks_of", "merge_guarded", "set_locks"]
