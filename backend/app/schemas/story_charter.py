"""Story Charter: the author's requirements as a first-class, persistent record.

The Charter answers *what the author asked for* — separately from what the
Bible says is true about the world and from what Story Memory says has
happened on the page. It is written once when a project is created (from the
Create Novel form or a free-text brief), refined by the author at any time, and
rendered into **every** planning and generation prompt so requirements do not
evaporate after the first stages.

Three kinds of entries keep the model honest about what is fixed and what is
still the author's decision:

- ``requirements``  — things the novel must (or should) do; each carries a
  ``strength`` (``must`` | ``prefer``) and a ``scope`` telling generation
  where it applies.
- ``open_choices``  — things the author deliberately left undecided. Prompts
  must not silently turn these into permanent facts; the planner may propose
  options but the drafting model must keep them open.
- ``boundaries``    — content the novel must never include.

Every entry records ``source`` (``author`` | ``interpreted`` | ``imported``) so
the UI can show the author what the system inferred versus what they typed.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

STORY_CHARTER_VERSION = "story-charter-1"

RequirementStrength = Literal["must", "prefer"]
RequirementScope = Literal["whole_novel", "planning", "characters", "world", "prose", "ending", "chapter"]
EntrySource = Literal["author", "interpreted", "imported"]
RequirementCategory = Literal[
    "premise", "protagonist", "cast", "world", "progression", "relationships", "romance", "tone", "theme",
    "structure", "pacing", "prose", "content", "length", "ending", "other",
]


class CharterRequirement(BaseModel):
    """One requirement the novel must honour."""

    id: str = Field(description="Stable short id (e.g. 'req-3'); referenced by warnings and prompts")
    text: str = Field(description="The requirement, in the author's terms, one or two sentences")
    category: RequirementCategory = Field(default="other")
    strength: RequirementStrength = Field(default="must", description="'must' is non-negotiable; 'prefer' guides choices")
    scope: RequirementScope = Field(default="whole_novel", description="Where generation must apply it")
    source: EntrySource = Field(default="author", json_schema_extra={"x-ai-exclude": True})
    rationale: str = Field(default="", description="Why the system believes this is what the author wants (only for interpreted entries)")
    locked: bool = Field(default=True, description="Locked requirements are never rewritten by the system", json_schema_extra={"x-ai-exclude": True})


class OpenChoice(BaseModel):
    """Something the author intentionally left undecided."""

    id: str = Field(description="Stable short id (e.g. 'open-2')")
    topic: str = Field(description="What is undecided (e.g. 'the protagonist's family background')")
    options: List[str] = Field(default_factory=list, description="Directions the author would accept, if they named any")
    guidance: str = Field(default="", description="How the story may explore it without settling it permanently")
    decide_by: Literal["author", "planner", "either"] = Field(default="author", description="Who may settle this: only the author, the planner during architecture, or either")
    source: EntrySource = Field(default="author", json_schema_extra={"x-ai-exclude": True})


class CharterBoundary(BaseModel):
    """Content the novel must never include."""

    id: str = Field(description="Stable short id (e.g. 'no-1')")
    text: str = Field(description="What is off limits")
    severity: Literal["hard", "soft"] = Field(default="hard", description="'hard' blocks generation; 'soft' is avoided but not fatal")
    source: EntrySource = Field(default="author", json_schema_extra={"x-ai-exclude": True})


class ReferenceUsage(BaseModel):
    """How an imported reference novel may inform this one (never its content)."""

    reference_title: str = Field(default="", description="Reference title, for the author's eyes only")
    similarity: Literal["loose", "moderate", "close"] = Field(default="moderate", description="How closely to follow the reference's structure and rhythm")
    learn: List[str] = Field(default_factory=list, description="Qualities to learn from the reference (e.g. 'chapter-ending hooks', 'reward cadence')")
    never_reuse: List[str] = Field(default_factory=list, description="Always: names, settings, scenes, phrasing; plus anything the author adds")


class CharterInterpretation(BaseModel):
    """Model output when a free-text brief is turned into charter entries."""

    interpretation_thinking: str = Field(default="", description="Short reasoning: what the brief clearly fixes, what it leaves open, what it forbids")
    working_title: str = Field(default="")
    one_line_pitch: str = Field(default="", description="The novel in one sentence, in the author's terms")
    requirements: List[CharterRequirement] = Field(default_factory=list)
    open_choices: List[OpenChoice] = Field(default_factory=list)
    boundaries: List[CharterBoundary] = Field(default_factory=list)
    questions_for_author: List[str] = Field(default_factory=list, description="Up to 5 questions whose answers would most improve planning; never blockers")


class StoryCharter(BaseModel):
    """The persisted Charter (a singleton ``Story Charter`` card per project)."""

    version: str = Field(default=STORY_CHARTER_VERSION, json_schema_extra={"x-ai-exclude": True})
    working_title: str = Field(default="", description="Working title")
    one_line_pitch: str = Field(default="", description="The novel in one sentence")
    brief: str = Field(default="", description="The author's own description, verbatim; never rewritten by the system")
    audience: str = Field(default="", description="Who the novel is for (e.g. 'adult readers of Korean-style progression fantasy')")
    language: str = Field(default="English", description="Language of the prose")
    target_chapters: Optional[int] = Field(default=None, description="Planned chapter count, if decided")
    words_per_chapter: Optional[int] = Field(default=None, description="Planned words per chapter, if decided")
    reference: Optional[ReferenceUsage] = Field(default=None, description="How the imported reference may inform this novel")
    requirements: List[CharterRequirement] = Field(default_factory=list)
    open_choices: List[OpenChoice] = Field(default_factory=list)
    boundaries: List[CharterBoundary] = Field(default_factory=list)
    questions_for_author: List[str] = Field(default_factory=list, description="Open questions the system raised; the author may answer them by adding requirements")
    interpretation_notes: str = Field(default="", description="What the system inferred from the brief, in plain language, so the author can correct it")
    # System fields
    updated_at: str = Field(default="", json_schema_extra={"x-ai-exclude": True})
    interpreted_at: str = Field(default="", description="When the brief was last interpreted", json_schema_extra={"x-ai-exclude": True})
    interpreted_brief_hash: str = Field(default="", description="Hash of the brief the interpretation was made from", json_schema_extra={"x-ai-exclude": True})
    source_job_id: Optional[int] = Field(default=None, description="Create Novel job that seeded this charter", json_schema_extra={"x-ai-exclude": True})

    def is_empty(self) -> bool:
        return not (self.brief.strip() or self.requirements or self.open_choices or self.boundaries or self.one_line_pitch.strip())

    def musts(self) -> List[CharterRequirement]:
        return [r for r in self.requirements if r.strength == "must"]

    def prefers(self) -> List[CharterRequirement]:
        return [r for r in self.requirements if r.strength == "prefer"]

    def by_scope(self, *scopes: str) -> List[CharterRequirement]:
        wanted = set(scopes) | {"whole_novel"}
        return [r for r in self.requirements if r.scope in wanted]


class CharterConflict(BaseModel):
    """A place where generated material appears to contradict the Charter."""

    entry_id: str
    entry_text: str
    kind: Literal["requirement", "boundary", "open_choice"]
    message: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    span: Optional[List[int]] = None
    evidence: str = ""


class CharterCheckReport(BaseModel):
    project_id: int
    chapter_number: Optional[int] = None
    checked_entries: int = 0
    conflicts: List[CharterConflict] = Field(default_factory=list)
    verdict: Literal["clean", "review", "block"] = "clean"


class CharterSummary(BaseModel):
    """Compact view for dashboards and the Create Novel flow."""

    project_id: int
    exists: bool
    working_title: str = ""
    one_line_pitch: str = ""
    musts: int = 0
    prefers: int = 0
    open_choices: int = 0
    boundaries: int = 0
    interpreted: bool = False
    brief_changed_since_interpretation: bool = False
    questions_for_author: List[str] = Field(default_factory=list)
    categories: Dict[str, int] = Field(default_factory=dict)


__all__ = [
    "STORY_CHARTER_VERSION", "CharterBoundary", "CharterCheckReport", "CharterConflict", "CharterInterpretation", "CharterRequirement", "CharterSummary",
    "EntrySource", "OpenChoice", "ReferenceUsage", "RequirementCategory", "RequirementScope", "RequirementStrength", "StoryCharter",
]
