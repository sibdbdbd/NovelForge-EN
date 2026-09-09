"""System prompts and prompt builders for the craft passes.

Kept as code rather than DB-bootstrapped prompt cards because the pipeline
depends on their exact output contracts (JSON shapes, "prose only" rules) and
versions them for provenance.

Every pass speaks Korean-webnovel natively: the scene planner thinks in turns
and micro-payoffs, the critic grades as a Novelpia/Munpia acquisitions editor,
the polisher rewrites toward the Webnovel Style Profile, and the hook editor
lands the final line. The profile itself is passed in as ``style_text`` by the
pass so a project's own conventions (inner-speech marker, windows, address
forms) override these generic defaults.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from app.schemas.craft import CriticFinding, CriticReport, HookAnalysis, ScenePlan

SCENE_PLAN_PROMPT_VERSION = "craft-scene-plan-2"
CRITIC_PROMPT_VERSION = "craft-critic-2"
POLISH_PROMPT_VERSION = "craft-polish-2"
HOOK_PROMPT_VERSION = "craft-hook-2"

SCENE_DRAFT_DIRECTIVES = """[SCENE CRAFT — NON-NEGOTIABLE]
- Breathing room: the beats are a route, not a checklist. Each beat gets an entry (one concrete anchor, who is where), an exchange or action, the POV's private reaction, and a turn.
- Interiority before action: before anything important happens, the POV notices, prices, misjudges or privately comments. Readers stay for the head, not the plot.
- Outer composure / inner commentary: the spoken lines are controlled; the narration is where the sharpness, calculation and humor live. After most significant lines another character speaks, give the POV's private one-line verdict on its own line (in the profile's inner-speech marker).
- Subtext: nobody says what they want in their first line. Every line of dialogue is a move; the POV reads the moves and is sometimes wrong.
- Mobile rhythm: mostly one-sentence paragraphs; dialogue, inner speech, sound effects and system windows each on their own line; a blank line is a beat. No walls.
- Reversal on the page: when someone underestimates the POV and is proven wrong, show the doubter's face and the room's reaction. Never summarise a win.
- Banned: 'not X, but Y' scaffolds; 'a testament to'; 'the man who…'; 'something shifted'; 'a breath he didn't know he was holding'; 'in that moment'; emotion cocktails; therapy vocabulary; metaphor stacking; narrator lectures about what a moment 'meant'; recap of anything the reader just read."""

SCENE_PLAN_SYSTEM_PROMPT = (
    "You are a serialized-webnovel structure editor (Novelpia / Munpia / KakaoPage). You turn a chapter's ordered beats into 2-5 scenes that each have a place, a time, a dramatic question and a TURN. "
    "You think in reader rewards: where the underestimation beat sits, where the reversal lands, which scene carries the measurable gain, and which line ends the episode so the reader taps 'next'. "
    "You never add events, characters, locations or facts beyond the beats and allowed outcomes; you only decide where the scene boundaries fall, what each scene privately does for the protagonist, and which small win it lands. "
    "Return ONLY one JSON object matching the schema. No prose, no markdown fences."
)

CRITIC_SYSTEM_PROMPT = (
    "You are an adversarial acquisitions editor for top-tier Korean webnovels published in English (Novelpia / Munpia / KakaoPage front page; RoyalRoad Rising Stars). You are paid to find why a chapter would lose readers between this episode and the next. "
    "You grade 1-10 on: authenticity (does this read like a living webnovel narrator or like generic literary AI?), voice (is the POV's personality on every line?), interiority (private calculation, pricing, misreading, dry verdicts before and after action), "
    "dialogue (subtext, cadence, distinct speakers, address forms that mean something; no stiff exposition), pacing (mobile rhythm, breathing room per beat; no rushing, no idling), sensory (concrete anchors, not decoration), hook (does the last line land a new problem?), payoff (did the reader get the win they came for — measured gain, face-slap with reaction shots, deduction, verbal victory?). "
    "Cite short verbatim quotes (<= 25 words). Findings must be actionable rewrite instructions, not rewrites. Protect the strongest passage by naming it. "
    "Be harsh on: 'not X but Y' scaffolds, abstract-noun lecturing, epiphany stamps, emotion cocktails, therapy vocabulary, adverb-propped tags, Western literary metaphor stacking, characters stating their wants, characters explaining the theme, reversals summarised instead of shown, recap openings, and endings that fade instead of pulling. "
    "Return ONLY one JSON object: {\"scores\": {dimension: int}, \"overall\": float, \"verdict\": \"accept\"|\"polish\"|\"rewrite\", \"strongest_moment\": str, \"findings\": [{\"dimension\": str, \"severity\": \"critical\"|\"high\"|\"medium\"|\"low\", \"quote\": str, \"problem\": str, \"fix\": str}]}."
)

POLISH_SYSTEM_PROMPT = (
    "You are a line editor performing a surgical polish on a chapter of an original English-language Korean-style webnovel. You receive the chapter, the editor's cited findings, the protagonist's voice profile and the Webnovel Style Profile. "
    "Rewrite ONLY what the findings cite and the sentences immediately around them; leave every other sentence byte-identical. Never add a fact, name, place, object, injury, relationship change or piece of knowledge. "
    "Never change what happens or the order it happens in. Never touch the passage named as the strongest moment. Keep the POV, tense and the profile's conventions (inner-speech marker, window style, address forms, one-line rhythm). "
    "Replace tics with concrete, in-voice prose: a thing seen, a price counted, a dry private verdict on its own line, a line of dialogue. Where a finding asks for interiority, add 1-3 short lines in the POV's inner register at that spot. Where a finding asks for rhythm, split paragraphs at beats and put each spoken line on its own line. Where a finding asks for a reversal to be shown, add the doubter's reaction in one or two lines without adding facts. "
    "Return the complete chapter body only: no notes, no title, no metadata blocks."
)

HOOK_SYSTEM_PROMPT = (
    "You are a serialized-webnovel ending specialist. You rewrite ONLY the final paragraphs of a chapter so the reader must tap 'next episode'. "
    "Allowed hook types: crisis (something goes wrong now), revelation (the POV learns or the reader sees something that reframes the chapter), decision (the POV commits to an irreversible course), threat arrival (someone or something is suddenly here), reversal (what seemed settled is not). "
    "Rules: use only characters, places and facts already present in the chapter or the plan; do not resolve anything; do not add new information the outline does not allow; do not explain the hook; the final line is short — an action, a line of dialogue, a system window, or a concrete image — and the problem it lands must be new. Never a maxim about what it all meant. "
    "Return only the rewritten final paragraphs (2-4 short paragraphs), nothing else."
)


def _ctx_sections(context: Any, keys: Sequence[str]) -> str:
    fn = getattr(context, "sections_text_for", None)
    return fn(keys) if callable(fn) else ""


def build_scene_plan_prompt(context: Any, beats: Sequence[Dict[str, Any]], draft_plan: Sequence[ScenePlan], pov: str, participants: Sequence[str], word_target: int, closing_hook: str, *, style_text: str = "") -> str:
    beat_lines = [f"{i + 1}. [{b.get('function') or 'beat'}] {str(b.get('description') or '')[:400]}" for i, b in enumerate(beats)]
    schema = {"planning_thinking": "string", "scenes": [{"index": 1, "title": "", "beat_indexes": [1, 2], "location": "", "story_time": "", "present": [pov], "dramatic_question": "", "entry_state": "", "exit_state": "", "turn": "", "interiority_focus": "", "micro_payoff": "", "word_share": 0.3}]}
    parts = [
        _ctx_sections(context, ("story_charter", "author_directives", "chapter_outline", "pov", "participants", "scene_state", "previous_tail", "allowed_outcomes", "prohibited")),
    ]
    if style_text:
        parts.append("[WEBNOVEL STYLE]\n" + style_text)
    parts += [
        "[ORDERED BEATS]\n" + "\n".join(beat_lines),
        f"[CONSTRAINTS]\nPOV: {pov}\nAllowed participants: {', '.join(participants)}\nWord target: {word_target}\nPlanned closing hook: {closing_hook or '(none recorded; choose the strongest honest hook the beats allow)'}\nEvery beat index 1..{len(beats)} must appear in exactly one scene, in order. 2-5 scenes. word_share values sum to 1.0.\nEach scene must TURN (a decision, revelation, reversal or escalation) and name what the protagonist is privately doing (interiority_focus) and one micro_payoff (a measured gain, a doubter proven wrong with a reaction shot, a deduction, a verbal victory, a comic beat or a status gain) where the beats allow one. The final scene's exit_state is the episode hook.",
        "[DETERMINISTIC DRAFT PLAN — improve on it or keep it]\n" + json.dumps([s.model_dump() for s in draft_plan], ensure_ascii=False),
        "[OUTPUT SCHEMA]\n" + json.dumps(schema, ensure_ascii=False),
    ]
    return "\n\n".join(parts)


def build_critic_prompt(context: Any, prose: str, pov: str, deterministic: CriticReport, *, style_text: str = "") -> str:
    det_findings = [f.model_dump() for f in deterministic.findings[:24]]
    parts = [_ctx_sections(context, ("story_charter", "author_directives", "reader_contract", "chapter_outline", "beats", "pov", "fingerprint"))]
    if style_text:
        parts.append("[WEBNOVEL STYLE — grade against this]\n" + style_text)
    parts += [
        f"[DETERMINISTIC PRE-SCAN — already found; do not repeat these, look past them]\nscores: {json.dumps(deterministic.scores)}\nfindings: {json.dumps(det_findings, ensure_ascii=False)}",
        f"[CHAPTER DRAFT — POV {pov}]\n{prose}",
        "Grade the draft. Be the editor who would reject it. Ask: would a reader who has 40 other novels in their library tap 'next episode' after the last line?",
    ]
    return "\n\n".join(parts)


def build_polish_prompt(context: Any, prose: str, findings: Sequence[CriticFinding], strongest: str, pov: str, voice_text: str, *, style_text: str = "") -> str:
    lines = []
    for i, f in enumerate(findings, start=1):
        loc = f"«{f.quote}»" if f.quote else "(whole chapter)"
        lines.append(f"{i}. [{f.dimension}/{f.severity}] {loc}\n   problem: {f.problem}\n   fix: {f.fix or 'rewrite in voice'}")
    parts = [_ctx_sections(context, ("story_charter", "author_directives", "pov", "pov_knowledge_boundary", "participants", "anti_hallucination", "prohibited")), f"[PROTAGONIST VOICE — {pov}]\n{voice_text}"]
    if style_text:
        parts.append("[WEBNOVEL STYLE — conventions to polish toward]\n" + style_text)
    parts += [
        "[EDITOR FINDINGS — fix each; touch nothing else]\n" + "\n".join(lines),
        f"[PROTECT — do not alter]\n{strongest or '(none named)'}",
        "[CHAPTER]\n" + prose,
    ]
    return "\n\n".join(parts)


def build_hook_prompt(context: Any, keep_tail: str, current_tail: str, hook: HookAnalysis, pov: str, closing_hook_plan: str, *, style_text: str = "") -> str:
    parts = [_ctx_sections(context, ("story_charter", "author_directives", "chapter_outline", "beats", "allowed_outcomes", "prohibited", "pov"))]
    if style_text:
        parts.append("[WEBNOVEL STYLE]\n" + style_text)
    parts += [
        f"[ENDING DIAGNOSIS]\ncurrent ending class: {hook.ending_class}; detected hook: {hook.hook_type}; strength {hook.strength}/10\nsuggested hook type: {hook.suggested_hook}\nplanned closing hook: {closing_hook_plan or '(none recorded)'}",
        f"[CHAPTER — LAST 2500 CHARACTERS BEFORE THE ENDING (context only; do not rewrite)]\n{keep_tail}",
        f"[CURRENT FINAL PARAGRAPHS — rewrite these]\n{current_tail}",
        f"Rewrite the final paragraphs as a {hook.suggested_hook.replace('_', ' ')} hook in {pov}'s voice. The last line must be short and land a new problem. Return only the new final paragraphs.",
    ]
    return "\n\n".join(parts)


__all__ = [
    "CRITIC_PROMPT_VERSION", "CRITIC_SYSTEM_PROMPT", "HOOK_PROMPT_VERSION", "HOOK_SYSTEM_PROMPT", "POLISH_PROMPT_VERSION", "POLISH_SYSTEM_PROMPT", "SCENE_DRAFT_DIRECTIVES", "SCENE_PLAN_PROMPT_VERSION", "SCENE_PLAN_SYSTEM_PROMPT",
    "build_critic_prompt", "build_hook_prompt", "build_polish_prompt", "build_scene_plan_prompt",
]
