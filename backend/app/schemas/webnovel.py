"""Webnovel Style Profile: the Korean-webnovel identity of a novel, as data.

The pipeline used to carry "write like a Korean webnovel" as one paragraph of
advice inside a single prompt. This module makes that identity a first-class,
persisted, measurable object:

- ``WebnovelStyleProfile`` — one singleton card per original project. It names
  the target platform, the subgenre template, the narration conventions the
  prose must use (inner-thought quoting, status windows, sound effects, one-line
  paragraph rhythm, address forms), the reward cadence and the chapter-ending
  discipline. Every drafting, critic, polish and hook prompt receives its
  rendered form, so chapter 300 obeys the same conventions as chapter 1.
- ``WebnovelConformance`` — a deterministic per-chapter scorecard (no model
  call) computed by ``services.forge.webnovel.conformance`` and merged into the
  Prose Craft critic as extra dimensions.
- ``AuthorDirective`` — the author's steering notes, scoped to the whole novel,
  an arc, or one chapter, injected into planning and drafting prompts in the
  Story Charter's authority position.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

WEBNOVEL_STYLE_VERSION = "webnovel-style-1"

SYSTEM = {"x-ai-exclude": True}

Platform = Literal["novelpia", "munpia", "kakaopage", "naver_series", "royalroad", "generic"]
Subgenre = Literal[
    "regression", "system_apocalypse", "hunter_gate", "tower_climb", "dungeon", "villainess_transmigration", "academy",
    "martial_arts_murim", "cultivation", "reincarnated_noble", "modern_fantasy", "game_litrpg", "office_life", "romance_fantasy",
    "isekai_return", "apocalypse_survival", "sports", "entertainment_industry", "historical_transmigration", "custom",
]
ThoughtStyle = Literal["single_quotes", "italics", "em_dash", "plain"]
WindowStyle = Literal["square_brackets", "angle_brackets", "none"]
SfxStyle = Literal["em_dash", "bare", "none"]
AddressConvention = Literal["korean_honorifics", "western_titles", "mixed", "minimal"]
Perspective = Literal["first_person", "third_limited", "third_close_alternating"]
NarrativeDistance = Literal["very_close", "close", "medium"]
Register = Literal["dry_cynical", "deadpan_pragmatic", "cold_calculating", "warm_wry", "manic_comic", "grim_survivor", "sardonic_noble", "earnest_underdog"]


class NarrationConventions(BaseModel):
    """Surface conventions that make prose *read* like a Korean webnovel in English."""

    thought_style: ThoughtStyle = Field(default="single_quotes", description="How the POV's direct inner speech is marked: 'single quotes' (Korean webnovel standard), italics, em-dash asides or plain narration")
    thought_density: Literal["sparse", "regular", "dense"] = Field(default="dense", description="How often direct inner speech appears; 'dense' = several per scene")
    window_style: WindowStyle = Field(default="square_brackets", description="Status / skill / system message boxes, when the genre has them")
    windows_enabled: bool = Field(default=False, description="Whether [System] windows exist in this world at all")
    sfx_style: SfxStyle = Field(default="em_dash", description="Sound-effect lines: 'Bang—' / 'Thud.' on their own line, bare, or none")
    sfx_density: Literal["none", "light", "regular"] = Field(default="light")
    address: AddressConvention = Field(default="mixed", description="How characters address each other: Korean honorific logic rendered in English (Senior, Team Leader, Young Master, -nim as a title word), Western titles, mixed, or minimal")
    paragraph_rhythm: Literal["one_line", "short", "mixed"] = Field(default="one_line", description="Dominant paragraph length: one sentence per paragraph (mobile-first), 1-3 sentences, or mixed")
    line_break_beats: bool = Field(default=True, description="Whether a blank line is used as a beat of silence / a punch before a reveal")
    chapter_title_style: Literal["numbered_only", "numbered_with_title", "title_only", "episode"] = Field(default="numbered_with_title", description="e.g. 'Chapter 12', 'Chapter 12 — The Bidding', 'Episode 12'")
    tense: Literal["past", "present"] = Field(default="past")
    onomatopoeia_english: List[str] = Field(default_factory=lambda: ["Thud.", "Crack—", "Bang!", "Click.", "Whoosh—", "Tap, tap.", "Creak.", "Clang!", "Rustle.", "Splash."], description="Allowed English SFX forms")


class GenreEngine(BaseModel):
    """The subgenre's progression / reward machinery, so planning and drafting agree on what a 'win' is."""

    subgenre: Subgenre = Field(default="custom")
    progression_axis: str = Field(default="", description="What measurably grows: rank, level, stat, cultivation stage, wealth, influence, skill mastery")
    tier_ladder: List[str] = Field(default_factory=list, description="Named tiers from lowest to highest, e.g. F, E, D, C, B, A, S, SS; or Qi Refining → Foundation → Core...")
    reward_types: List[str] = Field(default_factory=list, description="Kinds of dopamine the genre delivers: face-slap, hidden-talent reveal, loot/skill gain, humiliation reversal, expert recognition, sudden wealth, foresight cash-in, romance flag")
    face_slap_cadence: Literal["none", "occasional", "regular", "every_arc"] = Field(default="regular", description="How often a doubter is publicly proven wrong")
    knowledge_advantage: str = Field(default="", description="The protagonist's unfair edge (regression memory, system, modern knowledge, hidden bloodline) and its rules")
    world_hooks: List[str] = Field(default_factory=list, description="World-level engines that manufacture episodes: rankings, auctions, tournaments, gates, dungeon floors, exams, guild politics")
    typical_arc_shape: str = Field(default="", description="How an arc of this subgenre usually runs (setup → underestimation → escalating test → public reversal → new tier → new threat)")
    genre_vocabulary: List[str] = Field(default_factory=list, description="Terms the prose may use natively: Awakened, Gate, Rank, Skill, Constellation, Regressor, Murim, Dao, Mana, Aura...")


class ReaderExperience(BaseModel):
    """What the reader is paying for and how often they get paid."""

    core_fantasy: str = Field(default="", description="One line: the wish the novel fulfils (competence, revenge, being finally seen, building an empire...)")
    dopamine_per_chapter: int = Field(default=1, ge=0, le=4, description="Minimum earned wins per chapter")
    reward_gap_max_chapters: int = Field(default=2, ge=1, le=10, description="Longest allowed run of chapters without a real payoff")
    emotional_palette: List[str] = Field(default_factory=list, description="Feelings to hit regularly: vindication, awe, dread, warmth, wry amusement, righteous fury")
    comedy_level: Literal["none", "dry", "regular", "high"] = Field(default="dry")
    romance_mode: Literal["none", "slow_burn_subplot", "central", "harem_adjacent_no", "found_family"] = Field(default="slow_burn_subplot")
    violence_level: Literal["low", "moderate", "high"] = Field(default="moderate")
    interiority_share_target: float = Field(default=0.28, ge=0.05, le=0.6, description="Fraction of sentences that should carry the POV's private processing")


class ChapterShape(BaseModel):
    """Serial-episode discipline."""

    words_target: int = Field(default=2500, ge=600, le=12000)
    opening_rule: str = Field(default="Open inside an action, a line of dialogue or a sharp private thought; never with recap or weather.")
    ending_rule: str = Field(default="The last paragraph is a crisis, revelation, decision, threat arrival or reversal — one or two lines, no moral.")
    hook_in_last_line: bool = Field(default=True)
    min_scenes: int = Field(default=2, ge=1, le=6)
    max_scenes: int = Field(default=4, ge=1, le=8)
    recap_allowed: bool = Field(default=False, description="Whether the opening may restate the previous chapter (webnovels: no)")
    author_note_style: Literal["none", "short", "chatty"] = Field(default="none", description="Optional end-of-chapter author's note in the export")


class WebnovelStyleProfile(BaseModel):
    """The novel's webnovel identity — one singleton card per original project."""

    version: str = Field(default=WEBNOVEL_STYLE_VERSION, json_schema_extra=SYSTEM)
    platform: Platform = Field(default="novelpia", description="Target platform whose front-page conventions the prose imitates")
    perspective: Perspective = Field(default="first_person")
    narrative_distance: NarrativeDistance = Field(default="very_close")
    narrator_register: Register = Field(default="dry_cynical", description="Dominant narratorial register")
    narration: NarrationConventions = Field(default_factory=NarrationConventions)
    engine: GenreEngine = Field(default_factory=GenreEngine)
    reader: ReaderExperience = Field(default_factory=ReaderExperience)
    chapter: ChapterShape = Field(default_factory=ChapterShape)
    banned_moves: List[str] = Field(default_factory=lambda: [
        "recap openings", "explaining the theme", "narrator moralising", "dialogue that states the speaker's want directly",
        "long unbroken speeches", "Western literary metaphor stacking", "epiphany stamps ('in that moment')", "emotion cocktails",
    ])
    signature_moves: List[str] = Field(default_factory=lambda: [
        "one-line private verdicts after another character speaks", "the protagonist notices the price/exit/lie first",
        "a public underestimation reversed on the page", "a cold calculation delivered deadpan", "the last line lands a new problem",
    ])
    derived_from: Literal["author", "detected", "default"] = Field(default="default", json_schema_extra=SYSTEM)
    detection_notes: str = Field(default="", description="How the profile was derived from the reference (fingerprint signals), for the author's eyes", json_schema_extra=SYSTEM)
    updated_at: str = Field(default="", json_schema_extra=SYSTEM)


# ------------------------------------------------------------------ conformance
class ConformanceFinding(BaseModel):
    code: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    quote: str = ""
    problem: str
    fix: str = ""


class WebnovelConformance(BaseModel):
    """Deterministic per-chapter measurement against the profile."""

    version: str = Field(default=WEBNOVEL_STYLE_VERSION)
    scores: Dict[str, int] = Field(default_factory=dict, description="1-10 per dimension: rhythm, inner_voice, conventions, momentum, reward, ending")
    overall: float = Field(default=0.0, ge=0.0, le=10.0)
    metrics: Dict[str, float] = Field(default_factory=dict)
    findings: List[ConformanceFinding] = Field(default_factory=list)
    passed: bool = True


# ------------------------------------------------------------------- directives
DirectiveScope = Literal["novel", "arc", "chapter"]
DirectiveKind = Literal["must", "prefer", "avoid", "idea"]


class AuthorDirective(BaseModel):
    """One steering note from the author. Scope decides which prompts receive it."""

    id: str = Field(default="", json_schema_extra=SYSTEM)
    scope: DirectiveScope = Field(default="novel")
    chapter_from: int = Field(default=0, ge=0, description="First chapter this applies to (chapter/arc scope); 0 = n/a")
    chapter_to: int = Field(default=0, ge=0, description="Last chapter (inclusive) this applies to; 0 = same as chapter_from")
    kind: DirectiveKind = Field(default="must")
    text: str = Field(description="The author's note, in their own words")
    applies_to: List[Literal["planning", "drafting", "critic", "export"]] = Field(default_factory=lambda: ["planning", "drafting"])
    created_at: str = Field(default="", json_schema_extra=SYSTEM)
    consumed_by_chapters: List[int] = Field(default_factory=list, json_schema_extra=SYSTEM, description="Chapters whose drafts already received this directive")
    active: bool = Field(default=True)


class DirectiveBook(BaseModel):
    """Singleton card: every directive the author has issued for a project."""

    version: str = Field(default=WEBNOVEL_STYLE_VERSION, json_schema_extra=SYSTEM)
    directives: List[AuthorDirective] = Field(default_factory=list)
    updated_at: str = Field(default="", json_schema_extra=SYSTEM)


__all__ = [
    "WEBNOVEL_STYLE_VERSION", "AddressConvention", "AuthorDirective", "ChapterShape", "ConformanceFinding", "DirectiveBook", "DirectiveKind", "DirectiveScope",
    "GenreEngine", "NarrationConventions", "NarrativeDistance", "Perspective", "Platform", "ReaderExperience", "Register", "SfxStyle", "Subgenre", "ThoughtStyle",
    "WebnovelConformance", "WebnovelStyleProfile", "WindowStyle",
]
