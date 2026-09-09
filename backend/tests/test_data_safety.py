"""Data safety: server-side card revisions (snapshot before overwrite, restore), author locks on
Bible cards honoured by sync / architecture rebuilds, API-key masking with stored-key resolution,
and the pre-migration SQLite backup."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from sqlmodel import Session, create_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def client(app_client):
    return app_client


def _type_id(client, name: str) -> int:
    return next(t["id"] for t in client.get("/api/card-types").json() if t["name"] == name)


def _card(client, pid, type_name, title, content):
    r = client.post(f"/api/projects/{pid}/cards", json={"title": title, "content": content, "card_type_id": _type_id(client, type_name)})
    assert r.status_code in (200, 201), r.text
    return r.json()


def _project(client) -> int:
    return client.post("/api/projects/", json={"name": f"Safety {uuid.uuid4().hex[:6]}"}).json()["data"]["id"]


# ---------------------------------------------------------------- revisions

def test_user_save_snapshots_previous_content_and_restore_is_undoable(client):
    pid = _project(client)
    card = _card(client, pid, "Chapter Text", "Chapter 1", {"chapter_number": 1, "title": "One", "content": "First version of the chapter. " * 20})
    cid = card["id"]
    assert client.get(f"/api/cards/{cid}/revisions").json() == []
    # Saving unchanged content does not create history.
    client.put(f"/api/cards/{cid}", json={"content": card["content"]})
    assert client.get(f"/api/cards/{cid}/revisions").json() == []
    # A real edit snapshots the *previous* text.
    r = client.put(f"/api/cards/{cid}", json={"content": {**card["content"], "content": "Second version."}})
    assert r.status_code == 200
    revs = client.get(f"/api/cards/{cid}/revisions").json()
    assert len(revs) == 1 and revs[0]["reason"] == "user_save" and revs[0]["actor"] == "user" and revs[0]["chapter_number"] == 1 and revs[0]["word_count"] == 100
    assert "content" not in revs[0]
    full = client.get(f"/api/cards/{cid}/revisions/{revs[0]['id']}").json()
    assert full["content"]["content"].startswith("First version")
    # Restore brings the old text back and snapshots the text it replaced.
    r = client.post(f"/api/cards/{cid}/revisions/{revs[0]['id']}/restore")
    assert r.status_code == 200 and r.json()["content"]["content"].startswith("First version")
    revs = client.get(f"/api/cards/{cid}/revisions").json()
    assert [x["reason"] for x in revs] == ["restore", "user_save"]
    assert client.get(f"/api/cards/{cid}/revisions/{revs[0]['id']}").json()["content"]["content"] == "Second version."
    # Revisions belong to their card.
    other = _card(client, pid, "Chapter Text", "Chapter 2", {"chapter_number": 2, "content": "x"})
    assert client.get(f"/api/cards/{other['id']}/revisions/{revs[0]['id']}").status_code == 404
    assert client.post(f"/api/cards/{other['id']}/revisions/{revs[0]['id']}/restore").status_code == 404


def test_revision_history_is_bounded(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings.data_safety, "max_revisions_per_card", 3)
    pid = _project(client)
    card = _card(client, pid, "General Text", "Notes", {"content": "v0"})
    for i in range(1, 7):
        client.put(f"/api/cards/{card['id']}", json={"content": {"content": f"v{i}"}})
    revs = client.get(f"/api/cards/{card['id']}/revisions", params={"include_content": True}).json()
    assert [r["content"]["content"] for r in revs] == ["v5", "v4", "v3"]


def test_snapshot_disabled_when_limit_is_zero(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings.data_safety, "max_revisions_per_card", 0)
    pid = _project(client)
    card = _card(client, pid, "General Text", "Notes", {"content": "v0"})
    client.put(f"/api/cards/{card['id']}", json={"content": {"content": "v1"}})
    assert client.get(f"/api/cards/{card['id']}/revisions").json() == []


# ------------------------------------------------------------- author locks

def test_author_locks_module():
    from app.services.bible import author_locks as al

    content = {"trust": 50, "private_relationship": "allies", "author_locks": ["trust"]}
    allowed = al.guard(content, {"trust": 80, "private_relationship": "rivals"}, source="sync", chapter_number=4, reason="test")
    assert allowed == {"private_relationship": "rivals"}
    assert content["suppressed_updates"][0]["field"] == "trust" and content["suppressed_updates"][0]["proposed"] == 80 and content["suppressed_updates"][0]["source"] == "sync"
    # Unchanged proposals are not recorded as suppressed.
    al.guard(content, {"trust": 50}, source="sync")
    assert len(content["suppressed_updates"]) == 1
    merged = al.merge_guarded({"name": "A", "goal": "old", "author_locks": ["goal"]}, {"name": "A2", "goal": "new", "fear": "f"}, source="architecture")
    assert merged["goal"] == "old" and merged["name"] == "A2" and merged["fear"] == "f" and merged["author_locks"] == ["goal"]
    whole = al.merge_guarded({"name": "A", "goal": "old", "author_locks": ["*"]}, {"name": "A2", "goal": "new", "fear": "f"}, source="architecture")
    assert whole["name"] == "A" and whole["goal"] == "old" and whole["fear"] == "f"
    assert al.is_locked({"author_locks": ["voice"]}, "voice.sentence_tendency")
    assert not al.is_locked({}, "voice")


def test_locks_api_and_sync_respects_locks(client):
    from sqlmodel import Session

    from app.db.session import engine
    from app.services.forge import sync as sync_mod
    from app.services.forge.claims import Claim

    pid = _project(client)
    _card(client, pid, "Character Card", "Mira", {"name": "Mira", "aliases": [], "role_type": "Protagonist"})
    _card(client, pid, "Character Card", "Daren", {"name": "Daren", "aliases": [], "role_type": "Deuteragonist"})
    rel = _card(client, pid, "Relationship Arc", "Mira ↔ Daren", {"character_a": "Mira", "character_b": "Daren", "private_relationship": "wary allies", "trust": 40})
    promise = _card(client, pid, "Promise Payoff", "The drawer", {"setup": "A locked drawer", "planned_payoff": "It holds the letter", "status": "planted", "target_payoff_range": [1, 3]})
    chapter = _card(client, pid, "Chapter Text", "Chapter 1", {"chapter_number": 1, "content": "Mira and Daren argue. Daren says he trusts her now.", "entity_list": ["Mira", "Daren"]})
    r = client.put(f"/api/bible/cards/{rel['id']}/locks", json={"fields": ["private_relationship"]})
    assert r.status_code == 200 and r.json()["locks"] == ["private_relationship"]
    client.put(f"/api/bible/cards/{promise['id']}/locks", json={"fields": ["status"]})
    with Session(engine) as session:
        claims = [Claim(kind="relationship_changed", subject="Mira ↔ Daren", value="close allies", support="explicit", evidence="Daren says he trusts her now", span=(0, 20))]
        rep = sync_mod.synchronize_chapter(session, project_id=pid, chapter_number=1, chapter_card_id=chapter["id"], pov="Mira", participants=["Mira", "Daren"], prose=chapter["content"]["content"], claims=claims, model_claims=None, allowed_outcomes=["It holds the letter"])
        assert rep["canon_revision_after"] == rep["canon_revision_before"] + 1
    rel_after = client.get(f"/api/cards/{rel['id']}").json()["content"]
    assert rel_after["private_relationship"] == "wary allies"  # locked: not rewritten
    locks = client.get(f"/api/bible/cards/{rel['id']}/locks").json()
    assert locks["suppressed_updates"] and locks["suppressed_updates"][0]["proposed"] == "close allies" and locks["suppressed_updates"][0]["source"] == "sync"
    promise_after = client.get(f"/api/cards/{promise['id']}").json()["content"]
    assert promise_after["status"] == "planted"  # locked status survives an authorised payoff
    # Clearing suppressed updates after review.
    assert client.delete(f"/api/bible/cards/{rel['id']}/locks/suppressed").json()["suppressed_updates"] == []
    # Removing the lock lets the next sync write.
    client.put(f"/api/bible/cards/{rel['id']}/locks", json={"fields": []})
    assert client.get(f"/api/bible/cards/{rel['id']}/locks").json()["locks"] == []


def test_architecture_upsert_keeps_locked_fields_and_snapshots(client):
    from sqlmodel import Session

    from app.db.session import engine
    from app.services.autonomous.architecture import _upsert

    pid = _project(client)
    card = _card(client, pid, "Story Foundation", "Story Foundation", {"core_premise": "AUTHOR PREMISE", "stakes": "old stakes", "author_locks": ["core_premise"]})
    with Session(engine) as session:
        _upsert(session, pid, "Story Foundation", "Story Foundation", {"core_premise": "GENERATED PREMISE", "stakes": "new stakes"})
        session.commit()
    after = client.get(f"/api/cards/{card['id']}").json()["content"]
    assert after["core_premise"] == "AUTHOR PREMISE" and after["stakes"] == "new stakes" and after["author_locks"] == ["core_premise"]
    assert after["suppressed_updates"][0]["proposed"] == "GENERATED PREMISE"
    revs = client.get(f"/api/cards/{card['id']}/revisions").json()
    assert revs and revs[0]["reason"] == "ai_generation"


# --------------------------------------------------------------- api keys

def test_api_key_is_masked_in_reads_and_preserved_on_update(client):
    from sqlmodel import Session

    from app.db.models import LLMConfig
    from app.db.session import engine

    r = client.post("/api/llm-configs/", json={"provider": "openai_compatible", "model_name": "m", "api_key": "sk-secret-1234567890", "api_base": "http://127.0.0.1:9/v1", "display_name": "masked"})
    assert r.status_code == 200, r.text
    cfg = r.json()["data"]
    assert cfg["api_key"] == "••••7890"
    listed = next(c for c in client.get("/api/llm-configs/").json()["data"] if c["id"] == cfg["id"])
    assert listed["api_key"] == "••••7890" and "sk-secret" not in str(listed)
    # Saving the form with the masked value keeps the real key; a new value replaces it.
    r = client.put(f"/api/llm-configs/{cfg['id']}", json={"display_name": "renamed", "api_key": "••••7890"})
    assert r.status_code == 200 and r.json()["data"]["display_name"] == "renamed"
    with Session(engine) as session:
        assert session.get(LLMConfig, cfg["id"]).api_key == "sk-secret-1234567890"
    client.put(f"/api/llm-configs/{cfg['id']}", json={"api_key": "sk-new-key-0000"})
    with Session(engine) as session:
        assert session.get(LLMConfig, cfg["id"]).api_key == "sk-new-key-0000"
    copied = client.post(f"/api/llm-configs/{cfg['id']}/copy").json()["data"]
    assert copied["api_key"] == "••••0000"


def test_resolve_api_key_prefers_stored_key_for_masked_values(client):
    from sqlmodel import Session

    from app.db.session import engine
    from app.services.llm_config_service import resolve_api_key

    cfg = client.post("/api/llm-configs/", json={"provider": "openai_compatible", "model_name": "m", "api_key": "real-key-abcd", "api_base": "http://127.0.0.1:9/v1"}).json()["data"]
    with Session(engine) as session:
        assert resolve_api_key(session, api_key="••••abcd", config_id=cfg["id"]) == "real-key-abcd"
        assert resolve_api_key(session, api_key="", config_id=cfg["id"]) == "real-key-abcd"
        assert resolve_api_key(session, api_key="typed-key", config_id=cfg["id"]) == "typed-key"
        assert resolve_api_key(session, api_key="••••abcd", config_id=None) == ""


# ------------------------------------------------------------------ backups

def test_sqlite_backup_before_migration(tmp_path: Path):
    from alembic import command
    from app.db import migrations

    db = tmp_path / "novel.db"
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    # A database genuinely at the previous revision (built by upgrading to that target only).
    with engine.connect() as conn:
        cfg = migrations.alembic_config(engine)
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0006_budget_dispatch")
        conn.commit()
    with Session(engine) as s:
        from app.db.models import Project

        s.add(Project(name="keep me"))
        s.commit()
    assert not list(tmp_path.glob("*.bak"))
    info = migrations.upgrade_database(engine, backup=True)
    assert info["before"] == "0006_budget_dispatch" and info["after"] == migrations.head_revision()
    assert info["backup"] and Path(info["backup"]).exists() and ".pre-0006_budget_dispatch-" in info["backup"]
    # The backup is a valid database containing the author's data, at the old revision.
    import sqlite3

    with sqlite3.connect(info["backup"]) as conn:
        assert conn.execute("select name from project").fetchone()[0] == "keep me"
        assert conn.execute("select version_num from alembic_version").fetchone()[0] == "0006_budget_dispatch"
    # Already at head: no new backup is written.
    info2 = migrations.upgrade_database(engine, backup=True)
    assert info2["backup"] is None and len(list(tmp_path.glob("novel.db.pre-*.bak"))) == 1
    # A fresh, empty database is never backed up.
    fresh = create_engine(f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}")
    assert migrations.upgrade_database(fresh, backup=True)["backup"] is None
    # Pruning keeps the newest N copies.
    for _ in range(3):
        migrations.backup_sqlite_before_migration(engine, keep=2)
    assert len(list(tmp_path.glob("novel.db.pre-*.bak"))) == 2
    engine.dispose()
    fresh.dispose()
