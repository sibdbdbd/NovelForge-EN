"""Director: the author's live steering channel over a running (or paused) autonomous job.

Minimal-input authors never touch this. Authors who want to go deep get:

- **directives** — notes scoped to the whole novel, an arc (chapter range) or one
  chapter; injected into planning and drafting prompts in the Story Charter's
  authority position (see ``forge.webnovel.render``).
- **redo chapter N** — rewind canon and ledgers to N-1 (``rewind.rewind_to``),
  discard chapter texts and digests from N on, optionally attach a directive to
  chapter N, optionally replan blueprints from N, and requeue the job at
  ``CHAPTER_GENERATION_LOOP`` so the next step regenerates N under the author's
  note. Chapters below N are untouched.
- **style profile** — read / patch the persisted Webnovel Style Profile; the next
  chapter compiles against the edited profile.

Every mutation goes through the job's normal state machine: the job is paused or
waiting before a redo, and it is requeued (not executed) here; the worker runs
the stage under its lease as usual.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from loguru import logger
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.db.models import AutonomousNovelJob, Card
from app.schemas.webnovel import AuthorDirective, WebnovelStyleProfile
from app.services.autonomous import rewind
from app.services.bible.bible_service import BibleService
from app.services.forge import provenance
from app.services.forge.webnovel import DirectiveService, WebnovelStyleService

REDO_STAGES = ("CHAPTER_GENERATION_LOOP", "WHOLE_NOVEL_AUDIT", "GLOBAL_REPAIR", "EXPORT", "DONE")


class DirectorError(ValueError):
    pass


def _c(card: Optional[Card]) -> Dict[str, Any]:
    return card.content if card is not None and isinstance(card.content, dict) else {}


def _project(job: AutonomousNovelJob) -> int:
    if not job.original_project_id:
        raise DirectorError("The novel project does not exist yet (a storyline must be selected first)")
    return int(job.original_project_id)


# ------------------------------------------------------------------ directives
def pending_directive(payload: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    """A directive parked on the job before the project exists: full schema shape, so the UI sees the same fields as a persisted one."""
    d = AuthorDirective.model_validate({k: v for k, v in payload.items() if k in AuthorDirective.model_fields and k not in ("id", "created_at", "consumed_by_chapters")})
    d.id = f"pending-{index}"
    d.created_at = datetime.now().isoformat(timespec="seconds")
    return d.model_dump(mode="json")


def list_directives(session: Session, job: AutonomousNovelJob) -> List[Dict[str, Any]]:
    if not job.original_project_id:
        out = []
        for i, raw in enumerate((job.options or {}).get("pending_directives") or []):
            try:
                out.append({**pending_directive(raw, index=i + 1), "id": raw.get("id") or f"pending-{i + 1}"})
            except Exception as exc:  # noqa: BLE001 - a malformed parked note is skipped, not fatal
                logger.warning(f"[Director] pending directive unreadable: {exc}")
        return out
    return [d.model_dump(mode="json") for d in DirectiveService(session).book(int(job.original_project_id)).directives]


def add_directive(session: Session, job: AutonomousNovelJob, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Add a directive. Before the novel project exists it is parked on the job and applied when the project is created."""
    d = AuthorDirective.model_validate({k: v for k, v in payload.items() if k in AuthorDirective.model_fields})
    if d.scope in ("chapter", "arc") and not d.chapter_from:
        raise DirectorError("chapter/arc directives need chapter_from")
    if job.chapter_count and d.chapter_from and d.chapter_from > job.chapter_count:
        raise DirectorError(f"chapter_from {d.chapter_from} exceeds the chapter count {job.chapter_count}")
    if job.original_project_id:
        return DirectiveService(session).add(int(job.original_project_id), d).model_dump(mode="json")
    pending = list((job.options or {}).get("pending_directives") or [])
    d.id = f"pending-{len(pending) + 1}"
    d.created_at = datetime.now().isoformat(timespec="seconds")
    pending.append(d.model_dump(mode="json"))
    job.options = {**(job.options or {}), "pending_directives": pending}
    flag_modified(job, "options")
    session.add(job)
    session.commit()
    return pending[-1]


def apply_pending_directives(session: Session, job: AutonomousNovelJob) -> int:
    """Move directives parked on the job into the project's Directive Book (idempotent)."""
    pending = list((job.options or {}).get("pending_directives") or [])
    if not pending or not job.original_project_id:
        return 0
    svc = DirectiveService(session)
    n = 0
    for raw in pending:
        try:
            d = AuthorDirective.model_validate({k: v for k, v in raw.items() if k in AuthorDirective.model_fields and k not in ("id",)})
            svc.add(int(job.original_project_id), d, commit=False)
            n += 1
        except Exception as exc:  # noqa: BLE001 - one bad note must not lose the others
            logger.warning(f"[Director] pending directive skipped: {exc}")
    opts = dict(job.options or {})
    opts.pop("pending_directives", None)
    job.options = opts
    flag_modified(job, "options")
    session.add(job)
    session.commit()
    return n


def update_directive(session: Session, job: AutonomousNovelJob, directive_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    if not job.original_project_id:
        pending = list((job.options or {}).get("pending_directives") or [])
        for i, raw in enumerate(pending):
            if raw.get("id") == directive_id:
                raw.update({k: v for k, v in patch.items() if k in AuthorDirective.model_fields and k not in ("id", "created_at")})
                pending[i] = AuthorDirective.model_validate(raw).model_dump(mode="json")
                job.options = {**(job.options or {}), "pending_directives": pending}
                flag_modified(job, "options")
                session.add(job)
                session.commit()
                return pending[i]
        raise DirectorError("Directive not found")
    row = DirectiveService(session).update(int(job.original_project_id), directive_id, patch)
    if row is None:
        raise DirectorError("Directive not found")
    return row.model_dump(mode="json")


def remove_directive(session: Session, job: AutonomousNovelJob, directive_id: str) -> bool:
    if not job.original_project_id:
        pending = [d for d in (job.options or {}).get("pending_directives") or [] if d.get("id") != directive_id]
        changed = len(pending) != len((job.options or {}).get("pending_directives") or [])
        job.options = {**(job.options or {}), "pending_directives": pending}
        flag_modified(job, "options")
        session.add(job)
        session.commit()
        return changed
    return DirectiveService(session).remove(int(job.original_project_id), directive_id)


# --------------------------------------------------------------- style profile
def get_style_profile(session: Session, job: AutonomousNovelJob) -> Dict[str, Any]:
    if job.original_project_id:
        profile = WebnovelStyleService(session).get(int(job.original_project_id))
        if profile is not None:
            return profile.model_dump(mode="json")
    # Not persisted yet: detect from what we know so the author can preview and pre-edit.
    from app.services.forge.webnovel import detect_profile

    opts = dict(job.options or {})
    fp = None
    if job.source_project_id:
        card = BibleService(session).singleton(int(job.source_project_id), "Narrative Fingerprint")
        fp = _c(card) or None
    override = opts.get("style_profile_override")
    if isinstance(override, dict):
        try:
            return WebnovelStyleProfile.model_validate(override).model_dump(mode="json")
        except Exception:  # noqa: BLE001
            pass
    return detect_profile(options=opts, brief=str(opts.get("summary") or ""), fingerprint=fp, source_genre_hint=str(opts.get("genre") or ""), words_per_chapter=opts.get("words_per_chapter")).model_dump(mode="json")


def update_style_profile(session: Session, job: AutonomousNovelJob, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge a patch into the profile. Persists on the project when it exists, otherwise parks an override on the job.

    Changing ``engine.subgenre`` re-seeds the template-owned machinery (engine, reader, register, perspective,
    window conventions) from the new template before the rest of the patch is applied, so switching from
    "hunter_gate" to "villainess_transmigration" does not keep an S-rank tier ladder.
    """
    current = get_style_profile(session, job)
    new_subgenre = (patch.get("engine") or {}).get("subgenre") if isinstance(patch.get("engine"), dict) else None
    if new_subgenre and new_subgenre != (current.get("engine") or {}).get("subgenre"):
        from app.services.forge.webnovel.templates import SUBGENRE_TEMPLATES, template_for

        if new_subgenre not in SUBGENRE_TEMPLATES:
            raise DirectorError(f"Unknown subgenre '{new_subgenre}'")
        tpl = template_for(new_subgenre).model_dump(mode="json")
        current = {**current, "engine": tpl["engine"], "reader": tpl["reader"], "narrator_register": tpl["narrator_register"], "perspective": tpl["perspective"], "signature_moves": tpl["signature_moves"],
                   "narration": {**current.get("narration", {}), "windows_enabled": tpl["narration"]["windows_enabled"], "sfx_density": tpl["narration"]["sfx_density"]}}
    merged = _deep_merge(current, patch)
    profile = WebnovelStyleProfile.model_validate(merged)
    profile.derived_from = "author"
    if job.original_project_id:
        WebnovelStyleService(session).save(int(job.original_project_id), profile, reason="style_profile_edit")
    else:
        job.options = {**(job.options or {}), "style_profile_override": profile.model_dump(mode="json")}
        flag_modified(job, "options")
        session.add(job)
        session.commit()
    return profile.model_dump(mode="json")


def apply_style_override(session: Session, job: AutonomousNovelJob) -> bool:
    """When the project is created, an override edited before selection becomes the persisted profile.

    Idempotent: the override is consumed (removed from the job options) whether it was applied,
    superseded by an author edit made on the project itself, or rejected as invalid.
    """
    override = (job.options or {}).get("style_profile_override")
    if not override or not job.original_project_id:
        return False
    svc = WebnovelStyleService(session)
    existing = svc.get(int(job.original_project_id))
    applied = False
    if existing is None or existing.derived_from != "author":
        try:
            profile = WebnovelStyleProfile.model_validate(override)
            profile.derived_from = "author"
            svc.save(int(job.original_project_id), profile, commit=False, reason="auto_apply_override")
            applied = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Director] style override invalid, ignored: {exc}")
    opts = dict(job.options or {})
    opts.pop("style_profile_override", None)
    job.options = opts
    flag_modified(job, "options")
    session.add(job)
    session.commit()
    return applied


def style_override_profile(job: AutonomousNovelJob) -> Optional[WebnovelStyleProfile]:
    """The author's pre-project style edit, if one is parked on the job and valid."""
    override = (job.options or {}).get("style_profile_override")
    if not isinstance(override, dict):
        return None
    try:
        return WebnovelStyleProfile.model_validate(override)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Director] style override invalid, ignored: {exc}")
        return None


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------- redo
def redo_plan(session: Session, job: AutonomousNovelJob, from_chapter: int) -> Dict[str, Any]:
    """What a redo would touch, without doing it."""
    pid = _project(job)
    manifest = provenance.get_manifest(session, pid, create=True)
    latest = int(manifest.latest_committed_chapter)
    if from_chapter < 1 or from_chapter > max(1, latest):
        raise DirectorError(f"from_chapter must be between 1 and the latest committed chapter ({latest})")
    texts = [n for n, _, _ in _chapter_texts(session, pid) if n >= from_chapter]
    return {"from_chapter": from_chapter, "latest_committed": latest, "chapters_discarded": texts, "chapters_kept": latest - len(texts) if latest >= len(texts) else 0, "will_replan": True, "job_stage": job.stage, "job_status": job.status}


def redo_from_chapter(session: Session, job: AutonomousNovelJob, *, from_chapter: int, note: Optional[str] = None, note_kind: str = "must", replan: bool = True, discard_texts: bool = True) -> Dict[str, Any]:
    """Rewind to ``from_chapter`` and requeue the job at the chapter loop so chapter N regenerates under the author's note.

    Preconditions: the job is paused, waiting, or completed (never running — pause it first), and the novel project exists.
    """
    pid = _project(job)
    if job.status == "running":
        raise DirectorError("Pause the job before redoing a chapter")
    if job.status == "cancelled":
        raise DirectorError("The job is cancelled")
    if job.stage not in REDO_STAGES:
        raise DirectorError(f"Chapters cannot be redone while the job is at stage {job.stage}")
    plan = redo_plan(session, job, from_chapter)
    # 1. Author's note for the regenerated chapter (chapter-scoped directive).
    directive: Optional[Dict[str, Any]] = None
    if note and note.strip():
        directive = DirectiveService(session).add(pid, AuthorDirective(scope="chapter", chapter_from=from_chapter, chapter_to=from_chapter, kind=note_kind if note_kind in ("must", "prefer", "avoid", "idea") else "must", text=note.strip(), applies_to=["planning", "drafting", "critic"])).model_dump(mode="json")
    # 2. Rewind canon + ledgers to from_chapter - 1 (idempotent) and drop derived chapter artifacts.
    rew = rewind.rewind_to(session, pid, from_chapter)
    removed_texts = 0
    removed_digests = 0
    if discard_texts:
        removed_texts = _discard_chapter_texts(session, pid, from_chapter)
        removed_digests = _discard_digests(session, pid, from_chapter)
    _mark_runs_superseded(session, pid, from_chapter)
    # 3. Job state: back to the loop, chapters_committed = from_chapter - 1, clear audit/repair/export results and quality verdict.
    results = {k: v for k, v in (job.stage_results or {}).items() if k not in ("WHOLE_NOVEL_AUDIT", "GLOBAL_REPAIR", "EXPORT", "checkpoint:GLOBAL_REPAIR", "approved:EXPORT")}
    loop = dict(results.get("CHAPTER_GENERATION_LOOP") or {})
    results["CHAPTER_GENERATION_LOOP"] = {k: v for k, v in loop.items() if str(k).isdigit() and int(k) < from_chapter}
    redo_log = list(results.get("redo_log") or [])
    redo_log.append({"at": datetime.now().isoformat(timespec="seconds"), "from_chapter": from_chapter, "note": (note or "")[:400], "replan": replan, "discarded": plan["chapters_discarded"]})
    results["redo_log"] = redo_log[-50:]
    if replan:
        results["replan_from"] = from_chapter
    job.stage = "CHAPTER_GENERATION_LOOP"
    job.status = "queued"
    job.chapters_committed = from_chapter - 1
    job.stage_results = results
    job.quality_status = None
    job.quality_summary = {}
    job.error = None
    job.finished_at = None
    job.lease_owner = None
    job.lease_expires_at = None
    job.progress_message = f"Redo requested from chapter {from_chapter}" + (" with an author note" if note else "")
    job.updated_at = datetime.now()
    flag_modified(job, "stage_results")
    session.add(job)
    session.commit()
    session.refresh(job)
    return {"job_id": job.id, "from_chapter": from_chapter, "directive": directive, "rewind": rew, "chapter_texts_removed": removed_texts, "digests_removed": removed_digests, "replan": replan, "status": job.status, "stage": job.stage}


def _chapter_texts(session: Session, project_id: int):
    from app.services.autonomous.audit import chapter_texts

    return chapter_texts(session, project_id)


def _discard_chapter_texts(session: Session, project_id: int, from_chapter: int) -> int:
    """Snapshot then delete Chapter Text cards >= from_chapter (their outlines stay so the loop can regenerate)."""
    from app.services import revision_service

    n = 0
    for card in BibleService(session).cards_of_type(project_id, "Chapter Text"):
        c = _c(card)
        if int(c.get("chapter_number") or 0) >= from_chapter:
            try:
                revision_service.snapshot_before_overwrite(session, card, reason="director_redo", actor="user", note=f"before redo from chapter {from_chapter}", new_content=None)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[Director] snapshot skipped for chapter text {card.id}: {exc}")
            session.delete(card)
            n += 1
    session.flush()
    return n


def _discard_digests(session: Session, project_id: int, from_chapter: int) -> int:
    try:
        from app.services.story_memory.digest_service import DigestService

        svc = DigestService(session)
        n = 0
        for card in list(svc.digest_cards(project_id)):
            if int(_c(card).get("chapter_number") or 0) >= from_chapter:
                session.delete(card)
                n += 1
        session.flush()
        return n
    except Exception as exc:  # noqa: BLE001 - memory is derived; a failure here is not fatal
        logger.warning(f"[Director] digest discard skipped: {exc}")
        return 0


def _mark_runs_superseded(session: Session, project_id: int, from_chapter: int) -> None:
    from sqlmodel import select

    from app.db.models import ChapterPipelineRun

    for row in session.exec(select(ChapterPipelineRun).where(ChapterPipelineRun.project_id == project_id, ChapterPipelineRun.chapter_number >= from_chapter, ChapterPipelineRun.status == "committed")).all():
        row.status = "superseded"
        row.updated_at = datetime.now()
        session.add(row)
    session.flush()


__all__ = ["DirectorError", "REDO_STAGES", "add_directive", "apply_pending_directives", "apply_style_override", "get_style_profile", "list_directives", "redo_from_chapter", "redo_plan", "remove_directive", "update_directive", "update_style_profile"]
