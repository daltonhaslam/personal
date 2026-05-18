import json
from unittest.mock import patch

from src.config import load_config
from src.server import create_app


def test_get_root_serves_session_html(fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setattr("src.server.PROJECT_ROOT", tmp_path)
    (tmp_path / "session.html").write_text("<html><body>HELLO FORM</body></html>")
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    app = create_app(cfg)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"HELLO FORM" in resp.data


def test_post_save_happy_path_returns_summary_html(fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setattr("src.write_back.SESSIONS_DIR", tmp_path)
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    app = create_app(cfg)
    client = app.test_client()

    form = {
        "dinner_2026-05-22": "Tacos",
        "shopping_necessary": "milk",
        "babysitter_needed": False,
    }
    with patch("src.write_back._run_skill", return_value={"id": "x"}):
        resp = client.post("/save", json=form)
    assert resp.status_code == 200
    assert b"Tacos" in resp.data
    assert b"Saved" in resp.data


def test_post_save_validation_error_returns_400(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    app = create_app(cfg)
    client = app.test_client()
    bad = {"babysitter_needed": True, "babysitter_date": "", "babysitter_time": "", "babysitter_who": ""}
    resp = client.post("/save", json=bad)
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["status"] == "validation_error"
    assert len(payload["errors"]) > 0
