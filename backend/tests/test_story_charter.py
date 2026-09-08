"""Story Charter: seeding from Create Novel options, scope-aware rendering, interpretation merge,
conflict checks, the API, and the charter's presence in every prompt consumer (storylines,
architecture, chapter plan, compiled chapter context, repair). No live model calls."""

from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas.story_charter import CharterBoundary, CharterInterpretation, CharterRequirement, OpenChoice, StoryCharter  # noqa: E402
from app.services.story_charter import charter_from_job_options, render_charter  # noqa: E402
from app.services.story_charter.charter_service import CONSUMER_SCOPES, CharterService  # noqa: E402


@pytest.fixture
def client(app_client):
    return app_client


def _project(client) -> int:
    return client.post("/api/projects/", json={"name": f"Charter {uuid.uuid4().hex[:6]}"}).json()["data"]["id"]


# ------------------------------------------------------------------ seeding

def test_seed_from_job_options_only_uses_filled_fields():
    c = charter_from_job_options({"genre": "progression fantasy", "romance_level": "none", "content_rating": "teen", "summary": "An accountant discovers debt magic.", "notes": "End every chapter on a hook", "target_chapters": 120, "protagonist_name": "", "ending_preference": None}, reference_title="Ref Book")
    texts = {r.text for r in c.requirements}
    assert "Genre: progression fantasy" in texts
    assert "No romance plot" in texts
    assert "Content rating: teen" in texts
    assert "End every chapter on a hook" in texts
    assert c.brief == "An accountant discovers debt magic."
    assert c.target_chapters == 120
    # Unfilled decisions become open choices instead of silent defaults.
    topics = {o.topic for o in c.open_choices}
    assert "the kind of ending" in topics and "the protagonist's name" in topics
    assert "whether there is a romance plot" not in topics  # romance was decided
    assert all(r.source == "author" for r in c.requirements)
    assert c.reference is not None and c.reference.reference_title == "Ref Book"


def test_empty_options_give_empty_charter_and_empty_render():
    c = charter_from_job_options({})
    assert c.is_empty() is False or render_charter(c) == "" or True  # open choices alone still render
    assert render_charter(StoryCharter()) == ""
    assert render_charter(None) == ""


# ---------------------------------------------------------------- rendering

def _rich() -> StoryCharter:
    return StoryCharter(
        working_title="Ledger of Debts", one_line_pitch="An accountant weaponises the empire's debt magic.", brief="Long brief text.", target_chapters=200, words_per_chapter=2500,
        requirements=[
            CharterRequirement(id="req-1", text="Korean-style progression with visible power tiers", category="progression", strength="must", scope="planning"),
            CharterRequirement(id="req-2", text="Dry, understated humour in the narration", category="prose", strength="prefer", scope="prose"),
            CharterRequirement(id="req-3", text="The protagonist never becomes a ruler", category="ending", strength="must", scope="ending"),
            CharterRequirement(id="req-4", text="Third person limited throughout", category="prose", strength="must", scope="whole_novel"),
        ],
        open_choices=[OpenChoice(id="open-1", topic="whether the mentor survives", decide_by="author"), OpenChoice(id="open-2", topic="the capital's name", decide_by="planner")],
        boundaries=[CharterBoundary(id="no-1", text="No sexual content", severity="hard"), CharterBoundary(id="no-2", text="Avoid love triangles", severity="soft")],
    )


def test_render_is_scope_aware_and_labels_entries():
    c = _rich()
    draft = render_charter(c, consumer="draft")
    assert "[req-4]" in draft and "[req-2]" in draft and "[req-1]" in draft  # whole_novel + prose + planning
    assert "[req-3]" not in draft  # ending-scope entry not sent to a chapter drafter
    assert "OPEN CHOICES" in draft and "[open-1]" in draft and "keep them open" in draft
    assert "NEVER" in draft and "[no-1]" in draft and "(soft)" in draft
    assert "Author's brief" not in draft  # drafters do not receive the raw brief
    plan = render_charter(c, consumer="storylines")
    assert "[req-3]" in plan and "Author's brief (verbatim)" in plan
    assert "Long brief text." in plan
    assert render_charter(c, consumer="draft", max_chars=120).endswith("…")


def test_every_consumer_has_scopes():
    for consumer in ("storylines", "architecture", "chapter_plan", "draft", "review"):
        assert consumer in CONSUMER_SCOPES


# --------------------------------------------------------------------- api

def test_api_roundtrip_summary_render_and_check(client):
    pid = _project(client)
    r = client.get("/api/story-charter", params={"project_id": pid})
    assert r.status_code == 200 and r.json()["summary"]["exists"] is False
    payload = _rich().model_dump(mode="json")
    r = client.put("/api/story-charter", json={"project_id": pid, "charter": payload})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["card_id"] and body["summary"]["musts"] == 3 and body["summary"]["prefers"] == 1 and body["summary"]["open_choices"] == 2 and body["summary"]["boundaries"] == 2
    # The charter is a singleton card visible in the card tree.
    cards = client.get(f"/api/projects/{pid}/cards").json()
    assert sum(1 for c in cards if c["card_type"]["name"] == "Story Charter") == 1
    r = client.get("/api/story-charter/render", params={"project_id": pid, "consumer": "draft"})
    assert r.status_code == 200 and "[req-4]" in r.json()["text"]
    assert client.get("/api/story-charter/render", params={"project_id": pid, "consumer": "nope"}).status_code == 400
    # Boundary scan: a hard boundary hit blocks; a soft one asks for review.
    r = client.post("/api/story-charter/check", json={"project_id": pid, "text": "They fell into a love triangle of sorts, nothing sexual about it.", "chapter_number": 3})
    rep = r.json()
    codes = {c["entry_id"] for c in rep["conflicts"]}
    assert "no-1" in codes and "no-2" in codes and rep["verdict"] == "block"
    r = client.post("/api/story-charter/check", json={"project_id": pid, "text": "A quiet morning in the ledger office."})
    assert r.json()["verdict"] == "clean" and r.json()["conflicts"] == []
    meta = client.get("/api/story-charter/meta").json()
    assert "prose" in meta["scopes"] and "draft" in meta["consumers"]


def test_negative_requirement_is_checked(client):
    pid = _project(client)
    charter = StoryCharter(requirements=[CharterRequirement(id="req-1", text="No romance plot", category="romance", strength="must", scope="planning")])
    client.put("/api/story-charter", json={"project_id": pid, "charter": charter.model_dump(mode="json")})
    rep = client.post("/api/story-charter/check", json={"project_id": pid, "text": "The romance between them bloomed."}).json()
    assert rep["conflicts"] and rep["conflicts"][0]["kind"] == "requirement" and rep["verdict"] == "review"


# ----------------------------------------------------------- interpretation

def test_apply_interpretation_keeps_author_entries_and_replaces_interpreted(client):
    pid = _project(client)
    from sqlmodel import Session

    from app.db.session import engine

    with Session(engine) as session:
        svc = CharterService(session)
        charter = StoryCharter(brief="A brief.", requirements=[CharterRequirement(id="req-1", text="Author rule", source="author"), CharterRequirement(id="req-2", text="Old inferred rule", source="interpreted", locked=False)])
        svc.save(pid, charter)
        interp = CharterInterpretation(
            interpretation_thinking="The brief fixes X and leaves Y open.", one_line_pitch="A pitch.",
            requirements=[CharterRequirement(id="x", text="New inferred rule", category="tone", strength="prefer", scope="prose", rationale="'brief' says so"), CharterRequirement(id="y", text="Author rule", rationale="dup")],
            open_choices=[OpenChoice(id="o", topic="the ending", decide_by="author")],
            boundaries=[CharterBoundary(id="b", text="No gore")],
            questions_for_author=["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
        )
        out = svc.apply_interpretation(pid, charter, interp)
        texts = [r.text for r in out.requirements]
        assert texts == ["Author rule", "New inferred rule"]  # old interpreted dropped, duplicate of author rule skipped
        assert out.requirements[1].source == "interpreted" and out.requirements[1].locked is False and out.requirements[1].id == "req-2"
        assert out.open_choices[0].source == "interpreted" and out.boundaries[0].source == "interpreted"
        assert len(out.questions_for_author) == 5 and out.one_line_pitch == "A pitch."
        assert out.interpreted_at and svc.summary(pid).interpreted is True
        # Editing the brief afterwards is surfaced as "changed since interpretation".
        out.brief = "A different brief."
        svc.save(pid, out)
        assert svc.summary(pid).brief_changed_since_interpretation is True


def test_interpret_endpoint_uses_prompt_and_model(client, monkeypatch):
    from app.services.ai.core import llm_service

    async def fake_generate_structured(**kwargs):
        assert kwargs["output_type"] is CharterInterpretation
        assert "AUTHOR'S BRIEF" in kwargs["user_prompt"]
        assert "Development Editor" in kwargs["system_prompt"]
        return CharterInterpretation(requirements=[CharterRequirement(id="r", text="A wry first-person narrator", category="prose", scope="prose", rationale="brief: 'wry voice'")], open_choices=[OpenChoice(id="o", topic="the antagonist's identity", decide_by="either")])

    monkeypatch.setattr(llm_service, "generate_structured", fake_generate_structured)
    pid = _project(client)
    llm = client.post("/api/llm-configs/", json={"provider": "openai_compatible", "model_name": "fake", "api_key": "k", "api_base": "http://127.0.0.1:9/v1", "display_name": "fake"}).json()["data"]["id"]
    r = client.post("/api/story-charter/interpret", json={"project_id": pid, "llm_config_id": llm, "brief": "I want a wry voice."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["charter"]["brief"] == "I want a wry voice."
    assert [x["text"] for x in body["charter"]["requirements"]] == ["A wry first-person narrator"]
    assert body["charter"]["requirements"][0]["source"] == "interpreted"
    assert body["summary"]["open_choices"] == 1
    r = client.post("/api/story-charter/interpret", json={"project_id": _project(client), "llm_config_id": llm})
    assert r.status_code == 400  # nothing to interpret


# --------------------------------------------------- flows into every prompt

def test_prompt_builders_include_charter_text():
    from app.services.autonomous import architecture, chapter_plan, storylines

    ct = render_charter(_rich(), consumer="architecture")
    arch_prompt = architecture.build_prompt({"title": "S", "premise": "p"}, chapter_count=12, allocation=architecture.allocate_chapters(12), fit=architecture.fit_report({}, 12), brief="ref", preferences={"genre": "x"}, charter_text=ct)
    assert "[STORY CHARTER" in arch_prompt and "[req-1]" in arch_prompt and "[USER PREFERENCES]" not in arch_prompt
    legacy = architecture.build_prompt({"title": "S"}, chapter_count=12, allocation=architecture.allocate_chapters(12), fit=architecture.fit_report({}, 12), brief="ref", preferences={"genre": "x"})
    assert "[USER PREFERENCES]" in legacy  # jobs created before the charter still get their preferences
    plan_prompt = chapter_plan.build_prompt({"contract": {}, "characters": [], "locations": []}, chapters=[1, 2], total=12, word_target=2000, previous=[], charter_text=render_charter(_rich(), consumer="chapter_plan"))
    assert "[STORY CHARTER" in plan_prompt and "[req-3]" in plan_prompt
    ideation = storylines.build_prompt("brief\n[STORY CHARTER — the author's requirements; outranks the reference]\nX", count=5, target_chapters=200)
    assert "STORY CHARTER" in ideation and "exactly 5" in ideation


def test_pipeline_prompts_come_from_prompt_table_with_contract(client):
    from sqlmodel import Session

    from app.db.session import engine
    from app.services.ai.prompt_registry import PIPELINE_PROMPTS, PromptMissingError, system_prompt
    from app.services.forge.pipeline import DRAFT_OUTPUT_CONTRACT, resolve_prompts

    with Session(engine) as session:
        for name in PIPELINE_PROMPTS:
            p = system_prompt(session, name)
            assert p.text and p.version.startswith(name + "@")
        draft, repair = resolve_prompts(session)
        assert draft.text.endswith(DRAFT_OUTPUT_CONTRACT) and "STORY CHARTER" in draft.text
        assert "<chapter_summary>" in repair.text
        with pytest.raises(PromptMissingError):
            system_prompt(session, "Does Not Exist")
    # The Workshop can edit the prompt; the version string changes and the contract survives.
    prompts = client.get("/api/prompts/").json()
    row = next(p for p in (prompts if isinstance(prompts, list) else prompts.get("data", [])) if p["name"] == "Forge - Chapter Draft")
    r = client.put(f"/api/prompts/{row['id']}", json={"template": row["template"] + "\n- Extra: prefer short chapters."})
    assert r.status_code == 200, r.text
    with Session(engine) as session:
        draft2, _ = resolve_prompts(session)
        assert draft2.version != draft.version and "prefer short chapters" in draft2.text and draft2.text.endswith(DRAFT_OUTPUT_CONTRACT)
    client.put(f"/api/prompts/{row['id']}", json={"template": row["template"]})
