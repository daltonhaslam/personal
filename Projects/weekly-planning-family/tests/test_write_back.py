import subprocess
import pytest
from unittest.mock import patch

from src.config import load_config
from src.write_back import (
    CalendarWriteResult,
    ValidationError,
    parse_form,
    run_save,
    validate,
    write_calendar,
    write_todoist,
)


SAMPLE_FORM = {
    "retrospective_note": "good week",
    # dinners
    "dinner_2026-05-22": "Tacos",
    "dinner_2026-05-23": "Pasta Bolognese",
    "dinner_2026-05-24": "Eating out: ramen place",
    "dinner_2026-05-25": "",
    "dinner_2026-05-26": "",
    "dinner_2026-05-27": "",
    "dinner_2026-05-28": "",
    "new_meal": "Thai curry",
    "shopping_necessary": "milk\neggs\nbananas\n",
    "shopping_wants": "sourdough starter\n",
    # home schedule
    "wfh_2026-05-25": True,
    "home_by_2026-05-25": "",
    "wfh_2026-05-26": False,
    "home_by_2026-05-26": "17:00",
    "wfh_2026-05-27": False,
    "home_by_2026-05-27": "",
    "wfh_2026-05-28": True,
    "home_by_2026-05-28": "",
    # art blocks
    "art_date_0": "2026-05-24",
    "art_start_0": "14:00",
    "art_end_0": "16:00",
    "art_date_1": "",
    # babysitter
    "babysitter_needed": True,
    "babysitter_date": "2026-05-24",
    "babysitter_time": "18:00",
    "babysitter_who": "Sarah",
    # kid activities
    "kid_activity_title_0": "Soccer tryout",
    "kid_activity_date_0": "2026-05-23",
    "kid_activity_time_0": "10:00",
    "kid_activity_owner_0": "Both",
    "church_notes": "Temple Fri 10am\nMinistering visit",
    "home_notes": "Replace bathroom faucet\nClean gutters",
    "new_deadlines": "Renew passport - June 1",
    "finances_notes": "Revisit budget",
    "cfm_notes": "Both teaching",
    # date night
    "date_night_choice": "Out: ramen place",
    "date_night_date": "2026-05-24",
    "date_night_time": "19:00",
}


def test_parse_form_extracts_dinners():
    decisions = parse_form(SAMPLE_FORM)
    dinners = [d for d in decisions["dinners"] if d["meal"]]
    assert len(dinners) == 3
    assert dinners[0]["day"] == "2026-05-22"
    assert dinners[0]["meal"] == "Tacos"


def test_parse_form_extracts_shopping_lines():
    d = parse_form(SAMPLE_FORM)
    assert d["shopping_necessary"] == ["milk", "eggs", "bananas"]
    assert d["shopping_wants"] == ["sourdough starter"]


def test_parse_form_home_schedule_separates_wfh_and_homeby():
    d = parse_form(SAMPLE_FORM)
    items = {x["day"]: x for x in d["home_schedule"]}
    assert items["2026-05-25"]["wfh"] is True
    assert items["2026-05-26"]["wfh"] is False
    assert items["2026-05-26"]["home_by"] == "17:00"
    assert items["2026-05-27"]["wfh"] is False
    assert items["2026-05-27"]["home_by"] == ""


def test_parse_form_art_blocks_skips_empty_rows():
    d = parse_form(SAMPLE_FORM)
    assert len(d["art_blocks"]) == 1
    assert d["art_blocks"][0]["date"] == "2026-05-24"
    assert d["art_blocks"][0]["start"] == "14:00"


def test_parse_form_babysitter_only_when_needed():
    d = parse_form(SAMPLE_FORM)
    assert d["babysitter"]["who"] == "Sarah"
    form2 = dict(SAMPLE_FORM)
    form2["babysitter_needed"] = False
    d2 = parse_form(form2)
    assert d2["babysitter"] is None


def test_parse_form_kids_activities_skips_blanks():
    d = parse_form(SAMPLE_FORM)
    assert len(d["kids_activities"]) == 1
    assert d["kids_activities"][0]["title"] == "Soccer tryout"


def test_validate_passes_on_well_formed_form():
    d = parse_form(SAMPLE_FORM)
    errors = validate(d)
    assert errors == []


def test_validate_flags_babysitter_missing_date():
    form2 = dict(SAMPLE_FORM)
    form2["babysitter_date"] = ""
    d = parse_form(form2)
    errors = validate(d)
    assert any("babysitter" in e.field and "date" in e.message.lower() for e in errors)


def test_validate_flags_art_block_missing_end_time():
    form2 = dict(SAMPLE_FORM)
    form2["art_end_0"] = ""
    d = parse_form(form2)
    errors = validate(d)
    assert any("art" in e.field.lower() for e in errors)


def test_write_calendar_wfh_true_creates_all_day(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [],
        "home_schedule": [{"day": "2026-05-25", "wfh": True, "home_by": ""}],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    with patch("src.write_back._run_skill", return_value={"id": "ev1", "summary": "Dalton WFH"}) as mock:
        result = write_calendar(decisions, cfg)
    create_calls = [c for c in mock.call_args_list if "add-event.sh" in str(c.args[0])]
    assert len(create_calls) == 1
    args = create_calls[0].args[1]
    assert "--all-day" in args
    assert "--date" in args
    assert "2026-05-25" in args
    assert args[args.index("--title") + 1] == "Dalton WFH"
    assert args[args.index("--calendar-id") + 1] == cfg.calendars.shared_general
    assert result.created == 1
    assert result.failed == 0


def test_write_calendar_home_by_creates_15min_event(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [],
        "home_schedule": [{"day": "2026-05-26", "wfh": False, "home_by": "17:00"}],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    with patch("src.write_back._run_skill", return_value={"id": "ev2", "summary": "Dalton home"}) as mock:
        result = write_calendar(decisions, cfg)
    create_args = mock.call_args_list[0].args[1]
    assert "--all-day" not in create_args
    assert create_args[create_args.index("--start") + 1] == "2026-05-26T17:00"
    assert create_args[create_args.index("--end") + 1] == "2026-05-26T17:15"
    assert create_args[create_args.index("--title") + 1] == "Dalton home"
    assert result.created == 1


def test_write_calendar_dinners_all_day_on_meal_cal(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [
            {"day": "2026-05-22", "meal": "Tacos"},
            {"day": "2026-05-23", "meal": "Pasta"},
        ],
        "home_schedule": [],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    calls_by_cal = {}
    def fake_run(path, args):
        cal_id = args[args.index("--calendar-id") + 1]
        calls_by_cal.setdefault(cal_id, []).append(args)
        return {"id": f"ev-{cal_id}"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_calendar(decisions, cfg)
    assert cfg.calendars.shared_meals in calls_by_cal
    meal_calls = calls_by_cal[cfg.calendars.shared_meals]
    assert len(meal_calls) == 2
    for call_args in meal_calls:
        assert "--all-day" in call_args


def test_write_calendar_records_failed_writes(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [{"day": "2026-05-22", "meal": "Tacos"}],
        "home_schedule": [],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    def fake_run(path, args):
        raise subprocess.CalledProcessError(1, args, output="", stderr="oops")
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_calendar(decisions, cfg)
    assert result.created == 0
    assert result.failed == 1
    assert "oops" in result.errors[0]


def test_write_todoist_routes_shopping_to_to_buy(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": ["milk", "eggs"],
        "shopping_wants": ["sourdough"],
        "home_lines": [],
        "new_deadlines": [],
        "church_lines": [],
        "new_meal": "",
    }
    calls = []
    def fake_run(path, args):
        calls.append({"path": str(path), "args": args})
        return {"id": "x", "content": "ok"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_todoist(decisions, cfg)
    project_ids_called = [c["args"][c["args"].index("--project-id") + 1] for c in calls]
    assert project_ids_called.count(cfg.todoist.project_id("shopping")) == 2
    assert project_ids_called.count(cfg.todoist.project_id("shopping_wants")) == 1
    assert result.created == 3
    assert result.failed == 0


def test_write_todoist_routes_home_to_home_project(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": [],
        "shopping_wants": [],
        "home_lines": ["Fix faucet", "Clean gutters"],
        "new_deadlines": [],
        "church_lines": [],
        "new_meal": "",
    }
    calls = []
    def fake_run(path, args):
        calls.append(args)
        return {"id": "x"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_todoist(decisions, cfg)
    home_id = cfg.todoist.project_id("home")
    assert all(home_id in c for c in calls)
    assert result.created == 2


def test_write_todoist_routes_new_meal_to_meals(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": [], "shopping_wants": [],
        "home_lines": [], "new_deadlines": [], "church_lines": [],
        "new_meal": "Thai green curry",
    }
    calls = []
    def fake_run(path, args):
        calls.append(args)
        return {"id": "x"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        write_todoist(decisions, cfg)
    assert len(calls) == 1
    assert calls[0][calls[0].index("--content") + 1] == "Thai green curry"
    assert calls[0][calls[0].index("--project-id") + 1] == cfg.todoist.project_id("meals")


def test_write_todoist_omits_due_and_priority_except_for_major_deadlines(fixtures_dir):
    """Most items go in with no due/priority; only 'Major deadlines' get today+p2."""
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": ["apples"],
        "shopping_wants": [],
        "home_lines": ["fix faucet"],
        "new_deadlines": ["renew passports"],
        "church_lines": ["sign up to teach primary"],
        "new_meal": "thai curry",
    }
    calls = []
    def fake_run(path, args):
        calls.append(args)
        return {"id": "x"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        write_todoist(decisions, cfg)

    def args_for(content):
        return next(a for a in calls if a[a.index("--content") + 1] == content)

    for content in ["apples", "fix faucet", "sign up to teach primary", "thai curry"]:
        a = args_for(content)
        assert a[a.index("--due-string") + 1] == "", f"{content} should have no due"
        assert a[a.index("--priority") + 1] == "", f"{content} should have no priority"

    a = args_for("renew passports")
    assert a[a.index("--due-string") + 1] == "today"
    assert a[a.index("--priority") + 1] == "3"


def test_run_save_validation_failure_returns_400_payload(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    bad_form = {"babysitter_needed": True, "babysitter_date": "", "babysitter_time": "", "babysitter_who": ""}
    response = run_save(bad_form, cfg)
    assert response["status"] == "validation_error"
    assert len(response["errors"]) >= 3


def test_run_save_happy_path_writes_and_archives(fixtures_dir, tmp_path, monkeypatch):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    monkeypatch.setattr("src.write_back.SESSIONS_DIR", tmp_path)
    form = dict(SAMPLE_FORM)
    with patch("src.write_back._run_skill", return_value={"id": "x"}):
        response = run_save(form, cfg)
    assert response["status"] == "ok"
    assert "summary_html" in response
    archived = list(tmp_path.glob("*-session.html"))
    assert len(archived) == 1
    assert "Tacos" in archived[0].read_text()
