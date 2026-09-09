"""CHAPTER_GENERATION_LOOP: one chapter per call so the runner can checkpoint.

Each call runs the Forge pipeline (compile -> draft -> extract -> validate ->
repair -> revalidate -> commit -> sync) for the manifest's next chapter, then
reforecasts: it compares the committed chapter with the blueprint and, when
the deviation is material, triggers ``replan_from`` for the next window.

Automatic policy for a rejected chapter (blockers remain after the pipeline's
in-run repairs): regenerate with ``regenerate=True`` up to
``MAX_CHAPTER_REGENERATIONS`` times, then fail the stage with the right
category so the runner's ladder (reduce scope -> fallback model -> pause)
applies.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from sqlmodel import Session, select

from app.db.models import Card, ChapterPipelineRun
from app.services.autonomous import failpoints
from app.services.autonomous import failures as fail
from app.services.autonomous.chapter_plan import existing_outlines, replan_from
from app.services.autonomous.model_client import ForgeDrafterAdapter, ModelClient
from app.services.forge import provenance
from app.services.forge.pipeline import CraftOptions, PipelineOptions, PipelineResult, run_chapter

MAX_CHAPTER_REGENERATIONS = 2
WORD_DRIFT_TOLERANCE = 0.35
ACCEPTED_WARNING_SEVERITIES = ("medium", "low")


def craft_options_for(options: Dict[str, Any]) -> Optional[CraftOptions]:
    """Job options -> craft preset. ``craft_preset`` wins; otherwise follow ``quality_preset``; 'off' disables the layer."""
    preset = str(options.get("craft_preset") or {"economy": "economy", "quality": "full"}.get(str(options.get("quality_preset") or ""), "balanced")).lower()
    if preset in ("off", "none", "legacy"):
        return None
    opts = CraftOptions.preset(preset)
    if "model_scene_plan" in options:
        opts.model_scene_plan = bool(options["model_scene_plan"])
    return opts


def _c(card: Optional[Card]) -> Dict[str, Any]:
    return card.content if card is not None and isinstance(card.content, dict) else {}


def _category_for(result: PipelineResult) -> str:
    err = result.error or {}
    blocking = err.get("blocking") or []
    codes = {b.get("code") for b in blocking if isinstance(b, dict)}
    layers = {b.get("layer") for b in blocking if isinstance(b, dict)}
    if result.status == "compile_failed":
        return fail.STALE_DEPENDENCY if err.get("code") in ("stale_dependencies", "stale_canon_revision") else fail.PLANNING_IMPOSSIBILITY
    if "originality" in layers or codes & {"source_entity_leak", "entity_overlap", "long_phrase_overlap", "dialogue_overlap", "accidental_quotation"}:
        return fail.ORIGINALITY_VIOLATION
    if layers & {"fact", "pov", "character", "temporal", "outline", "entity"}:
        return fail.CONTINUITY_VIOLATION
    if result.status == "error":
        return fail.classify_exception(RuntimeError(err.get("message") or "pipeline error"))
    return fail.CONTINUITY_VIOLATION


def deviation_report(session: Session, project_id: int, chapter_number: int, result: PipelineResult, *, word_target: int) -> Dict[str, Any]:
    """Compare the committed chapter with its blueprint."""
    outline = existing_outlines(session, project_id).get(chapter_number) or {}
    metrics = (result.validation or {}).get("metrics") or {}
    words = int(metrics.get("unit_count") or len((result.prose or "").split()))
    reasons: List[str] = []
    if word_target and abs(words - word_target) / float(word_target) > WORD_DRIFT_TOLERANCE:
        reasons.append(f"word count {words} deviates from target {word_target}")
    sync = result.sync or {}
    committed_facts = sync.get("committed") or sync.get("facts_committed") or []
    planned_payoffs = [str(p).lower() for p in outline.get("payoffs") or []]
    prose_l = (result.prose or "").lower()
    missed = [p for p in planned_payoffs if p and not any(tok in prose_l for tok in p.split()[:3] if len(tok) > 3)]
    if missed:
        reasons.append(f"planned payoff(s) not evidenced: {missed[:3]}")
    style = result.style or {}
    if style.get("adherence_score") is not None and float(style["adherence_score"]) < 0.5:
        reasons.append(f"style adherence {style['adherence_score']} below 0.5")
    warnings = [i for i in ((result.validation or {}).get("issues") or []) if i.get("severity") in ACCEPTED_WARNING_SEVERITIES]
    return {"chapter": chapter_number, "words": words, "word_target": word_target, "reasons": reasons, "material": bool(missed) or (word_target and abs(words - word_target) / float(word_target) > 0.6), "accepted_warnings": [{"code": w.get("code"), "severity": w.get("severity"), "rationale": "below blocking threshold; accepted by policy"} for w in warnings][:20], "facts_committed": len(committed_facts) if isinstance(committed_facts, list) else committed_facts}


async def generate_next_chapter(session: Session, *, project_id: int, chapter_count: int, client: ModelClient, options: Dict[str, Any], word_target: int, budget_chars: int = 16000, lease_check: Optional[Callable[[], None]] = None, replan_before: Optional[int] = None) -> Dict[str, Any]:
    check = lease_check or (lambda: None)
    manifest = provenance.get_manifest(session, project_id, create=True)
    n = int(manifest.latest_committed_chapter) + 1
    if n > chapter_count:
        return {"complete": True, "chapter": None}
    pre_replan: Dict[str, Any] = {}
    if replan_before is not None and int(replan_before) == n and n <= chapter_count:
        # Director redo: the author asked for chapter n (and its window) to be replanned under their note before drafting.
        check()
        pre_replan = await replan_from(session, project_id=project_id, chapter_count=chapter_count, client=client, options=options, after_chapter=n - 1, reasons=[f"author redo from chapter {n}"])
    drafter = ForgeDrafterAdapter(client)
    craft = craft_options_for(options)
    pipeline_opts = PipelineOptions(max_repairs=int(options.get("max_repairs") or 2), budget_chars=budget_chars, word_target=word_target, regenerate=False, craft=craft)
    result: Optional[PipelineResult] = None
    for attempt in range(MAX_CHAPTER_REGENERATIONS + 1):
        if attempt:
            pipeline_opts = PipelineOptions(max_repairs=int(options.get("max_repairs") or 2) + 1, budget_chars=budget_chars, word_target=word_target, regenerate=True, craft=craft)
        check()
        result = await run_chapter(session, project_id=project_id, chapter_number=n, drafter=drafter, options=pipeline_opts)
        failpoints.hit("after_chapter_commit")
        if result.status == "committed":
            break
        if result.status in ("compile_failed",):
            break
    assert result is not None
    if result.status != "committed":
        raise fail.StageFailure(_category_for(result), f"Chapter {n} ended in status '{result.status}': {(result.error or {}).get('message') or (result.error or {}).get('code')}", detail={"chapter": n, "run_id": result.run_id, "error": result.error, "blocking": ((result.error or {}).get("blocking") or [])[:10]})
    check()
    memory = await digest_committed_chapter(session, project_id=project_id, chapter_number=n, client=client, result=result, options=options)
    check()
    dev = deviation_report(session, project_id, n, result, word_target=word_target)
    replan: Dict[str, Any] = {"replanned": 0}
    if dev["material"] and n < chapter_count:
        replan = await replan_from(session, project_id=project_id, chapter_count=chapter_count, client=client, options=options, after_chapter=n, reasons=dev["reasons"])
    if pre_replan:
        replan = {**replan, "pre_replan": pre_replan}
    try:
        from app.services.forge.webnovel import DirectiveService

        DirectiveService(session).mark_consumed(project_id, n)
    except Exception as exc:  # noqa: BLE001 - bookkeeping only
        logger.warning(f"[Autonomous] directive bookkeeping skipped for ch.{n}: {exc}")
    craft_summary = {"mode": (result.craft or {}).get("mode"), "score": ((result.craft or {}).get("critic_after") or {}).get("overall"), "accepted": (result.craft or {}).get("accepted"), "passes": [p.get("name") for p in (result.craft or {}).get("passes") or []], "webnovel": ((result.craft or {}).get("webnovel_after") or {}).get("scores"), "webnovel_overall": ((result.craft or {}).get("webnovel_after") or {}).get("overall")} if result.craft else None
    return {"complete": n >= chapter_count, "chapter": n, "run_id": result.run_id, "chapter_card_id": result.chapter_card_id, "model_calls": result.model_calls + (1 if memory.get("digested") else 0), "repair_attempts": result.repair_attempts, "style_score": (result.style or {}).get("adherence_score"), "validation_passed": (result.validation or {}).get("passed"), "craft": craft_summary, "deviation": dev, "replan": replan, "memory": memory}


async def digest_committed_chapter(session: Session, *, project_id: int, chapter_number: int, client: ModelClient, result: PipelineResult, options: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the Chapter Digest for a committed chapter through the budgeted model client.

    Story Memory is what lets chapter 300 remember chapter 12, so the autonomous loop keeps it
    current instead of relying on the editor's save hook. Failure is never fatal: the chapter is
    already committed and the compiler falls back to state packets for undigested chapters.
    """
    if options.get("story_memory") is False:
        return {"digested": False, "skipped": "disabled"}
    from app.schemas.story_memory import ChapterDigest
    from app.services.story_memory.digest_service import DigestService

    text = (result.prose or "").strip()
    if not text or not result.chapter_card_id:
        return {"digested": False, "skipped": "no prose"}
    svc = DigestService(session)
    try:
        if svc.is_fresh(project_id, chapter_number, text):
            return {"digested": False, "skipped": "fresh"}
        card = session.get(Card, int(result.chapter_card_id))
        c = _c(card)
        system_prompt, user_prompt = svc.build_prompts(project_id=project_id, text=text, chapter_number=chapter_number, volume_number=c.get("volume_number"), title=str(c.get("title") or ""), participants=list(c.get("participants") or []))
        digest = await client.structured(role="digest_extractor", schema=ChapterDigest, system_prompt=system_prompt, user_prompt=user_prompt, prompt_version="Chapter Digest Extraction@1", stage=f"CHAPTER_GENERATION_LOOP:ch{chapter_number}:digest")
        digest = svc.finalize_digest(digest, text=text, chapter_number=chapter_number, volume_number=c.get("volume_number"), title=str(c.get("title") or ""), chapter_card_id=int(result.chapter_card_id), llm_config_id=None)
        svc.save_digest(project_id, digest, commit=True)
        return {"digested": True, "hooks_opened": len(digest.hooks_opened), "state_changes": len(digest.state_changes)}
    except fail.StageFailure as exc:
        session.rollback()
        if exc.category == fail.BUDGET_EXCEEDED:
            raise
        logger.warning(f"[Autonomous] digest for ch.{chapter_number} skipped: {exc}")
        return {"digested": False, "error": str(exc)[:200]}
    except Exception as exc:  # noqa: BLE001 - memory is an enhancement over the committed chapter, never a blocker
        session.rollback()
        logger.warning(f"[Autonomous] digest for ch.{chapter_number} failed: {exc}")
        return {"digested": False, "error": f"{type(exc).__name__}: {exc}"[:200]}


def loop_status(session: Session, project_id: int, chapter_count: int) -> Dict[str, Any]:
    manifest = provenance.get_manifest(session, project_id, create=True)
    runs = session.exec(select(ChapterPipelineRun).where(ChapterPipelineRun.project_id == project_id).order_by(ChapterPipelineRun.id.desc()).limit(200)).all()
    return {"committed": int(manifest.latest_committed_chapter), "chapter_count": chapter_count, "runs": len(runs), "rejected_runs": sum(1 for r in runs if r.status == "rejected"), "model_calls": sum(r.model_calls for r in runs), "repair_attempts": sum(r.repair_attempts for r in runs)}


__all__ = ["ACCEPTED_WARNING_SEVERITIES", "MAX_CHAPTER_REGENERATIONS", "WORD_DRIFT_TOLERANCE", "craft_options_for", "deviation_report", "digest_committed_chapter", "generate_next_chapter", "loop_status"]
