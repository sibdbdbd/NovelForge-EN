"""Deterministic Webnovel Conformance: does the draft *read* like the profile says it should?

No model call. Measures the signals a regex can honestly measure and turns them
into 1-10 scores with cited, actionable findings, in six dimensions:

- rhythm      — paragraph length profile vs. the profile's rhythm, walls, dialogue-on-own-line
- inner_voice — direct inner speech in the configured marker, private verdicts after dialogue
- conventions — windows / SFX / address forms present when enabled, absent when disabled;
                recap opening; Western-literary metaphor stacking
- momentum    — opening in motion, transition-marker abuse, exposition blocks
- reward      — micro-payoffs and on-page reversal with reaction shots
- ending      — hook class and strength of the final line

The Prose Craft critic merges these into its report (lower score per shared
dimension wins), so a chapter that is clean English prose but not a webnovel
still gets polished toward the profile.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from app.schemas.webnovel import ConformanceFinding, WebnovelConformance, WebnovelStyleProfile
from app.services.forge.craft import hooks as hooks_mod
from app.services.forge.textmetrics import count_units, detect_language, split_paragraphs, split_sentences

# Inner speech markers.
_SQ_THOUGHT = re.compile(r"(?m)^\s*[‘'](?!s\b)[^’'\n]{3,240}[’']\s*$")            # 'So that's how it is.' on its own line
_IT_THOUGHT = re.compile(r"(?m)^\s*\*[^*\n]{3,240}\*\s*$")                          # *italic thought* on its own line
_DASH_ASIDE = re.compile(r"—[^—\n]{4,120}—")
_DIALOGUE = re.compile(r"(?m)^\s*[\"“][^\"”\n]{1,600}[\"”]")
_DIALOGUE_ANY = re.compile(r"[\"“][^\"”\n]{2,}[\"”]")
_WINDOW = re.compile(r"(?m)^\s*[\[【<][^\]】>\n]{2,160}[\]】>]\s*$")
_WINDOW_INLINE = re.compile(r"\[[A-Z][^\]\n]{2,80}\]")
_SFX = re.compile(r"(?m)^\s*(?:[A-Z][a-z]{1,10}(?:,\s*[a-z]{1,10})?[—\-–!.]+|[A-Z]{2,10}[—!.]+)\s*$")
_RECAP_OPEN = re.compile(r"^(?:\s*(?:previously|last (?:time|chapter)|as (?:you|we) (?:may )?(?:recall|remember)|after (?:the|what) (?:events|happened)|it had been \w+ (?:days|hours|weeks) since|the (?:day|night) before,? (?:I|he|she|they) had))", re.I)
_WEATHER_OPEN = re.compile(r"^\s*(?:the (?:sun|rain|wind|sky|morning|dawn|night|moon|fog)|it was a (?:cold|warm|grey|gray|bright|dark|quiet))\b", re.I)
_TRANSITION = re.compile(r"^(?:meanwhile|later|afterward|afterwards|hours later|that night|the next (?:morning|day|night)|elsewhere|at the same time)\b", re.I)
_EXPOSITION = re.compile(r"\b(?:was known|had been|centuries|years ago|the system was|the rule was|according to|it was said|history|founded|established in)\b", re.I)
_METAPHOR = re.compile(r"\b(?:like a|like the|as if|as though|as a|reminded (?:him|her|them|me) of|a tapestry of|a symphony of|a dance of|the ghost of a)\b", re.I)
_LITERARY = re.compile(r"\b(?:liminal|ephemeral|ineffable|gossamer|luminous|cacophony|palimpsest|a testament to|juxtaposition|visceral|resonat(?:e|ed|ing))\b", re.I)
_WANT_STATED = re.compile(r"[\"“][^\"”\n]*\bI (?:want|need) (?:you to|to)\b[^\"”\n]*[\"”]", re.I)
_REACTION_SHOT = re.compile(r"\b(?:stared|gaped|went (?:pale|white|red|still|quiet|silent)|froze|flinched|fell silent|silence (?:fell|spread)|murmur(?:s|ed)?|whisper(?:s|ed)? (?:ran|spread|rippled)|jaw (?:tightened|dropped|worked)|mouth (?:opened|fell open|worked)|eyes (?:widened|narrowed|went wide)|blinked|looked at (?:me|him|her) (?:again|differently|properly|for the first time)|re-?evaluat|recalculat|swallowed|stepped back|took a step back|lowered (?:his|her|their) (?:head|gaze|eyes)|bowed|straightened|nobody (?:laughed|spoke|moved))\b", re.I)
_UNDERESTIMATION = re.compile(r"\b(?:sneer|scoff|snort|smirk|dismiss|laughed at|rolled (?:his|her|their) eyes|waved (?:me|him|her) off|didn'?t (?:even )?look|nobody expected|no one expected|what could (?:a|an|the) \w+ (?:possibly )?do|you\? |just a\b|only a\b|a mere\b|beneath (?:him|her|them|notice))\b", re.I)
_TIER_WORDS = re.compile(r"\b(?:rank(?:ed)?|level|lv\.?|tier|grade|stage|floor|class [A-F]|[A-F](?:\+|-)?-rank|S-rank|SS-rank|breakthrough|awakened|promoted|ascended|advanced to)\b", re.I)
_TIER_GAIN = re.compile(r"\b(?:rank(?:ed)? up|level(?:ed)? up|leveled|advanced to|promoted to|broke through|breakthrough|reached (?:the )?(?:\w+ )?(?:rank|stage|realm|floor|level)|new (?:rank|skill|title|class)|skill acquired|acquired:|unlocked|awakened|re-?measur(?:e|ed|ing)|(?:rank|grade|level|stage)\s*:?\s*[A-Z]{1,3}\b(?:\+|-)?|\brank [A-Z]\b)", re.I)
_PRIVATE_VERDICT = re.compile(r"(?m)^\s*(?:[‘'][^’'\n]{3,160}[’']|\*[^*\n]{3,160}\*|(?:So|Right|Fine|Well|Of course|Naturally|Figures|Liar|Interesting|Wrong|Good|Bad|No)\.|[A-Z][^.!?\n]{0,60}\b(?:then|apparently|probably|clearly|obviously|which meant|so that was|filed|noted|counted)\b[^.!?\n]{0,60}\.)\s*$")


def _clamp(v: float) -> int:
    return int(max(1, min(10, round(v))))


def _finding(code: str, severity: str, problem: str, fix: str, quote: str = "") -> ConformanceFinding:
    return ConformanceFinding(code=code, severity=severity, problem=problem, fix=fix, quote=quote[:140])


def _paragraph_profile(paras: Sequence[str], lang: Optional[str]) -> Dict[str, float]:
    if not paras:
        return {"count": 0, "one_line_share": 0.0, "short_share": 0.0, "wall_share": 0.0, "mean_units": 0.0}
    lengths = [count_units(p, lang) for p in paras]
    beat_counts = [_beats_in_paragraph(p, lang) for p in paras]
    one_line = sum(1 for n in beat_counts if n <= 1)
    short = sum(1 for n in beat_counts if n <= 3)
    walls = sum(1 for n in lengths if n > 110)
    return {"count": len(paras), "one_line_share": one_line / len(paras), "short_share": short / len(paras), "wall_share": walls / len(paras), "mean_units": sum(lengths) / len(lengths)}


def _beats_in_paragraph(p: str, lang: Optional[str]) -> int:
    """Sentences per paragraph, where a spoken line plus its attribution counts as one beat and short units (≤ 28 words) as one line."""
    if _DIALOGUE.match(p) and count_units(p, lang) <= 40:
        return 1
    if count_units(p, lang) <= 28:
        return 1
    return len(split_sentences(p, lang))


def _dialogue_followed_by_verdict(paras: Sequence[str]) -> Tuple[int, int]:
    """(dialogue paragraphs, dialogue paragraphs followed within two paragraphs by a private verdict)."""
    d = 0
    v = 0
    for i, p in enumerate(paras):
        if _DIALOGUE.match(p):
            d += 1
            window = paras[i + 1:i + 3]
            if any(_PRIVATE_VERDICT.match(w) or _SQ_THOUGHT.match(w) or _IT_THOUGHT.match(w) for w in window):
                v += 1
    return d, v


def measure_conformance(
    prose: str,
    profile: WebnovelStyleProfile,
    *,
    language: Optional[str] = None,
    closing_hook_plan: str = "",
    chapter_number: Optional[int] = None,
    pacing_mode: Optional[str] = None,
) -> WebnovelConformance:
    lang = language or detect_language(prose)
    text = prose or ""
    paras = split_paragraphs(text)
    sents = split_sentences(text, lang)
    words = count_units(text, lang) or 1
    per_k = 1000.0 / float(words)
    n, e, r, c = profile.narration, profile.engine, profile.reader, profile.chapter
    findings: List[ConformanceFinding] = []
    metrics: Dict[str, float] = {}

    # ---------------------------------------------------------------- rhythm
    shape = _paragraph_profile(paras, lang)
    metrics.update({"paragraphs": shape["count"], "one_line_share": round(shape["one_line_share"], 3), "short_para_share": round(shape["short_share"], 3), "wall_share": round(shape["wall_share"], 3), "mean_para_units": round(shape["mean_units"], 1)})
    rhythm = 8.0
    if n.paragraph_rhythm == "one_line":
        target_one = 0.55
        if shape["one_line_share"] < target_one:
            rhythm -= min(4.0, (target_one - shape["one_line_share"]) * 10)
            findings.append(_finding("rhythm_too_dense", "high" if shape["one_line_share"] < 0.35 else "medium", f"Only {round(shape['one_line_share'] * 100)}% of paragraphs are single sentences; the profile asks for a one-line mobile rhythm", "Break paragraphs at every beat; give each line of dialogue, each private thought and each impact its own line"))
    elif n.paragraph_rhythm == "short":
        if shape["short_share"] < 0.7:
            rhythm -= min(3.0, (0.7 - shape["short_share"]) * 8)
            findings.append(_finding("rhythm_long_paragraphs", "medium", f"Only {round(shape['short_share'] * 100)}% of paragraphs are ≤3 sentences", "Split paragraphs around beats and lines of dialogue"))
    if shape["wall_share"] > 0.12:
        rhythm -= min(3.0, shape["wall_share"] * 12)
        wall = next((p for p in paras if count_units(p, lang) > 110), "")
        findings.append(_finding("paragraph_walls", "high" if shape["wall_share"] > 0.25 else "medium", f"{round(shape['wall_share'] * 100)}% of paragraphs are walls (>110 units)", "Cut every wall into one-idea paragraphs; move interiority onto its own lines", wall[:120]))
    # dialogue sharing a paragraph with long narration
    mixed = sum(1 for p in paras if _DIALOGUE_ANY.search(p) and count_units(p, lang) > 60 and not _DIALOGUE.match(p))
    if mixed >= 3:
        rhythm -= 1.0
        findings.append(_finding("dialogue_buried", "medium", f"{mixed} lines of dialogue are buried inside long narration paragraphs", "Give each spoken line its own paragraph; put the POV's reaction on the next line"))
    metrics["dialogue_buried"] = mixed

    # ------------------------------------------------------------ inner voice
    sq = len(_SQ_THOUGHT.findall(text))
    it = len(_IT_THOUGHT.findall(text))
    dash = len(_DASH_ASIDE.findall(text))
    marked = {"single_quotes": sq, "italics": it, "em_dash": dash, "plain": 0}[n.thought_style]
    wrong_marker = {"single_quotes": it, "italics": sq, "em_dash": 0, "plain": sq + it}[n.thought_style]
    metrics.update({"inner_speech_marked": marked, "inner_speech_wrong_marker": wrong_marker, "inner_speech_per_k": round(marked * per_k, 2)})
    want = {"sparse": 1.0, "regular": 2.5, "dense": 4.5}[n.thought_density]  # per 1000 words
    inner = 8.0
    if n.thought_style != "plain":
        have = marked * per_k
        if have < want * 0.5:
            inner -= 3.5
            findings.append(_finding("inner_speech_missing", "high", f"{marked} marked inner-speech line(s) in {words} words; the profile wants ≈{want:.0f}/1000 in {n.thought_style.replace('_', ' ')}", f"After significant lines and at each turn, add the POV's direct private line in {n.thought_style.replace('_', ' ')} on its own line — a verdict, a price, a misread"))
        elif have < want:
            inner -= 1.5
            findings.append(_finding("inner_speech_thin", "medium", f"Inner speech is thin ({have:.1f}/1000 vs ≈{want:.0f})", "Add a private one-liner after the other characters' key lines"))
        if wrong_marker >= 2:
            inner -= 1.5
            findings.append(_finding("inner_speech_marker", "medium", f"{wrong_marker} inner-speech line(s) use a different marker than the profile's {n.thought_style.replace('_', ' ')}", f"Use {n.thought_style.replace('_', ' ')} consistently for thought"))
    d_count, v_count = _dialogue_followed_by_verdict(paras)
    verdict_share = (v_count / d_count) if d_count else 1.0
    metrics.update({"dialogue_paragraphs": d_count, "dialogue_with_private_verdict": v_count, "verdict_share": round(verdict_share, 3)})
    if d_count >= 6 and verdict_share < 0.25:
        inner -= 2.0
        findings.append(_finding("no_private_verdicts", "high", f"Only {v_count} of {d_count} dialogue lines are followed by the POV's private read", "Webnovel readers stay for the narrator's head: after most significant lines, one line of what the POV actually thinks (price, lie, exit, grade)"))
    elif d_count >= 6 and verdict_share < 0.45:
        inner -= 0.8

    # ------------------------------------------------------------ conventions
    conv = 8.5
    windows = len(_WINDOW.findall(text))
    inline_windows = len(_WINDOW_INLINE.findall(text))
    sfx = len(_SFX.findall(text))
    metrics.update({"windows": windows, "windows_inline": inline_windows, "sfx_lines": sfx})
    if n.windows_enabled and n.window_style != "none":
        if windows == 0 and (_TIER_WORDS.search(text) or e.subgenre in ("hunter_gate", "system_apocalypse", "tower_climb", "game_litrpg", "dungeon")):
            conv -= 1.5
            findings.append(_finding("windows_absent", "medium", "The world has system windows but this chapter shows none although it mentions ranks/levels/skills", "Render one terse window on its own line at the measurable moment, followed by the POV's dry one-line reaction"))
        elif windows > max(6, words // 300):
            conv -= 1.5
            findings.append(_finding("windows_spam", "medium", f"{windows} window lines; the page turns into a spreadsheet", "Keep the two that matter; narrate the rest through effect"))
    elif windows >= 2:
        conv -= 2.0
        findings.append(_finding("windows_forbidden", "high", f"{windows} bracketed window lines in a world without system windows", "Remove the windows; show power through effect and reactions"))
    if n.sfx_density == "none" and sfx >= 2:
        conv -= 1.0
        findings.append(_finding("sfx_forbidden", "low", f"{sfx} stand-alone sound-effect lines but the profile disables them", "Fold impacts into action sentences"))
    elif n.sfx_density == "regular" and sfx == 0 and words >= 1200 and e.subgenre not in ("office_life", "romance_fantasy", "villainess_transmigration", "entertainment_industry"):
        conv -= 0.7
        findings.append(_finding("sfx_absent", "low", "No stand-alone SFX line in an action-genre chapter", "At one moment of impact, let the sound stand alone on its line ('Thud.')"))
    if sfx > max(5, words // 400):
        conv -= 1.0
        findings.append(_finding("sfx_spam", "medium", f"{sfx} stand-alone SFX lines; it reads like a comic panel", "Keep at most a few per chapter, at real impacts"))
    first = paras[0] if paras else ""
    if first and _RECAP_OPEN.search(first) and not c.recap_allowed:
        conv -= 2.5
        findings.append(_finding("recap_opening", "high", "The chapter opens with recap", "Open inside an action, a line of dialogue or a sharp private thought", first[:120]))
    elif first and _WEATHER_OPEN.search(first):
        conv -= 1.0
        findings.append(_finding("weather_opening", "medium", "The chapter opens on weather / atmosphere", "Open on a person doing something or saying something", first[:120]))
    metaphors = len(_METAPHOR.findall(text))
    literary = len(_LITERARY.findall(text))
    metrics.update({"metaphor_per_k": round(metaphors * per_k, 2), "literary_words": literary})
    if metaphors * per_k > 9:
        conv -= 1.5
        findings.append(_finding("metaphor_stacking", "medium", f"{metaphors} figurative comparisons ({metaphors * per_k:.1f}/1000 words): Western literary texture, not webnovel", "Replace most comparisons with a concrete observation or the POV's flat verdict"))
    if literary >= 3:
        conv -= 1.0
        m = _LITERARY.search(text)
        findings.append(_finding("literary_register", "medium", f"{literary} literary-workshop words", "Use the narrator's plain, quick idiom", m.group(0) if m else ""))
    wants = len(_WANT_STATED.findall(text))
    if wants >= 2:
        conv -= 1.0
        m = _WANT_STATED.search(text)
        findings.append(_finding("want_stated_directly", "medium", f"{wants} lines of dialogue state the speaker's want outright", "Nobody says what they want in their first line; make the line a move and let the POV decode it", m.group(0) if m else ""))
    metrics["wants_stated"] = wants

    # -------------------------------------------------------------- momentum
    momentum = 8.0
    transitions = sum(1 for p in paras if _TRANSITION.match(p))
    expo_sents = sum(1 for s in sents if _EXPOSITION.search(s) and not _DIALOGUE_ANY.search(s))
    expo_share = expo_sents / float(len(sents) or 1)
    metrics.update({"transition_paragraphs": transitions, "exposition_share": round(expo_share, 3)})
    if transitions >= 4:
        momentum -= 1.5
        findings.append(_finding("transition_hopping", "medium", f"{transitions} paragraphs open with a time/place transition marker", "Cut to the new scene mid-action; let one concrete detail place the reader"))
    if expo_share > 0.14:
        momentum -= min(3.0, (expo_share - 0.14) * 20)
        findings.append(_finding("exposition_block", "high" if expo_share > 0.22 else "medium", f"{round(expo_share * 100)}% of sentences are exposition", "Deliver world facts through a conflict, a price or a mistake; cut the rest"))
    # exposition runs: 4+ consecutive expository sentences
    run = best = 0
    for s in sents:
        if _EXPOSITION.search(s) and not _DIALOGUE_ANY.search(s):
            run += 1
            best = max(best, run)
        else:
            run = 0
    if best >= 4:
        momentum -= 1.0
        findings.append(_finding("exposition_run", "medium", f"A run of {best} consecutive expository sentences", "Break the lecture with a line of dialogue or the POV's reaction"))
    if paras and not (_DIALOGUE_ANY.search(first) or _SQ_THOUGHT.match(first) or _IT_THOUGHT.match(first) or re.search(r"\b(?:\w+ed|\w+ing)\b", first)):
        momentum -= 0.5

    # ----------------------------------------------------------------- reward
    hook = hooks_mod.analyze_hook(text, closing_hook_plan=closing_hook_plan, language=lang)
    payoffs = list(hook.micro_payoffs)
    reactions = len(_REACTION_SHOT.findall(text))
    under = len(_UNDERESTIMATION.findall(text))
    tiers = len(_TIER_WORDS.findall(text))
    tier_gain = bool(_TIER_GAIN.search(text)) or (windows >= 2 and tiers >= 2)
    # Genre wins the generic detector cannot see: a measured gain witnessed, or an underestimation answered by reaction shots.
    if tier_gain and reactions >= 1 and "measured_gain" not in payoffs:
        payoffs.append("measured_gain")
    if under >= 1 and reactions >= 2 and "face_slap" not in payoffs:
        payoffs.append("face_slap")
    metrics.update({"micro_payoffs": len(payoffs), "reaction_shots": reactions, "underestimation_cues": under, "tier_mentions": tiers, "tier_gain": 1.0 if tier_gain else 0.0})
    reward = 8.0
    is_grounding = (chapter_number == 1) or (pacing_mode == "grounding")
    if len(payoffs) < r.dopamine_per_chapter:
        if not is_grounding:
            reward -= 3.0 if not payoffs else 1.5
            findings.append(_finding("reward_missing", "high" if not payoffs else "medium", f"{len(payoffs)} earned win(s) detected; the profile promises ≥{r.dopamine_per_chapter} per chapter" + (f" ({', '.join(e.reward_types[:3])}…)" if e.reward_types else ""), "Land one concrete win before the last beat: a deduction, a measured gain, a doubter proven wrong, a verbal victory — shown, with a witness"))
        else:
            if not payoffs:
                reward -= 0.5
    if under >= 1 and reactions == 0 and e.face_slap_cadence != "none":
        reward -= 1.5
        findings.append(_finding("reversal_without_reaction", "medium", "The protagonist is underestimated but no onlooker reaction is shown", "When the reversal lands, cut to the doubter's face, the room's murmur, one re-evaluation"))
    elif reactions >= 2 and (payoffs or under):
        reward += 0.5
    if e.progression_axis and tiers == 0 and words >= 1500 and e.subgenre in ("hunter_gate", "system_apocalypse", "tower_climb", "dungeon", "game_litrpg", "cultivation", "martial_arts_murim", "academy"):
        reward -= 0.5

    # ----------------------------------------------------------------- ending
    ending = float(hook.strength)
    last = paras[-1] if paras else ""
    metrics.update({"hook_strength": hook.strength, "hook_type_weight": 1.0 if hook.hook_type != "none" else 0.0, "last_paragraph_units": count_units(last, lang) if last else 0})
    if hook.is_soft:
        findings.append(_finding("soft_ending", "high", f"Ending is a soft {hook.ending_class.replace('_', ' ')}: nothing pulls the reader to the next chapter", f"Rewrite the final lines as a {hook.suggested_hook.replace('_', ' ')} hook: short, concrete, no moral", hook.tail_excerpt[-140:]))
    elif c.hook_in_last_line and last and count_units(last, lang) > 45:
        ending -= 1.0
        findings.append(_finding("long_last_paragraph", "low", "The last paragraph is long; the hook should be one or two lines", "Cut the final paragraph to the line that lands the problem", last[-140:]))
    if last and re.search(r"\b(?:and (?:that|this) was (?:the|how|when)|(?:I|he|she|they) (?:had )?learned that|the lesson|what (?:it|this) meant)\b", last, re.I):
        ending -= 2.0
        findings.append(_finding("closing_moral", "high", "The chapter closes on a moral / meaning statement", "End on an action, a line of dialogue or a concrete new problem", last[-140:]))

    scores = {"rhythm": _clamp(rhythm), "inner_voice": _clamp(inner), "conventions": _clamp(conv), "momentum": _clamp(momentum), "reward": _clamp(reward), "ending": _clamp(ending)}
    weights = {"rhythm": 1.2, "inner_voice": 1.5, "conventions": 1.0, "momentum": 1.0, "reward": 1.4, "ending": 1.3}
    overall = sum(scores[k] * weights[k] for k in scores) / sum(weights.values())
    passed = overall >= 6.5 and not any(f.severity == "critical" for f in findings)
    return WebnovelConformance(scores=scores, overall=round(overall, 2), metrics=metrics, findings=findings, passed=passed)


__all__ = ["measure_conformance"]
