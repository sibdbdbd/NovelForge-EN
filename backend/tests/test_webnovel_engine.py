"""Webnovel Style Engine + Director — no live model calls.

Covers: subgenre templates and cue-based guessing; profile detection from author
fields and fingerprint signals (minimal input still yields a genre-correct
profile); prompt rendering for drafting / planning / critic; deterministic
Webnovel Conformance on webnovel-shaped vs. literary prose; critic merge; the
persisted profile + Directive Book on a project; directive scoping; and the
Director's redo-from-chapter flow on a finished job (rewind + requeue + note).
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict

import pytest
from sqlmodel import Session, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests import test_autonomous_pipeline as ap  # noqa: E402

pytestmark = pytest.mark.timeout(900)


WEBNOVEL_PROSE = """I counted the exits before I counted the people. Two doors, one window, seven hunters who thought they were the only ones in the room who mattered.

"F-rank," the assessor said, not looking up. "Crystal's on your left."

'Same crystal. Same crack down the side.'

I put my hand on it.

[Mana Measurement: Rank E — Error. Re-measuring.]

The assessor looked up.

[Mana Measurement: Rank B]

Silence fell over the hall. Somebody's clipboard hit the floor.

'Lower than last time. Good. Less attention.'

"That's impossible," the assessor said. His hand had gone still on the desk.

"Then measure it again."

He did. The room went very quiet. The man beside me who had sneered at my card an hour ago took a step back without seeming to notice he had.

Thud.

The door behind us had closed. Nobody had touched it."""

LITERARY_PROSE = (
    "It was a cold grey morning when Elara awoke, the pale light filtering through gossamer curtains like a half-remembered dream, and she lay there for a long while considering the ineffable weight of what had transpired the night before, "
    "the way the conversation with her mentor had unspooled like a ribbon of silk, each word a testament to the liminal space between who she had been and who she was becoming. The manor was quiet. She rose, dressed, and descended the great staircase, "
    "her thoughts a tapestry of doubt and resolve, and found the breakfast room empty save for the steward, who informed her that the Duke had departed at dawn for the capital, where the council would convene in three days to decide the fate of the northern provinces, "
    "a matter of some complexity given the history of the region, which had been contested for centuries between the crown and the border lords, and which had been the subject of the treaty her grandfather had negotiated, according to the family histories, in the year of the great flood. "
    "She ate slowly. She thought about her grandfather. When she had finished, she went to the library and read until the light failed, and then she went to bed, and the house settled into silence around her, and she slept."
)


# ---------------------------------------------------------------- templates
def test_templates_cover_every_label_and_guess_from_cues():
    from app.services.forge.webnovel.templates import SUBGENRE_LABELS, SUBGENRE_TEMPLATES, guess_subgenre, template_for

    assert set(SUBGENRE_LABELS) == set(SUBGENRE_TEMPLATES)
    for key, tpl in SUBGENRE_TEMPLATES.items():
        assert tpl.engine.subgenre == key
        assert tpl.reader.core_fantasy and tpl.engine.reward_types
    assert guess_subgenre("A regressed knight returns to the day before the betrayal") == "regression"
    assert guess_subgenre("S-rank hunter guild raid gate") == "hunter_gate"
    assert guess_subgenre("possessed the villainess of an otome novel; the duke's daughter") == "villainess_transmigration"
    assert guess_subgenre("a quiet love story on a farm") is None
    assert template_for("nonsense").engine.subgenre == "custom"
    assert template_for(None).engine.subgenre == "custom"
    # Templates are copies: mutating one must not leak into the library.
    t = template_for("hunter_gate")
    t.engine.tier_ladder.append("X")
    assert "X" not in template_for("hunter_gate").engine.tier_ladder


# ---------------------------------------------------------------- detection
def test_detect_profile_minimal_and_deep_inputs():
    from app.services.forge.webnovel import detect_profile

    # Minimal input: nothing but a fingerprint-like signal set -> still a sensible, complete profile.
    fp = {"language": "en", "chapters_measured": 20, "per_chapter_metrics": [{"status_window_count": 3}] * 20, "layers": {
        "pov_focalization": {"features": {"pov": "first_person", "pov_stability": 0.95}},
        "rhythm": {"features": {"short_paragraph_ratio": {"median": 0.72}, "paragraph_len_mean": {"median": 14.0}, "chapter_units": {"median": 2100}}},
        "internal_monologue": {"features": {"internal_thought_ratio": {"median": 0.22}}},
        "humor": {"features": {"humor_score_mean": 4.0}},
        "pacing_reward": {"features": {"reward_gap_chapters": {"median": 1.0}}},
    }}
    p = detect_profile(fingerprint=fp, source_scene_functions=["status_screen_presentation", "power_reveal", "fight_choreography"], source_genre_hint="")
    assert p.derived_from in ("detected", "default")
    assert p.perspective == "first_person"
    assert p.narration.paragraph_rhythm == "one_line"
    assert p.narration.thought_density == "dense"
    assert p.narration.windows_enabled is True
    assert p.chapter.words_target == 2100
    assert "reference" in p.detection_notes
    # Deep input: author fields win over everything.
    d = detect_profile(options={"subgenre": "villainess_transmigration", "platform": "kakaopage", "perspective": "third_limited", "register": "warm_wry", "thought_style": "italics", "status_windows": False, "romance_level": "central", "genre_intensity": "intense", "comedy_level": "high", "words_per_chapter": 3000}, brief="a hunter regresses", fingerprint=fp)
    assert d.engine.subgenre == "villainess_transmigration" and d.derived_from == "author"
    assert d.platform == "kakaopage" and d.perspective == "third_limited" and d.narrator_register == "warm_wry"
    assert d.narration.thought_style == "italics" and d.narration.windows_enabled is False
    assert d.reader.romance_mode == "central" and d.reader.comedy_level == "high" and d.reader.dopamine_per_chapter >= 2
    assert d.chapter.words_target == 3000
    # Brief cues beat the fingerprint's genre guess.
    b = detect_profile(brief="He regressed to the week before the betrayal; this second chance, he would be early instead of late", fingerprint=fp)
    assert b.engine.subgenre == "regression"
    # A mixed brief (regression + hunter) resolves to the subgenre with the most cue hits; the fingerprint windows still apply.
    m = detect_profile(brief="He came back to the day of his awakening; this time the gate would not take his sister; S-rank hunters everywhere", fingerprint=fp)
    assert m.engine.subgenre == "hunter_gate" and m.narration.windows_enabled is True


# ---------------------------------------------------------------- rendering
def test_render_blocks_are_bounded_and_carry_conventions():
    from app.services.forge.webnovel import render_for_critic, render_for_drafting, render_for_planning, template_for
    from app.services.forge.webnovel.render import render_directives
    from app.schemas.webnovel import AuthorDirective

    p = template_for("hunter_gate")
    d = render_for_drafting(p)
    assert len(d) <= 3600 and "single quotes" in d and "[Skill acquired" in d and "Face-slap" in d and "BANNED" in d
    pl = render_for_planning(p)
    assert "Progression axis" in pl and "Reward types" in pl and "≈2500 words" in pl
    c = render_for_critic(p)
    assert "acquisitions editor" in c and "Penalise" in c
    # windows disabled -> the drafting block says so explicitly
    p2 = template_for("office_life")
    assert "no system windows" in render_for_drafting(p2)
    # directives: scope filtering
    ds = [
        AuthorDirective(id="dir-1", scope="novel", kind="must", text="The mentor never dies."),
        AuthorDirective(id="dir-2", scope="chapter", chapter_from=5, kind="idea", text="Open on the auction floor."),
        AuthorDirective(id="dir-3", scope="arc", chapter_from=10, chapter_to=20, kind="avoid", text="No romance progress in this arc."),
        AuthorDirective(id="dir-4", scope="novel", kind="must", text="Critic-only note", applies_to=["critic"]),
        AuthorDirective(id="dir-5", scope="novel", kind="must", text="Inactive", active=False),
    ]
    ch5 = render_directives(ds, chapter=5, consumer="drafting")
    assert "dir-1" in ch5 and "dir-2" in ch5 and "dir-3" not in ch5 and "dir-4" not in ch5 and "Inactive" not in ch5
    ch15 = render_directives(ds, chapter=15, consumer="drafting")
    assert "dir-3" in ch15 and "dir-2" not in ch15 and "AVOID" in ch15
    # Without a chapter (architecture / novel-wide planning): novel + arc notes are visible, chapter notes are not.
    whole = render_directives(ds, chapter=None, consumer="planning")
    assert "dir-1" in whole and "dir-3" in whole and "dir-2" not in whole and "dir-4" not in whole
    assert render_directives([], chapter=1) == ""


# -------------------------------------------------------------- conformance
def test_conformance_separates_webnovel_from_literary_prose():
    from app.services.forge.webnovel import measure_conformance, template_for

    p = template_for("hunter_gate")
    good = measure_conformance(WEBNOVEL_PROSE, p)
    bad = measure_conformance(LITERARY_PROSE, p)
    assert good.overall > bad.overall + 3.0, (good.overall, bad.overall)
    assert good.passed and not bad.passed
    assert good.metrics["one_line_share"] > 0.8 and good.metrics["windows"] == 2 and good.metrics["inner_speech_marked"] == 2 and good.metrics["sfx_lines"] == 1
    assert good.metrics["micro_payoffs"] >= 1 and good.metrics["reaction_shots"] >= 2
    codes = {f.code for f in bad.findings}
    for expected in ("rhythm_too_dense", "paragraph_walls", "inner_speech_missing", "weather_opening", "metaphor_stacking", "literary_register", "exposition_block", "reward_missing", "soft_ending"):
        assert expected in codes, (expected, sorted(codes))
    # A profile without windows flags the windows as a convention violation.
    nowin = template_for("office_life")
    c = measure_conformance(WEBNOVEL_PROSE, nowin)
    assert "windows_forbidden" in {f.code for f in c.findings}
    # Recap opening is caught.
    recap = "Previously, I had escaped the gate. " + WEBNOVEL_PROSE
    assert "recap_opening" in {f.code for f in measure_conformance(recap, p).findings}
    # Scores are ints 1..10 and the report round-trips through JSON.
    assert all(1 <= v <= 10 for v in good.scores.values()) and set(good.scores) == {"rhythm", "inner_voice", "conventions", "momentum", "reward", "ending"}
    assert good.model_dump(mode="json")["overall"] == good.overall


def test_critic_merge_takes_lower_shared_scores_and_adds_webnovel_dimensions():
    from app.services.forge.craft import critic as critic_mod, hooks as hooks_mod
    from app.services.forge.webnovel import measure_conformance, template_for

    p = template_for("hunter_gate")
    det = critic_mod.deterministic_critic(LITERARY_PROSE, hook=hooks_mod.analyze_hook(LITERARY_PROSE), language="en", pov_name="Elara", word_target=2500)
    conf = measure_conformance(LITERARY_PROSE, p)
    merged = critic_mod.merge_conformance(det, conf)
    assert merged.source == "merged"
    assert merged.scores["pacing"] <= min(det.scores["pacing"], conf.scores["rhythm"], conf.scores["momentum"])
    assert merged.scores["payoff"] <= conf.scores["reward"] and merged.scores["hook"] <= conf.scores["ending"]
    assert {"webnovel_rhythm", "webnovel_inner_voice", "webnovel_ending"} <= set(merged.scores)
    assert merged.overall <= det.overall + 0.01
    assert any(f.problem.startswith("[webnovel/") for f in merged.findings)
    assert len(merged.findings) >= len(det.findings)
    assert critic_mod.merge_conformance(det, None) is det


def test_grade_without_profile_is_plain_deterministic_critic():
    from app.services.forge.craft.passes import CraftInputs, grade

    inputs = CraftInputs(pov="Nadia", participants=["Nadia"], beats=[], word_target=800)
    rep = grade(WEBNOVEL_PROSE, inputs)
    assert rep.source == "deterministic" and "webnovel_rhythm" not in rep.scores
    from app.services.forge.webnovel import template_for

    inputs.style_profile = template_for("hunter_gate")
    rep2 = grade(WEBNOVEL_PROSE, inputs)
    assert rep2.source == "merged" and "webnovel_rhythm" in rep2.scores


# --------------------------------------------------------------- persistence
def test_style_and_directive_services_persist_on_a_project(app_client):
    from app.db.session import engine
    from app.schemas.card import CardCreate  # noqa: F401 - ensures bootstrap ran
    from app.schemas.project import ProjectCreate
    from app.schemas.webnovel import AuthorDirective
    from app.services import project_service
    from app.services.forge.webnovel import DirectiveService, WebnovelStyleService

    with Session(engine) as s:
        project, _ = project_service.create_project(s, ProjectCreate(name="webnovel-engine-test", description="", template=None))
        svc = WebnovelStyleService(s)
        assert svc.get(project.id) is None
        profile = svc.ensure(project.id, options={"subgenre": "tower_climb"}, brief="")
        assert profile.engine.subgenre == "tower_climb"
        # ensure() is idempotent: an existing profile is returned untouched even when options change.
        again = svc.ensure(project.id, options={"subgenre": "office_life"})
        assert again.engine.subgenre == "tower_climb"
        profile.narrator_register = "manic_comic"
        svc.save(project.id, profile)
        assert svc.get(project.id).narrator_register == "manic_comic"
        assert svc.card(project.id).card_type.name == "Webnovel Style Profile"

        ds = DirectiveService(s)
        assert ds.book(project.id).directives == []
        d1 = ds.add(project.id, AuthorDirective(scope="novel", kind="must", text="The mentor never dies."))
        d2 = ds.add(project.id, AuthorDirective(scope="chapter", chapter_from=3, kind="idea", text="Open on the auction floor."))
        assert d1.id == "dir-1" and d2.id == "dir-2" and d1.created_at
        assert [d.id for d in ds.for_chapter(project.id, 3)] == ["dir-1", "dir-2"]
        assert [d.id for d in ds.for_chapter(project.id, 4)] == ["dir-1"]
        assert "dir-2" in ds.render(project.id, chapter=3) and "dir-2" not in ds.render(project.id, chapter=4)
        assert ds.update(project.id, "dir-2", {"chapter_from": 4, "chapter_to": 6}).chapter_to == 6
        assert [d.id for d in ds.for_chapter(project.id, 5)] == ["dir-1", "dir-2"]
        assert ds.mark_consumed(project.id, 5) == 2 and ds.mark_consumed(project.id, 5) == 0
        assert ds.remove(project.id, "dir-2") and not ds.remove(project.id, "dir-2")
        assert [d.id for d in ds.book(project.id).directives] == ["dir-1"]
        # A third add reuses the freed id space deterministically.
        d3 = ds.add(project.id, AuthorDirective(scope="arc", chapter_from=10, chapter_to=12, kind="avoid", text="No new POVs."))
        assert d3.id == "dir-2"


# ---------------------------------------------------------- compiler / craft
def test_compiled_context_carries_style_and_directives_into_prompts(app_client):
    """On a full Forge project, a profile and a chapter directive surface as mandatory sections and reach every craft pass."""
    from app.db.session import engine
    from app.schemas.webnovel import AuthorDirective
    from app.services.forge.compiler import ChapterContextCompiler
    from app.services.forge.craft import CraftOptions
    from app.services.forge.pipeline import PipelineOptions, run_chapter
    from app.services.forge.webnovel import DirectiveService, WebnovelStyleService
    from tests import test_forge_continuity as cont
    from tests import test_prose_craft as pc

    state: Dict[str, Any] = {}
    cont._setup_projects(app_client, state)
    pid = state["original_pid"]
    with Session(engine) as s:
        WebnovelStyleService(s).ensure(pid, options={"subgenre": "regression"})
        DirectiveService(s).add(pid, AuthorDirective(scope="chapter", chapter_from=1, kind="must", text="Chapter one ends with the tide bell ringing twice."))
        DirectiveService(s).add(pid, AuthorDirective(scope="novel", kind="avoid", text="No flashbacks to the first life longer than a line."))
        ctx = ChapterContextCompiler(s).compile(project_id=pid, chapter_number=1)
        s.rollback()
    keys = [sec.key for sec in ctx.sections]
    assert "webnovel_style" in keys and "author_directives" in keys
    assert keys.index("author_directives") < keys.index("reader_contract")  # author speaks before the Bible
    style = next(sec for sec in ctx.sections if sec.key == "webnovel_style")
    assert style.mandatory and "Regression" in style.text and "single quotes" in style.text
    direct = next(sec for sec in ctx.sections if sec.key == "author_directives")
    assert direct.mandatory and "tide bell" in direct.text and "flashbacks" in direct.text
    assert any(i["card_type"] == "Webnovel Style Profile" for i in ctx.manifest["included_cards"])
    # The craft passes receive the style block and directives; the run records conformance before/after.
    drafter = pc.CraftDrafter()
    with Session(engine) as s:
        res = asyncio.run(run_chapter(s, project_id=pid, chapter_number=1, drafter=drafter, options=PipelineOptions(max_repairs=2, craft=CraftOptions.full())))
    assert res.status == "committed", res.error
    scene_calls = [c for c in drafter.calls if c["role"] == "drafting" and "[THIS SCENE" in c["user_prompt"]]
    assert scene_calls and all("[WEBNOVEL STYLE" in c["user_prompt"] and "[AUTHOR DIRECTIVES" in c["user_prompt"] and "tide bell" in c["user_prompt"] for c in scene_calls)
    critic_call = next(c for c in drafter.calls if c["role"] == "critic")
    assert "[WEBNOVEL STYLE — grade against this]" in critic_call["user_prompt"] and "acquisitions editor" in critic_call["user_prompt"]
    polish_call = next(c for c in drafter.calls if c["role"] == "polish")
    assert "[WEBNOVEL STYLE — conventions to polish toward]" in polish_call["user_prompt"]
    craft = res.craft
    assert craft["webnovel_before"] and craft["webnovel_after"] and set(craft["webnovel_after"]["scores"]) == {"rhythm", "inner_voice", "conventions", "momentum", "reward", "ending"}
    assert craft["critic_after"]["source"] == "merged" and "webnovel_rhythm" in craft["critic_after"]["scores"]
    # Chapter 2 does not receive the chapter-1 directive but keeps the novel-wide one.
    with Session(engine) as s:
        ctx2 = ChapterContextCompiler(s).compile(project_id=pid, chapter_number=2)
        s.rollback()
    d2 = next(sec for sec in ctx2.sections if sec.key == "author_directives")
    assert "tide bell" not in d2.text and "flashbacks" in d2.text


# -------------------------------------------------------------- director
def test_director_redo_from_chapter_rewinds_and_requeues(app_client):
    """Run the fake pipeline to completion, then redo from chapter 4 with a note: chapters 1-3 stay, 4-6 are regenerated under the note."""
    from app.db.models import AutonomousNovelJob, Card, ChapterPipelineRun
    from app.db.session import engine
    from app.services.autonomous import director, runner as runner_mod
    from app.services.autonomous.audit import chapter_texts
    from app.services.forge import provenance
    from app.services.forge.webnovel import DirectiveService, WebnovelStyleService

    fake = ap.FakeClient()
    fake.faults = {"storyline_malformed": False, "architecture_bad": False, "draft_leak": False}
    client = app_client
    import base64

    r = client.post("/api/autonomous/jobs", json={
        "filename": "redo.epub", "content_base64": base64.b64encode(ap.build_source_epub()).decode(), "llm_config_id": _llm_config_id(client),
        "mode": "fully_automatic", "quality_preset": "economy", "subgenre": "hunter_gate", "platform": "munpia", "thought_style": "single_quotes",
        "directives": [{"scope": "novel", "kind": "must", "text": "The protagonist never begs."}], "auto_start": False, "preflight_acknowledged": True,
    })
    assert r.status_code == 200, r.text
    job_id = r.json()["job"]["id"]
    assert r.json()["job"]["status"] == "paused"  # auto_start=false parks the job for Director edits
    # Director before the project exists: style preview + pending directives are visible and editable.
    r = client.get(f"/api/autonomous/jobs/{job_id}/style")
    assert r.status_code == 200 and r.json()["engine"]["subgenre"] == "hunter_gate" and r.json()["platform"] == "munpia"
    r = client.patch(f"/api/autonomous/jobs/{job_id}/style", json={"narrator_register": "grim_survivor", "reader": {"comedy_level": "none"}})
    assert r.status_code == 200 and r.json()["narrator_register"] == "grim_survivor" and r.json()["reader"]["comedy_level"] == "none" and r.json()["derived_from"] == "author"
    # Switching subgenre re-seeds the template machinery (tier ladder, reader fantasy) but keeps the rest of the patch.
    r = client.patch(f"/api/autonomous/jobs/{job_id}/style", json={"engine": {"subgenre": "villainess_transmigration"}, "narrator_register": "grim_survivor"})
    assert r.status_code == 200 and r.json()["engine"]["subgenre"] == "villainess_transmigration" and "S" not in r.json()["engine"]["tier_ladder"] and r.json()["narrator_register"] == "grim_survivor"
    assert client.patch(f"/api/autonomous/jobs/{job_id}/style", json={"engine": {"subgenre": "not_a_genre"}}).status_code == 400
    r = client.patch(f"/api/autonomous/jobs/{job_id}/style", json={"engine": {"subgenre": "hunter_gate"}, "narrator_register": "grim_survivor", "reader": {"comedy_level": "none"}})
    assert r.status_code == 200 and r.json()["engine"]["subgenre"] == "hunter_gate" and r.json()["reader"]["comedy_level"] == "none"
    r = client.get(f"/api/autonomous/jobs/{job_id}/directives")
    assert r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["id"] == "pending-1"
    r = client.post(f"/api/autonomous/jobs/{job_id}/directives", json={"scope": "arc", "chapter_from": 2, "chapter_to": 3, "kind": "prefer", "text": "Keep the assessor in play."})
    assert r.status_code == 200 and r.json()["id"] == "pending-2"
    r = client.get(f"/api/autonomous/jobs/{job_id}/style/preview")
    assert r.status_code == 200 and "grim" in r.json()["drafting"]

    with Session(engine) as s:
        job = s.get(AutonomousNovelJob, job_id)
        runner_mod.resume(s, job)
        runner = ap._runner(s, job_id, fake)
        # Drive to storyline selection.
        for _ in range(12):
            job = asyncio.run(runner.step())
            if job.status == "waiting_for_user":
                break
        assert job.stage == "STORYLINE_SELECTION"
        from app.db.models import StorylineCandidate

        opt = s.exec(select(StorylineCandidate).where(StorylineCandidate.job_id == job_id, StorylineCandidate.rejected == False)).first()  # noqa: E712
        runner_mod.select_storyline(s, job, storyline_id=opt.id, chapter_count=ap.CHAPTERS)
        for _ in range(40):
            job = asyncio.run(runner.step())
            if job.status in ("completed", "failed", "cancelled", "waiting_for_user", "paused"):
                break
        assert job.status == "completed", (job.status, job.stage, job.error)
        pid = int(job.original_project_id)
        # The pre-selection edits landed on the project once it existed.
        prof = WebnovelStyleService(s).get(pid)
        assert prof is not None and prof.narrator_register == "grim_survivor" and prof.engine.subgenre == "hunter_gate" and prof.derived_from == "author"
        ids = [d.id for d in DirectiveService(s).book(pid).directives]
        assert len(ids) == 2 and all(i.startswith("dir-") for i in ids)
        assert "pending_directives" not in (job.options or {}) and "style_profile_override" not in (job.options or {}), sorted(job.options or {})
        # Every committed chapter run carries webnovel conformance in its craft report.
        runs = s.exec(select(ChapterPipelineRun).where(ChapterPipelineRun.project_id == pid, ChapterPipelineRun.status == "committed")).all()
        assert len(runs) == ap.CHAPTERS
        craft = (runs[0].validation_report or {}).get("craft") or {}
        assert craft.get("webnovel_after") and "scores" in craft["webnovel_after"]
        loop = job.stage_results["CHAPTER_GENERATION_LOOP"]
        assert loop["1"]["craft"]["webnovel_overall"] is not None
        # Whole-novel audit has the webnovel summary; export has the style summary and the new artifacts.
        assert job.stage_results["WHOLE_NOVEL_AUDIT"]["webnovel"]["profile"]["subgenre"] == "hunter_gate"
        assert job.stage_results["EXPORT"]["style_profile"]["platform"] == "munpia"
        before_texts = {n: text for n, _, text in chapter_texts(s, pid)}
        ch3_card_id = next(c.id for n, c, _ in chapter_texts(s, pid) if n == 3)

    # Redo plan preview and redo from chapter 4 with a note.
    r = client.get(f"/api/autonomous/jobs/{job_id}/redo/plan", params={"from_chapter": 4})
    assert r.status_code == 200 and r.json()["chapters_discarded"] == [4, 5, 6]
    r = client.get(f"/api/autonomous/jobs/{job_id}/redo/plan", params={"from_chapter": 99})
    assert r.status_code == 400
    r = client.post(f"/api/autonomous/jobs/{job_id}/redo", json={"from_chapter": 4, "note": "Chapter four must open at the assessor's desk.", "replan": True, "auto_start": False})
    assert r.status_code == 200, r.text
    body = r.json()["job"]
    assert body["stage"] == "CHAPTER_GENERATION_LOOP" and body["chapters_committed"] == 3 and body["quality_status"] is None and body["status"] == "paused"
    assert body["stage_results"].get("replan_from") == 4 and "EXPORT" not in body["stage_results"]

    with Session(engine) as s:
        job = s.get(AutonomousNovelJob, job_id)
        pid = int(job.original_project_id)
        manifest = provenance.get_manifest(s, pid)
        assert manifest.latest_committed_chapter == 3
        assert {n for n, _, _ in chapter_texts(s, pid)} == {1, 2, 3}
        assert s.get(Card, ch3_card_id) is not None
        d = [x for x in DirectiveService(s).book(pid).directives if x.scope == "chapter" and x.chapter_from == 4]
        assert len(d) == 1 and "assessor" in d[0].text
        # Runs for chapters >= 4 are superseded, so the compiler's previous-run check passes for chapter 5 later.
        assert all(r.status == "superseded" for r in s.exec(select(ChapterPipelineRun).where(ChapterPipelineRun.project_id == pid, ChapterPipelineRun.chapter_number >= 4)).all())
        # A running job refuses a redo until paused.
        job.status = "running"
        s.add(job)
        s.commit()
        with pytest.raises(director.DirectorError):
            director.redo_from_chapter(s, job, from_chapter=2)
        job.status = "paused"
        s.add(job)
        s.commit()
        runner_mod.resume(s, job)
        # Drive the regeneration to completion again: 4..6 regenerate, 1..3 untouched, artifacts rebuilt.
        runner = ap._runner(s, job_id, fake)
        calls_before = len(fake.calls)
        for _ in range(40):
            job = asyncio.run(runner.step())
            if job.status in ("completed", "failed", "cancelled", "waiting_for_user", "paused"):
                break
        assert job.status == "completed", (job.status, job.stage, job.error)
        after_texts = {n: text for n, _, text in chapter_texts(s, pid)}
        assert set(after_texts) == {1, 2, 3, 4, 5, 6}
        assert all(after_texts[n] == before_texts[n] for n in (1, 2, 3))
        s.refresh(manifest)
        assert manifest.latest_committed_chapter == 6
        # The note reached the chapter-4 prompts (planner + drafter) and the replan marker was consumed.
        prompts = [c for c in fake.calls[calls_before:] if c["stage"].startswith("DOWNSTREAM_REPLAN")]
        assert prompts, "director redo must trigger a replan window before drafting chapter 4"
        assert "replan_from" not in (job.stage_results or {})
        assert job.stage_results["redo_log"][-1]["from_chapter"] == 4
        book = DirectiveService(s).book(pid)
        note = next(x for x in book.directives if x.chapter_from == 4 and x.scope == "chapter")
        assert 4 in note.consumed_by_chapters
        assert len(s.exec(select(ChapterPipelineRun).where(ChapterPipelineRun.project_id == pid, ChapterPipelineRun.status == "committed")).all()) == ap.CHAPTERS
    r = client.get(f"/api/autonomous/jobs/{job_id}/chapters/4/quality")
    assert r.status_code == 200 and r.json()["webnovel_after"]["scores"]
    r = client.get(f"/api/autonomous/jobs/{job_id}/artifacts")
    assert r.status_code == 200 and {a["kind"] for a in r.json()} >= {"webnovel_text", "toc", "epub"}
    r = client.get("/api/autonomous/subgenres")
    assert r.status_code == 200 and any(x["key"] == "regression" for x in r.json())


def _llm_config_id(client) -> int:
    from app.db.models import LLMConfig
    from app.db.session import engine

    with Session(engine) as s:
        cfg = s.exec(select(LLMConfig).where(LLMConfig.provider == "authnd")).first()
        if cfg is None:
            cfg = LLMConfig(provider="authnd", model_name="moonshotai/kimi-k3", api_key="", display_name="Kimi K3 test")
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
        return int(cfg.id)
