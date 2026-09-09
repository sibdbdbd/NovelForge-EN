"""Story Charter API: read, edit, interpret and check the author's requirements."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.models import Project
from app.db.session import get_session
from app.schemas.story_charter import CharterCheckReport, CharterSummary, StoryCharter
from app.services.story_charter import CHARTER_TYPE, CharterService, render_charter
from app.services.story_charter.charter_service import CONSUMER_SCOPES

router = APIRouter()


class CharterReadResponse(BaseModel):
    project_id: int
    card_id: Optional[int] = None
    charter: StoryCharter
    summary: CharterSummary


class CharterSaveRequest(BaseModel):
    project_id: int
    charter: StoryCharter


class CharterInterpretRequest(BaseModel):
    project_id: int
    llm_config_id: int
    brief: Optional[str] = Field(default=None, description="Replaces the stored brief before interpreting")
    replace_interpreted: bool = Field(default=True, description="Drop previously interpreted entries; author-authored entries are always kept")


class CharterRenderResponse(BaseModel):
    project_id: int
    consumer: str
    text: str
    chars: int
    consumers: List[str]


class CharterCheckRequest(BaseModel):
    project_id: int
    text: str
    chapter_number: Optional[int] = None


def _project(session: Session, project_id: int) -> Project:
    p = session.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.get("", response_model=CharterReadResponse, summary="The project's Story Charter (empty charter when none exists yet)")
def get_charter(project_id: int, session: Session = Depends(get_session)) -> CharterReadResponse:
    _project(session, project_id)
    svc = CharterService(session)
    card = svc.card(project_id)
    charter = svc.get(project_id) or StoryCharter()
    return CharterReadResponse(project_id=project_id, card_id=card.id if card else None, charter=charter, summary=svc.summary(project_id))


@router.put("", response_model=CharterReadResponse, summary="Save the Story Charter (author edits are authoritative)")
def save_charter(req: CharterSaveRequest, session: Session = Depends(get_session)) -> CharterReadResponse:
    _project(session, req.project_id)
    svc = CharterService(session)
    try:
        card = svc.save(req.project_id, req.charter)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return CharterReadResponse(project_id=req.project_id, card_id=card.id, charter=svc.get(req.project_id) or req.charter, summary=svc.summary(req.project_id))


@router.post("/interpret", response_model=CharterReadResponse, summary="Interpret the free-text brief into requirements, open choices and boundaries (one model call)")
async def interpret_charter(req: CharterInterpretRequest, session: Session = Depends(get_session)) -> CharterReadResponse:
    _project(session, req.project_id)
    svc = CharterService(session)
    try:
        charter = await svc.interpret(req.project_id, llm_config_id=req.llm_config_id, brief=req.brief, replace_interpreted=req.replace_interpreted)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    card = svc.card(req.project_id)
    return CharterReadResponse(project_id=req.project_id, card_id=card.id if card else None, charter=charter, summary=svc.summary(req.project_id))


@router.get("/render", response_model=CharterRenderResponse, summary="Exactly what a prompt consumer receives from the charter")
def render(project_id: int, consumer: str = "draft", session: Session = Depends(get_session)) -> CharterRenderResponse:
    _project(session, project_id)
    if consumer not in CONSUMER_SCOPES:
        raise HTTPException(status_code=400, detail=f"consumer must be one of {sorted(CONSUMER_SCOPES)}")
    text = render_charter(CharterService(session).get(project_id), consumer=consumer)
    return CharterRenderResponse(project_id=project_id, consumer=consumer, text=text, chars=len(text), consumers=sorted(CONSUMER_SCOPES))


@router.post("/check", response_model=CharterCheckReport, summary="Deterministic scan of a text against boundaries and negative requirements")
def check(req: CharterCheckRequest, session: Session = Depends(get_session)) -> CharterCheckReport:
    _project(session, req.project_id)
    return CharterService(session).check_text(req.project_id, req.text, chapter_number=req.chapter_number)


@router.get("/meta", response_model=Dict[str, Any], summary="Charter vocabulary for the editor (scopes, categories, consumers)")
def meta() -> Dict[str, Any]:
    from app.schemas.story_charter import RequirementCategory, RequirementScope

    return {"card_type": CHARTER_TYPE, "scopes": list(RequirementScope.__args__), "categories": list(RequirementCategory.__args__), "consumers": {k: list(v) for k, v in CONSUMER_SCOPES.items()}}


__all__ = ["router"]
