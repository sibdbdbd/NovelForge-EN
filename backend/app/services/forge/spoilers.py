"""Spoiler detection: does a chapter draft *state* a prohibited fact or future outcome?

This replaces three copies of the same brittle heuristic (``validate_outline``,
``validate_pov`` and the Story Memory continuity guard) that flagged a sentence
as a critical spoiler when any two stop-word-filtered tokens of a future beat
appeared within a two-sentence window. In a 400-chapter novel the compiler fed
those functions ~2,000 future beats, so ordinary vocabulary ("gold", "supply")
became unusable in chapter 1 and the repair editor looped until it exhausted its
budget.

Design
------
A prohibited statement is decomposed into *anchors* (the proper names it is
about, one group of tokens per name) and *content* terms (what it asserts).
A draft position is a match only when it reproduces the **proposition**:

* every anchor group is represented (some token of each name — "Corvin" for
  "Corvin Ashe"), either in the sentence or, when the sentence opens with a
  subject pronoun (*He was the courier*), in the sentence before it;
* the content terms co-occur: **all** of them for statements with fewer than
  four, at least ``ceil(0.75 * n)`` (floor three) otherwise;
* short statements (fewer than three content terms) must be reproduced within a
  single sentence; longer ones may span two consecutive sentences, since a
  reveal is often a build-up followed by the blow.

Matching is inflection-tolerant through the shared light stemmer (``forges`` ~
``forging``, ``revealed`` ~ ``reveals``) but never prefix-based (``gold`` is not
``golden``), and questions are excluded (a POV *wondering* is suspense).

Confidence
----------
``high`` when the proposition is anchored and carries at least two specific
terms, when three or more specific terms co-occur, or when a short statement is
reproduced as a **copular identity** (*Corvin was the courier*, *he had always
been the courier*) — the canonical shape of a reveal. Everything else is
``medium``. Callers map ``high`` to a blocking issue and ``medium`` to an
advisory one, so a single ambiguous overlap can never trap the repair loop.

Cost
----
The draft is tokenised once into per-sentence stem sets; each statement is then
a handful of set operations per sentence. Two thousand statements against a
3,000-word chapter take tens of milliseconds instead of ~15 s of per-term regex.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.services.forge.lexicon import STOP_WORDS, is_non_name_word, stem
from app.services.forge.textmetrics import detect_language, split_sentences

_CHAPTER_TAG_RX = re.compile(r"^\(ch\.\d+\)\s*")
_TRAILING_PAREN_RX = re.compile(r"\s*\((?:POV unaware|planned reveal|reveal planned)[^)]*\)\s*$", re.I)
_TOKEN_RX = re.compile(r"[A-Za-z][A-Za-z'’]*")
_PRONOUN_START_RX = re.compile(r"^[\s\"“'‘(\[]*(?:he|she|they|it)\b", re.I)
_COPULA = r"(?:is|was|are|were|had been|has been|had always been|has always been|turned out to be|must be|must have been|would be|became)"
_NEGATION_RX = re.compile(r"\b(?:not|never|no|neither|nor)\b|n['’]t\b", re.I)
_QUESTION_ENDINGS = ("?", "？")
WINDOW_SENTENCES = 2


def normalize_statement(statement: str) -> str:
    """Strip compiler decorations: ``(ch.12) ...`` prefixes and ``(POV unaware; reveal planned ch.18)`` suffixes."""
    s = _CHAPTER_TAG_RX.sub("", str(statement or "").strip())
    s = _TRAILING_PAREN_RX.sub("", s)
    return s.strip()


@dataclass(frozen=True)
class Statement:
    """A prohibited statement decomposed for matching."""

    raw: str
    text: str
    anchors: Tuple[Tuple[str, ...], ...]  # one group of token stems per proper name
    content: Tuple[str, ...]  # stems of the specific content terms (names excluded)

    @property
    def matchable(self) -> bool:
        """A statement needs a proposition: a name plus what is asserted about it, or two
        specific content terms. A lone topic word ("the gold") can never be a spoiler."""
        if not self.content:
            return False
        return bool(self.anchors) or len(self.content) >= 2

    def required_content(self) -> int:
        """Content terms that must all co-occur: every one for short statements, 75 % (>= 3) for long ones."""
        n = len(self.content)
        if n < 4:
            return n
        return max(3, math.ceil(0.75 * n))

    @property
    def short(self) -> bool:
        return len(self.content) < 3


def _name_tokens(names: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for n in names:
        for tok in _TOKEN_RX.findall(str(n or "")):
            t = tok.lower().split("'")[0].split("’")[0]
            if len(t) >= 2:
                out.add(t)
                out.add(stem(t))
    return out


def compile_statement(statement: str, *, participants: Iterable[str] = (), language: Optional[str] = None) -> Statement:
    """Decompose one prohibited statement into anchor groups and content stems.

    A token is part of a name when it belongs to a known participant or is
    capitalised mid-statement and not an ordinary word by the lexicon; adjacent
    name tokens form one group ("Corvin Ashe"). A capitalised *first* token that is
    not a participant is treated as content: statements are sentences, and their
    first word is capitalised for that reason alone.
    """
    text = normalize_statement(statement)
    lang = language or detect_language(text)
    if lang == "ko":
        toks = [t for t in re.split(r"\s+", text) if len(t) >= 2]
        return Statement(raw=statement, text=text, anchors=(), content=tuple(dict.fromkeys(toks)))
    participant_tokens = _name_tokens(participants)
    groups: List[Tuple[str, ...]] = []
    content: List[str] = []
    seen: Set[str] = set()
    current: List[str] = []
    for i, raw in enumerate(_TOKEN_RX.findall(text)):
        low = raw.lower().split("'")[0].split("’")[0]
        if len(low) < 2:
            current = []
            continue
        st = stem(low)
        is_name = low in participant_tokens or st in participant_tokens or (i > 0 and raw[0].isupper() and not is_non_name_word(low))
        if is_name:
            if st not in seen:
                seen.add(st)
                current.append(st)
            continue
        if current:
            groups.append(tuple(current))
            current = []
        if len(low) < 3 or low in STOP_WORDS or st in seen:
            continue
        seen.add(st)
        content.append(st)
    if current:
        groups.append(tuple(current))
    return Statement(raw=statement, text=text, anchors=tuple(groups), content=tuple(content))


@dataclass
class SentenceIndex:
    """Pre-tokenised draft: per-sentence stem sets and two-sentence windows."""

    prose: str
    sentences: List[str]
    offsets: List[int]
    sentence_stems: List[Set[str]]
    window_stems: List[Set[str]]
    pronoun_start: List[bool]
    language: str

    @classmethod
    def build(cls, prose: str, *, language: Optional[str] = None, window: int = WINDOW_SENTENCES) -> "SentenceIndex":
        lang = language or detect_language(prose)
        sents = split_sentences(prose, lang)
        offsets: List[int] = []
        pos = 0
        keep: List[str] = []
        for s in sents:
            idx = prose.find(s, pos)
            if idx < 0:
                idx = pos
            pos = idx + len(s)
            if s.rstrip().endswith(_QUESTION_ENDINGS):
                continue  # questions are suspense, never statements
            keep.append(s)
            offsets.append(idx)
        per_sentence: List[Set[str]] = []
        for s in keep:
            if lang == "ko":
                per_sentence.append({t for t in re.split(r"\s+", s) if len(t) >= 2})
            else:
                per_sentence.append({stem(t.lower().split("'")[0].split("’")[0]) for t in _TOKEN_RX.findall(s) if len(t) >= 3})
        windows: List[Set[str]] = []
        for i in range(len(keep)):
            acc: Set[str] = set()
            for j in range(i, min(len(keep), i + window)):
                acc |= per_sentence[j]
            windows.append(acc)
        pronoun = [bool(_PRONOUN_START_RX.match(s)) for s in keep]
        return cls(prose=prose, sentences=keep, offsets=offsets, sentence_stems=per_sentence, window_stems=windows, pronoun_start=pronoun, language=lang)


@dataclass
class SpoilerHit:
    statement: str
    span: Tuple[int, int]
    sentence: str
    matched: List[str] = field(default_factory=list)
    confidence: str = "high"  # "high" | "medium"

    def as_dict(self) -> Dict[str, object]:
        return {"statement": self.statement, "span": list(self.span), "sentence": self.sentence[:200], "matched": self.matched, "confidence": self.confidence}


def _anchors_present(groups: Tuple[Tuple[str, ...], ...], stems: Set[str]) -> Optional[Set[str]]:
    """The anchor stems found when every group has a representative, else None."""
    found: Set[str] = set()
    for group in groups:
        hit = [g for g in group if g in stems]
        if not hit:
            return None
        found.update(hit)
    return found


def _copular_identity(sentence: str, anchor_stems: Set[str], content_stems: Set[str]) -> bool:
    """``<subject> was/is/had always been (the) <predicate>`` with no negation, in either
    direction (*Corvin was the courier*, *the courier was Corvin*): the shape of a reveal."""
    names = [re.escape(a) + r"\w*" for a in sorted(anchor_stems)]
    subjects = "|".join(names + ["he", "she", "they", "it"])
    for c in content_stems:
        cw = re.escape(c) + r"\w*"
        forward = rf"\b(?:{subjects})\b[^.;:!?\n]{{0,40}}?\b{_COPULA}\s+(?:the|a|an|his|her|their|our|my|its)?\s*(?:\w+\s+){{0,2}}?{cw}"
        backward = rf"\b{cw}\b[^.;:!?\n]{{0,40}}?\b{_COPULA}\s+(?:{'|'.join(names) or '(?!x)x'})" if names else None
        for pattern in (forward, backward):
            if not pattern:
                continue
            m = re.search(pattern, sentence, re.I)
            if m and not _NEGATION_RX.search(m.group(0)):
                return True
    return False


def match_statement(index: SentenceIndex, stmt: Statement) -> Optional[SpoilerHit]:
    """First position at which ``stmt`` is reproduced, or None."""
    if not stmt.matchable:
        return None
    need = stmt.required_content()
    content = set(stmt.content)
    scopes = index.sentence_stems if stmt.short else index.window_stems
    for i, stems in enumerate(scopes):
        anchor_scope = stems
        if stmt.anchors and i > 0 and index.pronoun_start[i] and stmt.short:
            anchor_scope = stems | index.sentence_stems[i - 1]  # "Corvin ... . He was the courier."
        anchors_found = _anchors_present(stmt.anchors, anchor_scope) if stmt.anchors else set()
        if anchors_found is None:
            continue
        hit_content = content & stems
        if len(hit_content) < need:
            continue
        high = (stmt.anchors and len(hit_content) >= 2) or len(hit_content) >= 3
        if not high and stmt.short and _copular_identity(index.sentences[i], anchors_found, hit_content):
            high = True
        span = (index.offsets[i], index.offsets[i] + len(index.sentences[i]))
        return SpoilerHit(statement=stmt.text, span=span, sentence=index.sentences[i], matched=sorted(anchors_found | hit_content), confidence="high" if high else "medium")
    return None


def find_spoilers(prose: str, statements: Iterable[str], *, participants: Iterable[str] = (), language: Optional[str] = None, max_hits: int = 50) -> List[SpoilerHit]:
    """Every prohibited statement that the draft reproduces (at most ``max_hits``)."""
    if not prose or not prose.strip():
        return []
    index = SentenceIndex.build(prose, language=language)
    parts = list(participants)
    hits: List[SpoilerHit] = []
    seen_texts: Set[str] = set()
    for raw in statements:
        stmt = compile_statement(raw, participants=parts, language=index.language)
        key = stmt.text.lower()
        if not key or key in seen_texts:
            continue
        seen_texts.add(key)
        hit = match_statement(index, stmt)
        if hit is not None:
            hits.append(hit)
            if len(hits) >= max_hits:
                break
    return hits


__all__ = ["SentenceIndex", "SpoilerHit", "Statement", "WINDOW_SENTENCES", "compile_statement", "find_spoilers", "match_statement", "normalize_statement"]
