"""Claim extraction from a chapter draft.

Two channels:
1. A structured channel: the drafting model may return a JSON block of claims
   (``ChapterClaims`` schema) *outside* the visible prose. It is optional.
2. A deterministic channel: ``extract_claims`` always runs over the prose and
   produces entity mentions, possession/location/injury/knowledge statements
   with exact evidence spans. Deterministic claims are what validation and
   synchronization trust; model claims are cross-checked against them and are
   never applied unless an evidence span in the prose supports them.

Every claim carries its evidence span and a support level:
explicit (a sentence states it), strongly_entailed (a pattern implies it
unambiguously), weakly_inferred (needs interpretation) or unsupported.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.services.forge.lexicon import is_non_name_word
from app.services.forge.textmetrics import detect_language, split_sentences

CLAIMS_VERSION = "claims-1"
CLAIMS_BLOCK_RX = re.compile(r"<claims>\s*([\s\S]*?)\s*</claims>", re.S | re.I)
CHAPTER_SUMMARY_RX = re.compile(r"<chapter_summary>\s*([\s\S]*?)\s*</chapter_summary>", re.S | re.I)
CHAPTER_SUM_HASH_RX = re.compile(r"(?:^|\n)\s*#chapter\d*sum[:\s]*\n?([\s\S]*?)(?:(?:\n\s*)?#endchapter\d*sum|(?=(?:^|\n)\s*#(?:scenehandoff|claims))|\Z)", re.I)
SCENE_HANDOFF_RX = re.compile(r"<scene_handoff>\s*([\s\S]*?)\s*</scene_handoff>", re.S | re.I)


def _clean_json_payload(raw_json: str) -> str:
    text = raw_json.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_scene_handoff_text(text: str) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip().lower()] = v.strip()
    return kv

_CAP_NAME = re.compile(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b")
_HANGUL_NAME = re.compile(r"[\uac00-\ud7a3]{2,4}(?=(?:은|는|이|가|을|를|의|에게|과|와|도|만|께서|이가)?\s)")
# Capitalised words that are not names for reasons the lexicon cannot know:
# genre nouns that webnovel prose routinely capitalises (System, Status, Guild
# ...), spatial adverbs and states of being that open sentences.
_GENRE_CAP = {
    "system", "status", "window", "interface", "admin", "game", "flag", "flags", "quest", "skill", "level", "class", "classes", "dungeon", "guild", "rank", "title", "stat", "stats", "hp", "mp", "exp",
    "inside", "outside", "behind", "above", "below", "beyond", "except", "like", "unlike",
    "dorm", "dormitory", "office", "infirmary", "library", "academy", "hall", "tower", "palace", "temple", "church", "castle", "manor", "estate", "market", "square", "street", "road", "gate", "wall",
    "step", "steps",
}
_STATE_ADJ = {"poisoned", "injured", "wounded", "bleeding", "dying", "dead", "corrupted", "broken", "shocked", "terrified", "trapped", "forced", "surrounded", "determined", "unable", "aware", "afraid", "lost", "hidden", "alone", "silent", "still"}


def _is_common_capitalized(word: str) -> bool:
    """A capitalised word that is ordinary English rather than a proper name.

    Delegates to the shared lexicon (stop words, numbers, titles, colours, time
    words, inflected verbs and adverbs) and adds the genre nouns and state
    adjectives above.
    """
    w = word.lower()
    return len(w) <= 2 or w in _GENRE_CAP or w in _STATE_ADJ or is_non_name_word(w)

_POSSESS_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:took|picked up|pocketed|received|was handed|accepted|stole|grabbed|kept|now held|carried)\s+(?:the|a|an|his|her)?\s*([a-z][a-z\- ]{2,40}?)(?:[.,;]| and | from | that | which )")
_LOSE_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:dropped|lost|gave away|handed over|surrendered|threw away|left behind)\s+(?:the|a|an|his|her)?\s*([a-z][a-z\- ]{2,40}?)(?:[.,;]| to | and )")
_MOVE_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:arrived at|reached|entered|walked into|stepped into|returned to|left for|rode to|traveled to|travelled to|came to)\s+(?:the\s+)?([A-Z][A-Za-z' ]{2,40}?)(?:[.,;]|\s(?:and|where|as|with|before|after)\b)")
_INJURY_EN = re.compile(r"\b([A-Z][a-z]+)(?:'s)?\s+(?:was|were|got|had been)\s+(wounded|injured|cut|stabbed|shot|burned|bruised|poisoned|broken|blinded|knocked out|bleeding)")
_LEARN_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:learned|realized|realised|discovered|found out|now knew|understood at last|understood)\s+(?:that\s+)?([^.?!\n]{6,160})")
_DIE_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:died|was dead|was killed|fell dead|breathed (?:his|her) last)")
_JOIN_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:joined|was inducted into|swore (?:an oath|fealty) to|became a member of|was expelled from|left)\s+(?:the\s+)?([A-Z][A-Za-z' ]{2,40}?)(?:[.,;]|\s(?:and|as)\b)")
_PROMISE_EN = re.compile(r"\b([A-Z][a-z]+)\s+(?:promised|swore|vowed)\s+(?:to\s+)?([^.?!\n]{4,140})")

_POSSESS_KO = re.compile(r"([\uac00-\ud7a3]{2,4})(?:은|는|이|가)\s+([\uac00-\ud7a3 ]{2,20}?)(?:을|를)\s+(?:받았다|챙겼다|집어\s?들었다|손에\s?넣었다|얻었다|가져갔다|건네받았다)")
_LOSE_KO = re.compile(r"([\uac00-\ud7a3]{2,4})(?:은|는|이|가)\s+([\uac00-\ud7a3 ]{2,20}?)(?:을|를)\s+(?:잃었다|떨어뜨렸다|넘겨주었다|버렸다|빼앗겼다)")
_MOVE_KO = re.compile(r"([\uac00-\ud7a3]{2,4})(?:은|는|이|가)\s+([\uac00-\ud7a3 ]{2,20}?)(?:에|으로|로)\s+(?:도착했다|들어섰다|들어갔다|돌아왔다|향했다|올랐다|내려갔다)")
_INJURY_KO = re.compile(r"([\uac00-\ud7a3]{2,4})(?:은|는|이|가|의)\s+[\uac00-\ud7a3 ]{0,12}?(다쳤다|베였다|찔렸다|부러졌다|피를\s?흘렸다|중독되었다|쓰러졌다|화상을\s?입었다)")
_LEARN_KO = re.compile(r"([\uac00-\ud7a3]{2,4})(?:은|는|이|가)\s+([^.?!\n]{4,80}?)(?:는|다는|라는)\s+(?:것을|사실을)\s+(?:알았다|알게\s?되었다|깨달았다|눈치챘다)")
_DIE_KO = re.compile(r"([\uac00-\ud7a3]{2,4})(?:은|는|이|가)\s+(?:죽었다|숨을\s?거두었다|목숨을\s?잃었다|살해당했다)")


class ClaimModel(BaseModel):
    """One structured claim the drafting model may report."""

    kind: str = Field(description="entity_introduced | possession_gained | possession_lost | location_changed | injury | knowledge_gained | relationship_changed | death | membership_changed | promise_made | other")
    subject: str = Field(default="")
    value: str = Field(default="")
    evidence: str = Field(default="", description="Exact sentence from the prose supporting the claim")


class ChapterClaims(BaseModel):
    claims: List[ClaimModel] = Field(default_factory=list)
    summary: str = Field(default="")
    ending_location: str = Field(default="")
    current_time: str = Field(default="")
    unresolved_immediate_action: str = Field(default="")
    open_dialogue_obligation: str = Field(default="")


@dataclass
class Claim:
    kind: str
    subject: str
    value: Any
    evidence: str
    span: Tuple[int, int]
    support: str = "explicit"
    source: str = "deterministic"  # or "model"

    def as_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "subject": self.subject, "value": self.value, "evidence": self.evidence[:240], "span": list(self.span), "support": self.support, "source": self.source}


def split_prose_and_claims(raw: str) -> Tuple[str, Optional[ChapterClaims]]:
    """Separate the visible prose from optional <claims>, <chapter_summary>, and <scene_handoff> blocks."""
    if not raw:
        return "", None

    prose = raw
    model_claims: Optional[ChapterClaims] = None

    # 1. Try extracting <claims> block
    m_claims = CLAIMS_BLOCK_RX.search(prose)
    if m_claims:
        claims_text = m_claims.group(1)
        prose = (prose[: m_claims.start()] + prose[m_claims.end():]).strip()
        try:
            cleaned = _clean_json_payload(claims_text)
            data = json.loads(cleaned)
            model_claims = ChapterClaims.model_validate(data)
        except Exception:
            model_claims = None

    # 2. Extract <chapter_summary> or #chapterXsum block
    summary_text = ""
    m_sum = CHAPTER_SUMMARY_RX.search(prose)
    if m_sum:
        summary_text = m_sum.group(1).strip()
        prose = (prose[: m_sum.start()] + prose[m_sum.end():]).strip()
    else:
        m_sum_hash = CHAPTER_SUM_HASH_RX.search(prose)
        if m_sum_hash:
            summary_text = m_sum_hash.group(1).strip()
            prose = (prose[: m_sum_hash.start()] + prose[m_sum_hash.end():]).strip()

    # 3. Extract <scene_handoff> block
    handoff_kv: Dict[str, str] = {}
    m_handoff = SCENE_HANDOFF_RX.search(prose)
    if m_handoff:
        handoff_kv = _parse_scene_handoff_text(m_handoff.group(1))
        prose = (prose[: m_handoff.start()] + prose[m_handoff.end():]).strip()

    # If any structured continuity was extracted, ensure ChapterClaims exists and is populated
    if summary_text or handoff_kv:
        if model_claims is None:
            model_claims = ChapterClaims()
        if summary_text and not model_claims.summary:
            model_claims.summary = summary_text
        if not model_claims.ending_location:
            model_claims.ending_location = handoff_kv.get("ending_location") or handoff_kv.get("location") or ""
        if not model_claims.current_time:
            model_claims.current_time = handoff_kv.get("current_time") or handoff_kv.get("time") or ""
        if not model_claims.unresolved_immediate_action:
            model_claims.unresolved_immediate_action = handoff_kv.get("unresolved_action") or handoff_kv.get("unresolved_immediate_action") or ""
        if not model_claims.open_dialogue_obligation:
            model_claims.open_dialogue_obligation = handoff_kv.get("open_dialogue") or handoff_kv.get("open_dialogue_obligation") or ""

    return prose.strip(), model_claims


def _find(prose: str, needle: str, start: int = 0) -> Tuple[int, int]:
    idx = prose.find(needle, start)
    return (idx, idx + len(needle)) if idx >= 0 else (-1, -1)


def _sentence_starts(prose: str, lang: str) -> Set[int]:
    """Character offsets where a sentence (or a quoted/parenthesised line) begins."""
    starts: Set[int] = set()
    pos = 0
    for s in split_sentences(prose, lang):
        idx = prose.find(s, pos)
        if idx < 0:
            continue
        starts.add(idx)
        m_lead = re.match(r'^[\s"“\'‘(\[]+', s)
        if m_lead:
            starts.add(idx + m_lead.end())
        pos = idx + len(s)
    for m in re.finditer(r'(?:^|\n)[\s"“\'‘(\[]*', prose):
        starts.add(m.end())
    # After a colon, semicolon, dash or an opening quote mid-sentence, capitalisation restarts too.
    for m in re.finditer(r'[:;—–]\s+|["“]\s*', prose):
        starts.add(m.end())
    return starts


def named_entities(prose: str, language: Optional[str] = None) -> Dict[str, List[Tuple[int, int]]]:
    """Candidate proper names with their spans.

    English: a capitalised token (or a run of up to two) counts as a name when it
    is *positionally* evidenced — it appears capitalised at least once where
    English would not capitalise an ordinary word (mid-sentence), or it is a
    multi-word run — and is not an ordinary word by the lexicon. Sentence-initial
    words alone are never names: "Twelve coins…", "Opened at dawn…" and
    "Counting was…" recur at sentence starts in normal prose. A word's lowercase
    form appearing in the same text is strong evidence against it being a name.

    Korean: Hangul 2–4 syllable tokens directly before a particle.
    """
    lang = language or detect_language(prose)
    out: Dict[str, List[Tuple[int, int]]] = {}
    if lang == "ko":
        for m in _HANGUL_NAME.finditer(prose):
            out.setdefault(m.group(0), []).append((m.start(), m.end()))
        return out
    starts = _sentence_starts(prose, lang)
    lowercase_forms = {w for w in re.findall(r"\b[a-z][a-z]+\b", prose)}
    candidates: Dict[str, List[Tuple[int, int, bool]]] = {}
    consumed_until = -1  # end offset of the last re-extended entity (see below)
    for m in _CAP_NAME.finditer(prose):
        if m.start() < consumed_until:
            continue  # already absorbed into the previous (re-extended) entity
        token = m.group(0)
        words = token.split()
        m_start = m.start()
        # Contraction heads ("Don", "It", "They") are stop words and drop out here; a
        # possessive ("Nadia's") keeps its name because the regex stops at the apostrophe.
        if _is_common_capitalized(words[0]):
            if len(words) == 1:
                continue
            # "The Salt" / "Old Marek": drop the ordinary head and keep the name that follows.
            m_start += len(words[0]) + 1
            token, words = words[1], [words[1]]
            if _is_common_capitalized(token):
                continue  # "Status Window", "Guild Master": two ordinary genre words
            # "The Signet Brooch": the regex paired "The Signet" and left "Brooch" for the next
            # match; re-extend so the full name is one entity.
            tail = re.match(r"\s[A-Z][a-z]+\b", prose[m_start + len(token):])
            if tail and not _is_common_capitalized(tail.group(0).strip()):
                token = token + tail.group(0)
                words = token.split()
                consumed_until = m_start + len(token)
        elif len(words) == 2 and _is_common_capitalized(words[1]):
            # "Marek Opened" — a name followed by an ordinary capitalised word: keep the name only.
            token, words = words[0], [words[0]]
        mid_sentence = m_start not in starts
        # A possessive ("Nadia's") is positive evidence of a name even at a sentence start.
        possessive = m_start + len(token) < len(prose) and prose[m_start + len(token)] in ("'", "’") and prose[m_start + len(token) + 1: m_start + len(token) + 2].lower() == "s"
        candidates.setdefault(token, []).append((m_start, m_start + len(token), mid_sentence or possessive))
    for token, spans in candidates.items():
        words = token.split()
        if len(words) == 1 and token.lower() in lowercase_forms:
            continue  # "Gold ... gold": an ordinary word that happened to open a sentence
        if len(words) == 1 and not any(mid for _, _, mid in spans):
            # Only ever sentence-initial: a name needs to recur before it counts (the lexicon
            # already rejected inflected verbs and adverbs such as "Opened" or "Suddenly").
            if len(spans) < 2:
                continue
        out[token] = [(a, b) for a, b, _ in spans]
    # A single-word name that is also the head of a recorded two-word name ("Brooch" in
    # "Signet Brooch") is the same entity; fold it into the longer form.
    multi = {t for t in out if " " in t}
    for t in list(out):
        if " " in t:
            continue
        owners = [mw for mw in multi if t in mw.split()]
        if owners:
            owner = owners[0]
            owner_spans = {(a, b) for a, b in out[owner]}
            out[owner] = sorted(owner_spans | {(a, b) for a, b in out[t] if not any(oa <= a < ob for oa, ob in owner_spans)})
            del out[t]
    return out

def extract_claims(prose: str, language: Optional[str] = None) -> List[Claim]:
    lang = language or detect_language(prose)
    claims: List[Claim] = []

    def add(kind: str, subject: str, value: Any, m: re.Match, support: str = "explicit") -> None:
        claims.append(Claim(kind=kind, subject=subject.strip(), value=value, evidence=prose[m.start():m.end()], span=(m.start(), m.end()), support=support))

    if lang == "ko":
        for m in _POSSESS_KO.finditer(prose):
            add("possession_gained", m.group(1), m.group(2).strip(), m)
        for m in _LOSE_KO.finditer(prose):
            add("possession_lost", m.group(1), m.group(2).strip(), m)
        for m in _MOVE_KO.finditer(prose):
            add("location_changed", m.group(1), m.group(2).strip(), m)
        for m in _INJURY_KO.finditer(prose):
            add("injury", m.group(1), m.group(2).strip(), m)
        for m in _LEARN_KO.finditer(prose):
            add("knowledge_gained", m.group(1), m.group(2).strip(), m)
        for m in _DIE_KO.finditer(prose):
            add("death", m.group(1), "dead", m)
        return claims
    for m in _POSSESS_EN.finditer(prose):
        add("possession_gained", m.group(1), m.group(2).strip(), m)
    for m in _LOSE_EN.finditer(prose):
        add("possession_lost", m.group(1), m.group(2).strip(), m)
    for m in _MOVE_EN.finditer(prose):
        add("location_changed", m.group(1), m.group(2).strip(), m)
    for m in _INJURY_EN.finditer(prose):
        add("injury", m.group(1), m.group(2).strip(), m)
    for m in _LEARN_EN.finditer(prose):
        add("knowledge_gained", m.group(1), m.group(2).strip(), m, support="strongly_entailed" if "realized" in m.group(0) or "realised" in m.group(0) else "explicit")
    for m in _DIE_EN.finditer(prose):
        add("death", m.group(1), "dead", m)
    for m in _JOIN_EN.finditer(prose):
        add("membership_changed", m.group(1), m.group(2).strip(), m)
    for m in _PROMISE_EN.finditer(prose):
        add("promise_made", m.group(1), m.group(2).strip(), m, support="strongly_entailed")
    return claims


def merge_model_claims(prose: str, deterministic: List[Claim], model: Optional[ChapterClaims]) -> List[Claim]:
    """Model claims are accepted only when their evidence sentence exists in the prose."""
    out = list(deterministic)
    if model is None:
        return out
    for mc in model.claims:
        ev = (mc.evidence or "").strip()
        span = _find(prose, ev) if ev else (-1, -1)
        if span[0] < 0:
            out.append(Claim(kind=mc.kind, subject=mc.subject, value=mc.value, evidence=ev, span=(-1, -1), support="unsupported", source="model"))
            continue
        dup = any(c.kind == mc.kind and c.subject.lower() == mc.subject.lower() and str(c.value).lower() == str(mc.value).lower() for c in out)
        if not dup:
            out.append(Claim(kind=mc.kind, subject=mc.subject, value=mc.value, evidence=ev, span=span, support="strongly_entailed", source="model"))
    return out


__all__ = ["CLAIMS_VERSION", "ChapterClaims", "Claim", "ClaimModel", "extract_claims", "merge_model_claims", "named_entities", "split_prose_and_claims"]
