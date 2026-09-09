"""Named-prompt resolution for pipeline roles.

Every model-facing system prompt of the planning and generation pipeline lives
in ``bootstrap/prompts/<name>.txt`` and is bootstrapped into the ``Prompt``
table, where the Prompt Workshop can edit it. Services fetch prompts through
``system_prompt`` so that:

- a missing prompt is an explicit error (never a silent fallback to a stale
  inline string);
- every invocation records a stable ``prompt_version`` string
  ``"<name>@<version>#<hash>"`` for provenance, so a Workshop edit is visible in
  the telemetry of the runs it affected;
- output-contract lines the code depends on (tag names, JSON rules) can be
  appended by the caller and are therefore not editable by mistake.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from app.services.prompt_service import get_prompt_by_name

# Prompt names used by the Forge / autonomous pipeline (kept here so tests can assert the set).
PROMPT_STORYLINES = "Autonomous - Storyline Ideation"
PROMPT_ARCHITECTURE = "Autonomous - Novel Architecture"
PROMPT_CHAPTER_PLAN = "Autonomous - Chapter Plan"
PROMPT_DRAFT = "Forge - Chapter Draft"
PROMPT_REPAIR = "Forge - Chapter Repair"
PROMPT_CHARTER_INTERPRET = "Story Charter Interpretation"

PIPELINE_PROMPTS = (PROMPT_STORYLINES, PROMPT_ARCHITECTURE, PROMPT_CHAPTER_PLAN, PROMPT_DRAFT, PROMPT_REPAIR, PROMPT_CHARTER_INTERPRET)


class PromptMissingError(RuntimeError):
    def __init__(self, name: str):
        super().__init__(f"Prompt '{name}' is missing; it is a required runtime dependency (restart the backend to re-bootstrap prompts, or restore it in the Prompt Workshop)")
        self.name = name


@dataclass(frozen=True)
class ResolvedPrompt:
    name: str
    text: str
    version: str

    def with_contract(self, contract: str) -> "ResolvedPrompt":
        """Append a code-owned output contract (not editable in the Workshop)."""
        if not contract.strip():
            return self
        return ResolvedPrompt(name=self.name, text=self.text.rstrip() + "\n\n" + contract.strip(), version=self.version)


def system_prompt(session: Session, name: str) -> ResolvedPrompt:
    row = get_prompt_by_name(session, name)
    if row is None or not (row.template or "").strip():
        raise PromptMissingError(name)
    text = str(row.template).strip()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return ResolvedPrompt(name=name, text=text, version=f"{name}@{int(row.version or 1)}#{digest}")


def optional_system_prompt(session: Session, name: str) -> Optional[ResolvedPrompt]:
    try:
        return system_prompt(session, name)
    except PromptMissingError:
        return None


__all__ = ["PIPELINE_PROMPTS", "PROMPT_ARCHITECTURE", "PROMPT_CHAPTER_PLAN", "PROMPT_CHARTER_INTERPRET", "PROMPT_DRAFT", "PROMPT_REPAIR", "PROMPT_STORYLINES", "PromptMissingError", "ResolvedPrompt", "optional_system_prompt", "system_prompt"]
