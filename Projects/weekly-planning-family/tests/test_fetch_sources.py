import json
import subprocess
from datetime import date
from unittest.mock import patch

from src.config import load_config
from src.fetch_sources import (
    Event,
    Message,
    Task,
    _run_skill,
    assemble_context,
    compute_week_window,
    fetch_calendar_range,
    fetch_gmail,
    fetch_todoist_deadlines,
    fetch_todoist_project,
)


def test_run_skill_parses_json_stdout():
    fake_result = subprocess.CompletedProcess(
        args=["x"], returncode=0,
        stdout=json.dumps([{"a": 1}, {"a": 2}]),
        stderr="",
    )
    with patch("subprocess.run", return_value=fake_result) as mock_run:
        result = _run_skill("/fake/path", ["--arg", "v"])
    assert result == [{"a": 1}, {"a": 2}]
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert called_args == ["/fake/path", "--arg", "v"]


def test_week_window_from_thursday():
    # Thursday May 21 2026 → window should start Fri May 22
    today = date(2026, 5, 21)
    start, end, horizon = compute_week_window(today)
    assert start == date(2026, 5, 22)
    assert end == date(2026, 5, 28)
    assert horizon == date(2026, 6, 18)


def test_week_window_from_friday():
    # Friday counts as the start day itself
    today = date(2026, 5, 22)
    start, end, horizon = compute_week_window(today)
    assert start == date(2026, 5, 22)
    assert end == date(2026, 5, 28)


def test_week_window_from_saturday():
    # Saturday May 23 → next Friday is May 29
    today = date(2026, 5, 23)
    start, end, _ = compute_week_window(today)
    assert start == date(2026, 5, 29)
    assert end == date(2026, 6, 4)


def test_fetch_calendar_range_calls_skill_per_day_and_tags_source():
    # 3-day range = 3 skill calls
    fake_responses = [
        [{"title": "Day1 evt", "start": "9:00 AM", "end": "10:00 AM"}],
        [],  # day 2 empty
        [{"title": "Day3 evt", "start": "all-day", "end": "all-day", "location": "Home"}],
    ]
    with patch("src.fetch_sources._run_skill", side_effect=fake_responses) as mock:
        events = fetch_calendar_range(
            calendar_id="cal@x",
            start=date(2026, 5, 22),
            end=date(2026, 5, 24),
            source_tag="general",
            exclude_recurring=False,
        )
    assert mock.call_count == 3
    assert len(events) == 2
    assert events[0].title == "Day1 evt"
    assert events[0].date == "2026-05-22"
    assert events[0].source == "general"
    assert events[1].title == "Day3 evt"
    assert events[1].location == "Home"


def test_fetch_calendar_range_passes_exclude_recurring_flag():
    with patch("src.fetch_sources._run_skill", return_value=[]) as mock:
        fetch_calendar_range(
            calendar_id="cal@x",
            start=date(2026, 5, 22),
            end=date(2026, 5, 22),
            source_tag="general",
            exclude_recurring=True,
        )
    # one call (one-day range), with the flag in args
    called_args = mock.call_args[0][1]
    assert "--exclude-recurring" in called_args


def test_fetch_gmail_basic(load_fixture):
    fixture = load_fixture("gmail_dalton.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture) as mock:
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="newer_than:7d -category:promotions",
            max_results=50,
            label_id=None,
        )
    assert len(msgs) == 2
    assert hit_cap is False
    assert msgs[0].id == "abc1"
    assert msgs[0].subject == "Appt reminder"
    assert msgs[0].account == "dalton"
    called_args = mock.call_args[0][1]
    assert "--account" in called_args
    assert "dalton" in called_args
    assert "--query" in called_args
    assert "--max-results" in called_args
    assert "50" in called_args


def test_fetch_gmail_hits_volume_cap(load_fixture):
    # fixture has 60 items but we ask for 50; skill returns all 60 (it doesn't truncate),
    # so the helper takes 50 and flags cap-hit
    fixture = load_fixture("gmail_volume_cap.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture):
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="x",
            max_results=50,
            label_id=None,
        )
    assert len(msgs) == 50
    assert hit_cap is True


def test_fetch_gmail_with_label_id_uses_label_query(load_fixture):
    fixture = load_fixture("gmail_kid_school.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture) as mock:
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="newer_than:7d",
            max_results=50,
            label_id="Label_1234567890123456789",
        )
    assert len(msgs) == 2
    assert msgs[0].account == "kid_school"  # tagged by helper since label_id was set
    called_args = mock.call_args[0][1]
    # Confirm the label was included by chaining onto the query
    # (we use Gmail's label: search syntax; the label ID must appear in the --query arg)
    query_idx = called_args.index("--query") + 1
    full_query = called_args[query_idx]
    assert "label:Label_1234567890123456789" in full_query or "Label_1234567890123456789" in full_query


def test_fetch_todoist_project_returns_tasks(load_fixture):
    fixture = load_fixture("todoist_meals.json")
    # The helper calls Todoist API; we patch the low-level HTTP call
    with patch("src.fetch_sources._todoist_get", return_value=fixture):
        tasks = fetch_todoist_project(project_id="1115")
    assert len(tasks) == 3
    assert tasks[0].id == "m1"
    assert tasks[0].content == "Sheet pan chicken thighs"
    assert "thighs" in tasks[0].description


def test_fetch_todoist_deadlines_within_window(load_fixture):
    fixture = load_fixture("todoist_deadlines.json")
    with patch("src.fetch_sources._todoist_get", return_value=fixture):
        tasks = fetch_todoist_deadlines(window_days=14, today=date(2026, 5, 17))
    # Both deadlines are within 14 days of 2026-05-17 (May 25 and May 30)
    assert len(tasks) == 2
    assert all(t.deadline for t in tasks)


def test_fetch_todoist_deadlines_excludes_far_future():
    fixture = [
        {"id": "x", "content": "Far future", "deadline": "2027-01-01", "project_id": "1113"},
        {"id": "y", "content": "Soon", "deadline": "2026-05-20", "project_id": "1113"},
    ]
    with patch("src.fetch_sources._todoist_get", return_value=fixture):
        tasks = fetch_todoist_deadlines(window_days=14, today=date(2026, 5, 17))
    assert len(tasks) == 1
    assert tasks[0].id == "y"


def test_assemble_context_uses_config_and_populates_fields(fixtures_dir, load_fixture):
    cfg = load_config(fixtures_dir / "config_valid.yaml")

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

    skill_responses = {
        "gcal-general": gcal_general,
        "gcal-meals": gcal_meals,
        "gcal-school": gcal_school,
        "gcal-personal": [],
        "gmail-dalton": gmail_d,
        "gmail-maggie": gmail_m,
        "gmail-kid_school": gmail_ks,
    }

    def fake_run_skill(path, args):
        path = str(path)
        if "list-events.sh" in path:
            cal_id = args[args.index("--calendar-id") + 1]
            if cal_id == cfg.calendars.shared_general:
                return skill_responses["gcal-general"]
            elif cal_id == cfg.calendars.shared_meals:
                return skill_responses["gcal-meals"]
            elif cal_id == cfg.calendars.dalton_personal:
                return skill_responses["gcal-personal"]
            else:
                return skill_responses["gcal-school"]
        if "search-emails.sh" in path:
            account = args[args.index("--account") + 1]
            query = args[args.index("--query") + 1]
            if "label:" in query or cfg.gmail.kid_school_label_id in query:
                return skill_responses["gmail-kid_school"]
            return skill_responses[f"gmail-{account}"]
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
        # No params = full /tasks call = deadline lookup
        return todoist_deadlines

    with patch("src.fetch_sources._run_skill", side_effect=fake_run_skill), \
         patch("src.fetch_sources._todoist_get", side_effect=fake_todoist_get):
        ctx = assemble_context(cfg, today=date(2026, 5, 21))  # Thursday

    assert ctx.week_start == date(2026, 5, 22)
    assert ctx.week_end == date(2026, 5, 28)
    assert len(ctx.general_events) > 0
    assert len(ctx.meal_events_last) > 0
    assert len(ctx.school_events) > 0
    assert len(ctx.dalton_gmail) == 2
    assert len(ctx.maggie_gmail) == 1
    assert len(ctx.kid_school_emails) == 2
    assert len(ctx.meals_library) == 3
    assert len(ctx.date_night_ideas) == 3
    assert len(ctx.screen_time_ideas) == 3
    assert len(ctx.upcoming_deadlines) == 2
    assert ctx.inbox_volume_flag is False


def test_event_source_class_collapses_disambiguators():
    assert Event(title="x", date="2026-05-22", start="", end="", source="general").source_class == "general"
    assert Event(title="x", date="2026-05-22", start="", end="", source="general-horizon").source_class == "general"
    assert Event(title="x", date="2026-05-22", start="", end="", source="school:Elementary").source_class == "school"
    assert Event(title="x", date="2026-05-22", start="", end="", source="meals").source_class == "meals"


def test_context_round_trip_preserves_all_fields():
    from src.fetch_sources import Context, Message
    ctx = Context(
        week_start=date(2026, 5, 22),
        week_end=date(2026, 5, 28),
        horizon_end=date(2026, 6, 18),
        general_events=[Event(title="t", date="2026-05-22", start="9 AM", end="10 AM", source="general")],
        meal_events_last=[Event(title="m", date="2026-05-15", start="all-day", end="all-day", source="meals")],
        dalton_gmail=[Message(id="1", subject="s", sender="x@y", snippet="hi", date="d", account="dalton")],
        maggie_gmail=[Message(id="2", subject="s2", sender="a@b", snippet="ok", date="d", account="maggie")],
        kid_school_emails=[Message(id="3", subject="s3", sender="c@d", snippet="np", date="d", account="kid_school")],
        meals_library=[Task(id="t1", content="pasta")],
        inbox_volume_flag=True,
    )
    revived = Context.from_dict(ctx.to_dict())
    assert revived.week_start == ctx.week_start
    assert revived.dalton_gmail[0].subject == "s"
    assert revived.maggie_gmail[0].account == "maggie"
    assert revived.kid_school_emails[0].snippet == "np"
    assert revived.inbox_volume_flag is True


def test_context_to_dict_is_json_safe(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    with patch("src.fetch_sources._run_skill", return_value=[]), \
         patch("src.fetch_sources._todoist_get", return_value=[]):
        ctx = assemble_context(cfg, today=date(2026, 5, 21))
    d = ctx.to_dict()
    json.dumps(d)  # would raise if not serializable
    assert d["week_start"] == "2026-05-22"
    assert d["inbox_volume_flag"] is False
