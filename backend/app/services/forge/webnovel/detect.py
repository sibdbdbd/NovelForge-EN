"""Derive a Webnovel Style Profile from what we already know: the author's inputs and the source fingerprint.

Authority order (highest first):
1. explicit author fields (platform, subgenre, perspective, options passed to Create Novel)
2. cues in the author's brief / genre / tags
3. measurable signals in the source Narrative Fingerprint (POV, paragraph rhythm,
   inner-thought share, status windows, humor, reward cadence) and the source's
   abstract scene functions
4. the subgenre template defaults

Nothing here reads source *content*: only the fingerprint's numbers and the
abstract function tags the analysis already produced.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.schemas.webnovel import WebnovelStyleProfile
from app.services.forge.webnovel.templates import guess_subgenre, template_for

_VALID_PLATFORMS = {"novelpia", "munpia", "kakaopage", "naver_series", "royalroad", "generic"}
_VALID_PERSPECTIVES = {"first_person", "third_limited", "third_close_alternating"}
_VALID_REGISTERS = {"dry_cynical", "deadpan_pragmatic", "cold_calculating", "warm_wry", "manic_comic", "grim_survivor", "sardonic_noble", "earnest_underdog"}


def _median(d: Any, default: float = 0.0) -> float:
    if isinstance(d, dict):
        try:
            return float(d.get("median", default) or default)
        except (TypeError, ValueError):
            return default
    try:
        return float(d)
    except (TypeError, ValueError):
        return default


def _features(fp: Dict[str, Any], layer: str) -> Dict[str, Any]:
    layers = fp.get("layers") or {}
    lyr = layers.get(layer) or {}
    return lyr.get("features") or {}


def fingerprint_signals(fp: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Compact, model-free reading of the fingerprint the detector reasons over."""
    if not fp:
        return {}
    pov = _features(fp, "pov_focalization")
    rhythm = _features(fp, "rhythm")
    inner = _features(fp, "internal_monologue")
    humor = _features(fp, "humor")
    reward = _features(fp, "pacing_reward")
    per_chapter = fp.get("per_chapter_metrics") or []
    status_windows = 0
    for m in per_chapter:
        if isinstance(m, dict):
            status_windows += int(m.get("status_window_count") or 0)
    ending = _features(fp, "chapter_ending")
    return {
        "language": fp.get("language"),
        "pov": pov.get("pov"),
        "pov_stability": float(pov.get("pov_stability") or 0.0),
        "short_paragraph_ratio": _median(rhythm.get("short_paragraph_ratio")),
        "paragraph_len_mean": _median(rhythm.get("paragraph_len_mean")),
        "chapter_units": _median(rhythm.get("chapter_units")),
        "internal_thought_ratio": _median(inner.get("internal_thought_ratio")),
        "humor_mean": _median(humor.get("humor_score_mean")) if isinstance(humor.get("humor_score_mean"), (int, float, dict)) else 0.0,
        "reward_gap_median": _median(reward.get("reward_gap_chapters"), 1.0),
        "status_windows_total": status_windows,
        "chapters_measured": int(fp.get("chapters_measured") or len(per_chapter) or 0),
        "ending_types": ending.get("ending_types") or {},
    }


def _scene_function_blob(source_functions: Iterable[str]) -> str:
    return " ".join(str(f).replace("_", " ") for f in source_functions)


def detect_profile(
    *,
    options: Optional[Dict[str, Any]] = None,
    brief: str = "",
    fingerprint: Optional[Dict[str, Any]] = None,
    source_scene_functions: Sequence[str] = (),
    source_genre_hint: str = "",
    words_per_chapter: Optional[int] = None,
) -> WebnovelStyleProfile:
    opts = dict(options or {})
    notes: List[str] = []

    # 1. subgenre: explicit > brief cues > source hint/functions > custom
    explicit = str(opts.get("subgenre") or "").strip().lower()
    subgenre = explicit if explicit and explicit != "custom" else None
    if subgenre:
        notes.append(f"subgenre '{subgenre}' set by the author")
    else:
        guess = guess_subgenre(brief, str(opts.get("genre") or ""), str(opts.get("tags") or ""), str(opts.get("summary") or ""), str(opts.get("notes") or ""))
        if guess:
            subgenre = guess
            notes.append(f"subgenre '{guess}' inferred from the author's brief / genre / tags")
        else:
            guess = guess_subgenre(source_genre_hint, _scene_function_blob(source_scene_functions))
            if guess:
                subgenre = guess
                notes.append(f"subgenre '{guess}' inferred from the reference's abstract structure (genre hint and scene functions)")
    profile = template_for(subgenre)
    profile.derived_from = "author" if explicit else ("detected" if subgenre else "default")

    # 2. platform
    platform = str(opts.get("platform") or "").strip().lower()
    if platform in _VALID_PLATFORMS:
        profile.platform = platform  # type: ignore[assignment]
        notes.append(f"platform '{platform}' set by the author")
    elif subgenre in ("game_litrpg",):
        profile.platform = "royalroad"
    elif subgenre in ("villainess_transmigration", "romance_fantasy"):
        profile.platform = "kakaopage"

    sig = fingerprint_signals(fingerprint)

    # 3. perspective: explicit > fingerprint POV > template
    persp = str(opts.get("perspective") or "").strip().lower()
    if persp in _VALID_PERSPECTIVES:
        profile.perspective = persp  # type: ignore[assignment]
        notes.append(f"perspective '{persp}' set by the author")
    elif sig.get("pov") in ("first_person", "third_person") and float(sig.get("pov_stability") or 0) >= 0.6:
        profile.perspective = "first_person" if sig["pov"] == "first_person" else "third_limited"
        notes.append(f"perspective '{profile.perspective}' learned from the reference (POV stability {sig['pov_stability']:.0%})")

    # 4. register
    reg = str(opts.get("narrator_register") or opts.get("register") or "").strip().lower()
    if reg in _VALID_REGISTERS:
        profile.narrator_register = reg  # type: ignore[assignment]
    elif sig and float(sig.get("humor_mean") or 0) >= 6.0 and profile.narrator_register in ("dry_cynical", "deadpan_pragmatic"):
        profile.narrator_register = "manic_comic" if float(sig["humor_mean"]) >= 7.5 else "warm_wry"
        notes.append(f"register lifted toward comedy (reference humor ≈{sig['humor_mean']:.1f}/10)")

    # 5. narration conventions from measurable rhythm
    if sig:
        spr = float(sig.get("short_paragraph_ratio") or 0)
        if spr >= 0.6:
            profile.narration.paragraph_rhythm = "one_line"
        elif spr >= 0.35:
            profile.narration.paragraph_rhythm = "short"
        else:
            profile.narration.paragraph_rhythm = "mixed"
        notes.append(f"paragraph rhythm '{profile.narration.paragraph_rhythm}' from reference short-paragraph share {spr:.0%}")
        itr = float(sig.get("internal_thought_ratio") or 0)
        profile.narration.thought_density = "dense" if itr >= 0.18 else ("regular" if itr >= 0.08 else "sparse")
        profile.reader.interiority_share_target = max(0.12, min(0.45, round(0.18 + itr * 0.6, 2)))
        if int(sig.get("status_windows_total") or 0) >= max(3, int(sig.get("chapters_measured") or 1) // 4):
            profile.narration.windows_enabled = True
            notes.append("status/system windows enabled: the reference uses bracketed windows regularly")
        gap = float(sig.get("reward_gap_median") or 1.0)
        profile.reader.reward_gap_max_chapters = int(max(1, min(4, round(gap) + 1)))
        if sig.get("language") == "ko":
            profile.narration.address = "korean_honorifics"
            profile.narration.sfx_density = "regular"
            notes.append("reference is Korean: honorific address logic and SFX lines enabled")

    # 6. chapter shape
    wpc = words_per_chapter or opts.get("words_per_chapter")
    if wpc:
        try:
            profile.chapter.words_target = max(600, min(12000, int(wpc)))
        except (TypeError, ValueError):
            pass
    elif sig.get("chapter_units") and sig.get("language") == "en":
        profile.chapter.words_target = int(max(1200, min(6000, round(sig["chapter_units"] / 100.0) * 100)))
        notes.append(f"chapter length ≈{profile.chapter.words_target} words from the reference median")

    # 7. author options that map onto reader experience
    rl = str(opts.get("romance_level") or "").lower()
    if rl == "none":
        profile.reader.romance_mode = "none"
    elif rl == "central":
        profile.reader.romance_mode = "central"
    elif rl == "subplot":
        profile.reader.romance_mode = "slow_burn_subplot"
    rating = str(opts.get("content_rating") or "").lower()
    if rating == "all ages":
        profile.reader.violence_level = "low"
    elif rating == "mature":
        profile.reader.violence_level = "high" if profile.reader.violence_level != "low" else "moderate"
    intensity = str(opts.get("genre_intensity") or "").lower()
    if intensity == "intense":
        profile.engine.face_slap_cadence = "every_arc" if profile.engine.face_slap_cadence == "regular" else profile.engine.face_slap_cadence
        profile.reader.dopamine_per_chapter = max(profile.reader.dopamine_per_chapter, 2)
    elif intensity == "subtle":
        profile.engine.face_slap_cadence = "occasional"
    if str(opts.get("thought_style") or "").lower() in ("single_quotes", "italics", "em_dash", "plain"):
        profile.narration.thought_style = str(opts["thought_style"]).lower()  # type: ignore[assignment]
    if "status_windows" in opts:
        profile.narration.windows_enabled = bool(opts["status_windows"])
    if str(opts.get("comedy_level") or "").lower() in ("none", "dry", "regular", "high"):
        profile.reader.comedy_level = str(opts["comedy_level"]).lower()  # type: ignore[assignment]

    profile.detection_notes = "; ".join(notes) if notes else "template defaults (no author fields, no fingerprint signals)"
    profile.updated_at = datetime.now().isoformat(timespec="seconds")
    return profile


__all__ = ["detect_profile", "fingerprint_signals"]
