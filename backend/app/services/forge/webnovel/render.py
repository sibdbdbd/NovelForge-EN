"""Prompt blocks rendered from a Webnovel Style Profile and the author's directives.

Three consumers, three shapes:
- planning (storylines, architecture, chapter plan): the genre engine, arc shape, reward cadence
- drafting (draft, scene, repair, polish, hook): the concrete on-the-page conventions
- critic: what to grade against, in the critic's language

Deterministic; no model calls. Author directives are rendered separately with
``render_directives`` so they can sit next to the Story Charter at the top of
the prompt (the author outranks the profile, the profile outranks the model).
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from app.schemas.webnovel import AuthorDirective, WebnovelStyleProfile
from app.services.forge.webnovel.templates import PLATFORM_NOTES, SUBGENRE_LABELS

_REGISTER_TEXT = {
    "dry_cynical": "dry, cynical, quick private verdicts; the narrator is funnier in their head than in their mouth",
    "deadpan_pragmatic": "deadpan and practical; treats the extraordinary as a logistics problem; understatement is the joke",
    "cold_calculating": "cold, precise, counts costs and exits; emotion leaks only through what the narrator refuses to look at",
    "warm_wry": "warm and wry; notices people kindly and skewers them gently; sincerity allowed once per scene",
    "manic_comic": "fast, comic, self-aware; the interior voice argues with itself; punchlines land on their own line",
    "grim_survivor": "grim, terse, sensory; short declaratives under pressure; humor is gallows humor and rare",
    "sardonic_noble": "sardonic, polished, aware of every rule of the room and which ones to break; courtesy as a blade",
    "earnest_underdog": "earnest, determined, honest about fear; wins are felt fully; no cynicism in the interior voice",
}

_THOUGHT_TEXT = {
    "single_quotes": "Mark the POV's direct inner speech with single quotes on its own line — 'So that's how it is.' — the Korean webnovel standard. Spoken dialogue uses double quotes. Never italics for thought.",
    "italics": "Mark the POV's direct inner speech with *italics* on its own line; spoken dialogue uses double quotes.",
    "em_dash": "Render the POV's direct inner speech as em-dash asides — like this — inside narration; spoken dialogue uses double quotes.",
    "plain": "Render inner speech as plain free-indirect narration in the POV's idiom; spoken dialogue uses double quotes.",
}

_WINDOW_TEXT = {
    "square_brackets": "System / status / skill windows are rendered as their own centred-looking lines in square brackets, e.g. [Skill acquired: Ledger Sight (Rank F)] or a multi-line [Status] block. Keep windows terse; the POV's one-line dry reaction follows immediately.",
    "angle_brackets": "System / status / skill windows are rendered in angle brackets on their own lines, e.g. <Quest complete>. Keep them terse; the POV's one-line reaction follows immediately.",
    "none": "No system windows.",
}

_SFX_TEXT = {
    "em_dash": "Sound effects may stand alone as a short line ending in an em-dash or period ('Thud—', 'Click.') at moments of impact; at most a few per chapter.",
    "bare": "Sound effects may stand alone as a short bare line ('Thud.') at moments of impact; at most a few per chapter.",
    "none": "No stand-alone sound-effect lines.",
}

_ADDRESS_TEXT = {
    "korean_honorifics": "Address follows Korean honorific logic rendered in natural English: titles as address ('Team Leader', 'Senior', 'Young Master', 'Elder', 'Hunter Park'), family-name-plus-title for distance, given name only for intimacy; the shift between them is a plot event. Never transliterate suffixes (-nim, -ssi) — translate them into title words or distance.",
    "western_titles": "Address uses Western titles and surnames for distance, given names for intimacy; the shift between them is a plot event.",
    "mixed": "Address mixes natural English titles ('Team Leader', 'Captain', 'Young Master', 'Senior') with names; distance vs. intimacy in address is deliberate and changes are plot events.",
    "minimal": "Minimal titling; characters mostly use names.",
}

_RHYTHM_TEXT = {
    "one_line": "Paragraphs are mostly ONE sentence. Two at most. A blank line is a beat. Dialogue, inner speech, SFX and windows each get their own line. Mobile-first: the eye should fall down the page.",
    "short": "Paragraphs are one to three sentences; dialogue and inner speech on their own lines; white space is pacing.",
    "mixed": "Paragraphs vary from one line to five sentences; tense moments go short, reflective moments may run longer; dialogue on its own line.",
}


def subgenre_label(profile: WebnovelStyleProfile) -> str:
    return SUBGENRE_LABELS.get(profile.engine.subgenre, profile.engine.subgenre.replace("_", " "))


def render_for_drafting(profile: WebnovelStyleProfile, *, max_chars: int = 3600) -> str:
    n, e, r, c = profile.narration, profile.engine, profile.reader, profile.chapter
    # Ordered by importance: when the budget bites, the tail (platform note, palette, vocabulary) goes first.
    core: List[str] = []
    core.append(f"Target: an English-language {subgenre_label(profile)} webnovel to {profile.platform.replace('_', ' ')} front-page standards. Perspective: {profile.perspective.replace('_', ' ')}, distance {profile.narrative_distance.replace('_', ' ')}. Register: {_REGISTER_TEXT.get(profile.narrator_register, profile.narrator_register)}.")
    core.append("ON THE PAGE:")
    core.append(f"- Rhythm: {_RHYTHM_TEXT[n.paragraph_rhythm]}")
    core.append(f"- Inner speech ({n.thought_density}): {_THOUGHT_TEXT[n.thought_style]} Give the POV's private verdict after most significant lines other characters speak.")
    if n.windows_enabled:
        core.append(f"- Windows: {_WINDOW_TEXT[n.window_style]}")
    else:
        core.append("- Windows: this world has no system windows; power is shown through effect and other people's reactions.")
    if n.sfx_density != "none":
        core.append(f"- SFX ({n.sfx_density}): {_SFX_TEXT[n.sfx_style]} Forms: {', '.join(n.onomatopoeia_english[:6])}.")
    core.append(f"- Address: {_ADDRESS_TEXT[n.address]}")
    core.append(f"- Tense: {n.tense}. Opening: {c.opening_rule} Ending: {c.ending_rule}" + (" The hook must be in the final line." if c.hook_in_last_line else "") + ("" if c.recap_allowed else " No recap of the previous chapter."))
    core.append("REWARDS:")
    core.append(f"- Core fantasy: {r.core_fantasy or 'competence recognised'}. At least {r.dopamine_per_chapter} earned win(s) this chapter" + (f" — kinds: {'; '.join(e.reward_types[:5])}." if e.reward_types else "."))
    if e.face_slap_cadence != "none":
        core.append(f"- Face-slap cadence '{e.face_slap_cadence}': when someone underestimates the protagonist, the reversal happens ON THE PAGE with onlooker reaction shots (the doubter's face, a murmur, a re-evaluation). Never summarise a reversal.")
    if e.progression_axis:
        core.append(f"- Progression is measurable: {e.progression_axis}." + (f" Ladder: {' → '.join(e.tier_ladder)}." if e.tier_ladder else "") + " Show the measurement and one witness registering it.")
    if e.knowledge_advantage:
        core.append(f"- Unfair edge: {e.knowledge_advantage} Use it visibly; sometimes pay a cost for it.")
    core.append(f"- Interiority target ≈{int(r.interiority_share_target * 100)}% of sentences (noticing, pricing, misreading, grading people).")
    if profile.banned_moves:
        core.append("BANNED: " + "; ".join(profile.banned_moves[:10]) + ".")
    if profile.signature_moves:
        core.append("SIGNATURE MOVES (use several): " + "; ".join(profile.signature_moves[:7]) + ".")
    tail: List[str] = []
    if e.genre_vocabulary:
        tail.append(f"- Genre vocabulary is native and unexplained: {', '.join(e.genre_vocabulary[:12])}.")
    if r.emotional_palette:
        tail.append(f"- Palette: {', '.join(r.emotional_palette)}. Comedy: {r.comedy_level}. Romance: {r.romance_mode.replace('_', ' ')}. Violence: {r.violence_level}.")
    note = PLATFORM_NOTES.get(profile.platform, "")
    if note:
        tail.append(f"- Platform: {note}")
    text = "\n".join(core)
    for line in tail:
        if len(text) + 1 + len(line) > max_chars:
            break
        text = text + "\n" + line
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def render_for_planning(profile: WebnovelStyleProfile, *, max_chars: int = 2600) -> str:
    e, r, c = profile.engine, profile.reader, profile.chapter
    lines: List[str] = [f"Genre engine: {subgenre_label(profile)} for {profile.platform.replace('_', ' ')} readers. Core fantasy: {r.core_fantasy or 'competence recognised'}."]
    if e.progression_axis:
        lines.append(f"- Progression axis (must advance visibly across arcs): {e.progression_axis}." + (f" Tier ladder: {' → '.join(e.tier_ladder)}." if e.tier_ladder else ""))
    if e.knowledge_advantage:
        lines.append(f"- Protagonist's unfair edge and its rules: {e.knowledge_advantage}")
    if e.world_hooks:
        lines.append(f"- Episode-manufacturing world hooks (use them to generate arcs, not one-off scenes): {'; '.join(e.world_hooks)}.")
    if e.typical_arc_shape:
        lines.append(f"- Arc shape readers expect: {e.typical_arc_shape}.")
    if e.reward_types:
        lines.append(f"- Reward types to schedule: {'; '.join(e.reward_types)}. At least {r.dopamine_per_chapter} per chapter; never more than {r.reward_gap_max_chapters} consecutive chapters without a real payoff.")
    lines.append(f"- Face-slap cadence: {e.face_slap_cadence}. Plan the underestimation beat BEFORE the reversal beat so the reversal is earned on the page.")
    lines.append(f"- Every chapter ≈{c.words_target} words, {c.min_scenes}-{c.max_scenes} scenes, ends on a hook (crisis / revelation / decision / threat arrival / reversal). Vary chapter function; three identical dominant functions in a row is a planning error.")
    lines.append(f"- Romance mode: {r.romance_mode.replace('_', ' ')}. Comedy: {r.comedy_level}. Violence: {r.violence_level}.")
    lines.append("- Long-serial structure: each arc raises the tier of both threat and protagonist; each arc ends with a status change the world must acknowledge and a new antagonist tier stepping in.")
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def render_for_critic(profile: WebnovelStyleProfile, *, max_chars: int = 1800) -> str:
    n, e, r = profile.narration, profile.engine, profile.reader
    lines = [
        f"Grade as a {profile.platform.replace('_', ' ')} acquisitions editor for {subgenre_label(profile)}.",
        f"- Rhythm expected: {n.paragraph_rhythm.replace('_', ' ')} paragraphs; inner speech {n.thought_density} in {n.thought_style.replace('_', ' ')}; " + ("system windows present and terse" if n.windows_enabled else "no windows") + f"; address convention '{n.address.replace('_', ' ')}'.",
        f"- Register expected: {_REGISTER_TEXT.get(profile.narrator_register, profile.narrator_register)}.",
        f"- Reward expected: ≥{r.dopamine_per_chapter} earned win(s)" + (f" of kinds like {', '.join(e.reward_types[:4])}" if e.reward_types else "") + f"; face-slap cadence {e.face_slap_cadence}; reversals shown with onlooker reactions, never summarised.",
        "- Ending expected: the last line lands a new problem; no fade-out, no moral.",
        "- Penalise: Western literary metaphor stacking, essayistic narration, characters stating their wants directly, recap openings, exposition without conflict, interior voice that sounds like a therapist or a novelist instead of this narrator.",
    ]
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def directives_for(directives: Iterable[AuthorDirective], *, chapter: Optional[int] = None, consumer: str = "drafting") -> List[AuthorDirective]:
    out: List[AuthorDirective] = []
    for d in directives:
        if not d.active or consumer not in d.applies_to:
            continue
        if d.scope == "novel":
            out.append(d)
        elif chapter is not None:
            lo = int(d.chapter_from or 0)
            hi = int(d.chapter_to or d.chapter_from or 0)
            if lo and lo <= chapter <= max(lo, hi):
                out.append(d)
        elif d.scope == "arc":
            out.append(d)
    return out


def render_directives(directives: Sequence[AuthorDirective], *, chapter: Optional[int] = None, consumer: str = "drafting", max_chars: int = 2400, prefiltered: bool = False) -> str:
    """Author directives as a prompt block. Empty string when none apply. ``prefiltered`` renders the list as given."""
    rows = list(directives) if prefiltered else directives_for(directives, chapter=chapter, consumer=consumer)
    if not rows:
        return ""
    kinds = {"must": "MUST", "prefer": "PREFER", "avoid": "AVOID", "idea": "IDEA (use if it fits)"}
    lines: List[str] = []
    for d in rows:
        where = "whole novel" if d.scope == "novel" else (f"chapter {d.chapter_from}" if not d.chapter_to or d.chapter_to == d.chapter_from else f"chapters {d.chapter_from}-{d.chapter_to}")
        lines.append(f"- [{d.id or 'dir'}] {kinds.get(d.kind, d.kind.upper())} ({where}): {d.text.strip()}")
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


__all__ = ["directives_for", "render_directives", "render_for_critic", "render_for_drafting", "render_for_planning", "subgenre_label"]
