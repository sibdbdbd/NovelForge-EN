"""Regression tests for the false-positive traps that stalled long-form generation.

Each test reproduces a real failure mode found in the engine (see the module
docstrings of ``forge.spoilers``, ``forge.lexicon`` and ``forge.claims``) and pins
the behaviour that must hold so the repair editor can never be trapped by a
heuristic again:

A. future-outline dumping / two-word spoiler overlap  (compiler + validators)
B. regex "NER" treating numbers, verbs and adjectives as characters (claims)
C. contractions and common words as source-distinctive terms (firewall)
D. severity: heuristics are advisory, canon contradictions block (validators)
E. the repair loop stops when it is futile (pipeline)
"""

from __future__ import annotations

import os
import sys
import time
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.forge import claims as claims_mod  # noqa: E402
from app.services.forge import compiler as compiler_mod  # noqa: E402
from app.services.forge import firewall as fw  # noqa: E402
from app.services.forge import lexicon, spoilers  # noqa: E402
from app.services.forge import validators as v  # noqa: E402

PARTICIPANTS = ["Nadia Quill", "Teo Marsh", "Corvin Ashe", "Petra Vale"]


# ------------------------------------------------------------------- lexicon
def test_stemmer_is_inflectional_only():
    assert lexicon.stem("reveals") == lexicon.stem("revealed") == lexicon.stem("revealing") == "reveal"
    assert lexicon.stem("forges") == lexicon.stem("forging") == lexicon.stem("forged")
    assert lexicon.stem("manifests") == "manifest"
    assert lexicon.stem("stabbed") == "stab" and lexicon.stem("running") == "run"
    # Derivational endings are never stripped: these must stay distinct words.
    assert lexicon.stem("courier") == "courier" and lexicon.stem("supply") == "supply"
    assert lexicon.stem("gold") != lexicon.stem("golden")
    assert lexicon.stem("glass") == "glass"  # root ends in -ss


def test_lexicon_classifies_ordinary_capitalised_words():
    for w in ("Twelve", "Forty", "Opened", "Counting", "Kept", "Adjusted", "Suddenly", "The", "Don", "Gold", "Morning", "Lord", "Silence"):
        assert lexicon.is_non_name_word(w), w
    for w in ("Nadia", "Corvin", "Sapphire", "Brooch", "Harrow", "Marek"):
        assert not lexicon.is_non_name_word(w), w


def test_content_terms_drop_stop_words_and_clitics():
    assert lexicon.content_terms("I've seen the gold supply; don't tell Corvin that it's stabilized") == ["gold", "supply", "corvin", "stabilized"]


# ----------------------------------------------------------------- spoilers (A)
def test_shared_vocabulary_is_not_a_spoiler():
    """Chapter 369's outcome must not make 'gold' and 'supply' unusable in chapter 1."""
    forbidden = ["(ch.369) The gold supply is stabilized"]
    prose = "Marek weighed the gold on the brass scale. The supply of coin had been thin all winter, and the pawnshop felt it."
    assert v.validate_outline(prose, beats=[], forbidden=forbidden, language="en", participants=["Marek"]) == []
    assert v.validate_pov(prose, pov="Marek", others=[], prohibited=forbidden, language="en") == []
    # ...while actually stating the outcome is caught.
    hit = v.validate_outline("By spring the gold supply had stabilized and the guild relaxed.", beats=[], forbidden=forbidden, language="en", participants=["Marek"])
    assert [(i.code, i.severity) for i in hit] == [("future_beat_advanced", "critical")]


def test_named_subject_is_required_for_a_spoiler_about_a_character():
    forbidden = ["Corvin is revealed as the courier"]
    # Corvin appears, the courier appears, but the proposition is not stated.
    innocent = "Corvin set the chalk down and said nothing. The courier had not come that night."
    assert v.validate_outline(innocent, beats=[], forbidden=forbidden, language="en", participants=PARTICIPANTS) == []
    # A question is suspense, never a reveal.
    assert v.validate_pov("Was Corvin the courier? Nadia could not say.", pov="Nadia Quill", others=PARTICIPANTS[1:], prohibited=forbidden, language="en") == []
    # Verb inflection of an unrelated sense ("forged ahead") is not the outcome either.
    stmt = ["Corvin Ashe is the courier who forges the manifests (POV unaware; reveal planned ch.18)"]
    assert v.validate_pov("The manifests were stacked on the desk. Corvin forged ahead through the crowd.", pov="Nadia Quill", others=PARTICIPANTS[1:], prohibited=stmt, language="en") == []


def test_real_spoilers_are_still_caught_with_spans():
    cases = [
        ("Nadia realized that Corvin Ashe is the courier who forges the manifests.", ["Corvin Ashe is the courier who forges the manifests (POV unaware; reveal planned ch.18)"], PARTICIPANTS),
        ("Then Mira broke the ancient seal and claimed the throne of the city.", ["Mira claims the throne of the city"], ["Mira Hale"]),
        ("Mira knew now: the royal seal is forged, a forgery pressed by Sela's own hand.", ["The royal seal is forged (planned reveal ch.30)"], ["Mira Hale", "Sela Quint"]),
        ("He looked through the ledger.\n\nThen the clerk revealed that Corvin was forging the manifests.", ["(ch.5) clerk reveals that Corvin forges the manifests"], []),
    ]
    for prose, statements, parts in cases:
        hits = spoilers.find_spoilers(prose, statements, participants=parts, language="en")
        assert len(hits) == 1, (prose, hits)
        hit = hits[0]
        assert hit.confidence == "high"
        assert prose[hit.span[0]:hit.span[1]].strip() and hit.span[0] >= 0
        assert hit.matched


def test_copular_identity_is_a_high_confidence_reveal():
    # "X was the Y" is the canonical shape of a reveal; both directions and pronoun carry-over count.
    for prose in ("The courier was Teo all along, she was sure now.", "Teo set the chalk down. He had always been the courier.", "Teo was the courier."):
        issues = v.validate_pov(prose, pov="Nadia", others=["Teo"], prohibited=["the courier is Teo all along (POV unaware)"], language="en")
        assert [(i.code, i.severity) for i in issues] == [("forbidden_reveal", "critical")], prose
    # A negated identity is not a reveal: it drops to the advisory co-occurrence tier.
    negated = v.validate_pov("Teo was not the courier, whatever Petra thought.", pov="Nadia", others=["Teo"], prohibited=["the courier is Teo all along (POV unaware)"], language="en")
    assert [i.severity for i in negated] == ["medium"]


def test_short_statement_co_occurrence_without_identity_is_advisory_not_blocking():
    # Anchor and single content term in one sentence, but no identity claim: advisory only.
    issues = v.validate_pov("Teo asked the courier for the time and got no answer.", pov="Nadia", others=["Teo"], prohibited=["the courier is Teo all along (POV unaware)"], language="en")
    assert [(i.code, i.severity) for i in issues] == [("forbidden_reveal", "medium")]
    assert not v.ValidationReport(issues=issues).blocking


def test_statement_too_vague_to_verify_never_matches():
    stmt = spoilers.compile_statement("(ch.40) Nadia learns something.", participants=["Nadia"])
    assert not stmt.matchable
    assert spoilers.find_spoilers("Nadia learns something new every day.", ["(ch.40) Nadia learns something."], participants=["Nadia"], language="en") == []


def test_spoiler_scan_is_linear_for_a_400_chapter_novel():
    future = []
    for n in range(2, 401):
        for b in range(3):
            future.append(f"(ch.{n}) beat {b}: the merchant guild tightens its grip on the gold supply while Marek repairs the ledger")
        for a in range(2):
            future.append(f"(ch.{n}) outcome {a}: Marek discovers a fact about the pawnshop founder number {n}")
    prose = " ".join(f"Sentence number {i} about the shop and its brass scale and the ledger." for i in range(250))
    t0 = time.perf_counter()
    issues = v.validate_outline(prose, beats=[], forbidden=future, language="en", participants=["Marek"])
    elapsed = time.perf_counter() - t0
    assert issues == []
    assert elapsed < 3.0, f"{len(future)} statements took {elapsed:.2f}s"


# ----------------------------------------------------------------- compiler (A)
def _outline_card(n: int, **content: Any) -> SimpleNamespace:
    base = {"chapter_number": n, "beats": [{"description": f"Marek opens the shop on day {n} and argues with the guild clerk about rent"}, {"description": f"The guild clerk demands the ledger of chapter {n}"}, {"description": "A stranger pawns a sapphire brooch"}], "allowed_outcomes": [f"The gold supply is stabilized in chapter {n}"]}
    base.update(content)
    return SimpleNamespace(id=1000 + n, content=base)


def test_compiler_future_window_is_bounded_and_skips_current_plan():
    cards = {n: _outline_card(n) for n in range(2, 401)}
    compiler = compiler_mod.ChapterContextCompiler.__new__(compiler_mod.ChapterContextCompiler)
    compiler._chapter_index = {(1, "Chapter Outline"): cards}
    window = compiler._future_outlines(1, 1, exclude=None)
    assert [int(c.content["chapter_number"]) for c in window] == list(range(2, 2 + compiler_mod.FUTURE_OUTLINE_WINDOW))
    planned = ["Marek opens the shop and argues with the guild clerk about rent", "A stranger pawns a sapphire brooch"]
    forbidden = compiler_mod.ChapterContextCompiler._future_forbidden(window, planned, 1)
    assert 0 < len(forbidden) <= compiler_mod.FUTURE_OUTLINE_MAX_ITEMS
    assert all(f.startswith("(ch.") for f in forbidden)
    # Beats the current chapter also plans (recurring scene templates) are not forbidden.
    assert not any("sapphire brooch" in f for f in forbidden)
    assert not any("argues with the guild clerk" in f for f in forbidden)
    # Chapter 369 is far outside the window: its vocabulary never reaches the validators.
    assert not any("(ch.369)" in f for f in forbidden)


def test_compiler_future_forbidden_caps_total_items():
    window = [_outline_card(n, allowed_outcomes=[f"Outcome {k} of chapter {n} concerning the harbour chain and the tide bell" for k in range(20)]) for n in range(2, 7)]
    forbidden = compiler_mod.ChapterContextCompiler._future_forbidden(window, [], 1)
    assert len(forbidden) == compiler_mod.FUTURE_OUTLINE_MAX_ITEMS


# --------------------------------------------------------------------- NER (B)
def test_numbers_verbs_and_adverbs_opening_sentences_are_not_characters():
    prose = (
        "Twelve coins lay on the counter. Twelve was not enough.\n\n"
        "Forty years of pawnbroking had taught him patience. Forty, and not a day less.\n\n"
        "Opened at dawn, the shop smelled of brass. Opened again at noon.\n\n"
        "Counting was the only prayer he knew. Counting kept him honest.\n\n"
        "Kept ledgers never lie. Kept promises are rarer.\n\n"
        "Adjusted for the season, the price was fair. Adjusted twice, it was still fair.\n\n"
        "Suddenly the bell rang. Suddenly everything changed."
    )
    assert claims_mod.named_entities(prose, "en") == {}
    assert v.validate_entities(prose, allowed=["Marek"], language="en") == []


def test_named_items_and_people_are_still_detected():
    prose = "She set the Signet Brooch down. The Signet Brooch caught the lamplight. Marek weighed the Signet Brooch. A Sapphire glittered. The Sapphire was flawed."
    ents = claims_mod.named_entities(prose, "en")
    assert len(ents["Signet Brooch"]) == 3 and "Brooch" not in ents  # sub-token folded into the full name
    assert len(ents["Sapphire"]) == 2
    issues = {i.evidence: i.severity for i in v.validate_entities(prose, allowed=["Marek"], language="en")}
    assert issues == {"Signet Brooch": "high", "Sapphire": "medium"}
    # Genuine people: possessives, mid-sentence mentions and recurring sentence-initial names all count.
    people = claims_mod.named_entities("Nadia's ledger lay open. Corvin waved. Corvin waved again. Then Corvin left. Petra saw Teo watch Ilse Varn cross the yard.", "en")
    assert set(people) == {"Nadia", "Corvin", "Teo", "Ilse Varn"} and len(people["Corvin"]) == 3
    # One sentence-initial mention with no other evidence is not a name: that is the "Twelve coins" trap.
    assert "Teo" not in claims_mod.named_entities("Teo watched the yard.", "en")


def test_genre_capitalisation_and_contractions_are_not_entities():
    prose = "The System pinged. Status Window opened. Level Up! The Guild Master frowned. Don't look. I've seen it. It's fine. \"Kept you waiting,\" said Teo."
    ents = claims_mod.named_entities(prose, "en")
    assert set(ents) == {"Teo"}


def test_ordinary_word_that_also_appears_lowercase_is_not_a_name():
    assert claims_mod.named_entities("He bought Gold at the Market. The gold was fake; the market was closed.", "en") == {}


# ---------------------------------------------------------------- firewall (C)
def _source() -> str:
    return "\n".join([
        "I've seen it before, she said. I've been here. Yes, I've told you. Don't ask.",
        "The Greywater Exchange stood empty. He went to the Greywater Exchange again. Greywater Exchange, they called it.",
        "Twelve bells rang. Twelve more would follow. Morning came to Tessaly. Tessaly slept on. Tessaly never woke; the road to Tessaly was long.",
    ] * 3)


def test_contractions_and_common_words_are_never_distinctive_terms():
    terms = fw.extract_candidate_terms(_source(), "en")
    assert "I've" not in terms and "Don't" not in terms and "Twelve" not in terms and "Morning" not in terms
    prof = fw.SourceProfile.from_chapters([_source()], entity_names=[])
    assert prof.distinctive_terms == {"greywater exchange", "tessaly"}
    rep = fw.check_text("I've never liked mornings, he thought. Twelve of them in a row. Don't ask.", prof)
    assert rep.passed and rep.findings == []


def test_single_distinctive_term_is_advisory_but_a_cluster_blocks():
    prof = fw.SourceProfile.from_chapters([_source()], entity_names=[])
    one = fw.check_text("They reached Tessaly by dusk.", prof)
    assert [f.severity for f in one.findings] == ["medium"] and one.passed
    prof.distinctive_terms |= {"saltmarket", "lantern ward"}
    many = fw.check_text("They reached Tessaly by dusk, crossed the Saltmarket and slept in the Lantern Ward.", prof)
    assert not many.passed and all(f.severity == "high" for f in many.findings if f.check == "distinctive_term_overlap")


def test_source_entity_names_still_block_regardless_of_frequency():
    prof = fw.SourceProfile.from_chapters([_source()], entity_names=["Marit Solen"])
    rep = fw.check_text("Marit Solen waited by the door.", prof)
    assert not rep.passed and rep.findings[0].check == "entity_overlap" and rep.findings[0].severity == "critical"


# ---------------------------------------------------------------- severity (D)
def test_style_findings_never_block():
    from app.services.forge.fingerprint import build_fingerprint
    from tests.fixtures import synthetic_novel as syn

    class _Ch:
        def __init__(self, n):
            self.chapter_number, self.chapter_id, self.text, self.language, self.analysis = n, f"c{n}", syn.chapter_text(n), "en", {}

    fp = build_fingerprint([_Ch(n) for n in range(1, 13)], manuscript_id="m1")
    bad = " ".join(["The long and winding exposition of the ancient guild continued for many paragraphs, because the history of the system was known to all, and it was said that centuries ago the rule had been written by scholars who were remembered for their patience."] * 30)
    issues, report = v.validate_style(bad, fp, max_failed=0)
    assert issues and all(i.severity in ("medium", "low") for i in issues)
    assert not v.ValidationReport(issues=issues).blocking


def test_canon_contradictions_still_block():
    claim = claims_mod.Claim(kind="death", subject="Teo Marsh", value="dead", evidence="Teo Marsh died.", span=(0, 15))
    issues = v.validate_facts([claim], locked={("teo marsh", "status"): "alive"}, planned=["Nadia counts rivets"], allowed=["Teo Marsh"])
    assert [(i.code, i.severity) for i in issues] == [("unplanned_death", "critical")]


# -------------------------------------------------------------------- lexicon alias
def test_prohibited_stop_alias_points_at_shared_lexicon():
    assert v._PROHIBITED_STOP is lexicon.STOP_WORDS
