import json
from datetime import date
from unittest.mock import patch

from src.config import load_config
from src.fetch_sources import assemble_context
from src.render_page import render


def test_render_produces_html_with_all_sections(fixtures_dir, load_fixture):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    retrospective = load_fixture("retrospective.json")
    margin_flags = load_fixture("margin_flags.json")

    gcal_general = load_fixture("gcal_general_events.json")
    gcal_meals = load_fixture("gcal_meal_events.json")
    gcal_school = load_fixture("gcal_school_events.json")
    gmail_d = load_fixture("gmail_dalton.json")
    gmail_m = load_fixture("gmail_maggie.json")
    gmail_ks = load_fixture("gmail_kid_school.json")
    todoist_meals = load_fixture("todoist_meals.json")
    todoist_dn = load_fixture("todoist_date_night.json")
    todoist_st = load_fixture("todoist_screen_time.json")
    todoist_deadlines = load_fixture("todoist_deadlines.json")

    def fake_run_skill(path, args):
        path = str(path)
        if "list-events.sh" in path:
            cal_id = args[args.index("--calendar-id") + 1]
            if cal_id == cfg.calendars.shared_meals:
                return gcal_meals
            if cal_id == cfg.calendars.shared_general:
                return gcal_general
            if cal_id == cfg.calendars.dalton_personal:
                return []
            return gcal_school
        if "search-emails.sh" in path:
            account = args[args.index("--account") + 1]
            query = args[args.index("--query") + 1]
            if "label:" in query:
                return gmail_ks
            return gmail_d if account == "dalton" else gmail_m
        return []

    def fake_todoist_get(path, params=None):
        if params and "project_id" in params:
            pid = params["project_id"]
            if pid == cfg.todoist.project_id("meals"):
                return todoist_meals
            if pid == cfg.todoist.project_id("date_night_ideas"):
                return todoist_dn
            if pid == cfg.todoist.project_id("screen_time"):
                return todoist_st
            return []
        return todoist_deadlines

    with patch("src.fetch_sources._run_skill", side_effect=fake_run_skill), \
         patch("src.fetch_sources._todoist_get", side_effect=fake_todoist_get):
        ctx = assemble_context(cfg, today=date(2026, 5, 21))

    html = render(ctx=ctx, retrospective=retrospective, margin_flags=margin_flags,
                  cfm_lesson_title="2 Nephi 1-5")

    # Section anchors all present
    for needle in [
        "Last week — what happened",
        "Week ahead at a glance",
        "Horizon",
        "Heads-up",
        "Dinners",
        "Shopping list",
        "Dalton's home schedule",
        "Maggie's art time",
        "Babysitter",
        "Kids' activities",
        "Church + temple",
        "Around the house",
        "Major deadlines",
        "Finances",
        "Come Follow Me",
        "Fun close",
        "Save & write back",
    ]:
        assert needle in html, f"missing section: {needle}"

    # Retrospective + flags rendered
    assert "Three home dinners" in html
    assert "Tuesday has 3 evening events" in html

    # Pre-loaded school events shown
    assert "Field Day" in html

    # Meals library appears as datalist options
    assert "Sheet pan chicken thighs" in html

    # Date night suggestions surfaced
    assert "ramen" in html or "canal" in html

    # CFM lesson title
    assert "2 Nephi" in html
