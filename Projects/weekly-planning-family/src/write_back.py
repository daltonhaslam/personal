"""Parse the form payload, validate, write to Calendar + Todoist, return summary HTML."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import Config
from src.constants import GCAL_WRITE, SESSIONS_DIR, TODOIST_ADD
from src.render_summary import render_summary


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class CalendarWriteResult:
    created: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class TodoistWriteResult:
    created: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    detail: str = ""


def _run_skill(skill_path: str | Path, args: list[str]) -> dict:
    """Run a write skill, return parsed JSON. Tests monkeypatch this."""
    result = subprocess.run(
        [str(skill_path)] + args,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


# -------- form parsing --------

_DINNER_RE = re.compile(r"^dinner_(\d{4}-\d{2}-\d{2})$")
_WFH_RE = re.compile(r"^wfh_(\d{4}-\d{2}-\d{2})$")
_HOME_BY_RE = re.compile(r"^home_by_(\d{4}-\d{2}-\d{2})$")
_ART_DATE_RE = re.compile(r"^art_date_(\d+)$")
_KID_TITLE_RE = re.compile(r"^kid_activity_title_(\d+)$")


def _split_lines(s: str) -> list[str]:
    return [line.strip() for line in (s or "").splitlines() if line.strip()]


def parse_form(form: dict) -> dict:
    """Translate the raw form dict into a structured decisions dict."""
    dinners: list[dict] = []
    for key, value in form.items():
        m = _DINNER_RE.match(key)
        if not m:
            continue
        dinners.append({"day": m.group(1), "meal": (value or "").strip()})
    dinners.sort(key=lambda d: d["day"])

    shopping_necessary = _split_lines(form.get("shopping_necessary", ""))
    shopping_wants = _split_lines(form.get("shopping_wants", ""))

    home_schedule: list[dict] = []
    wfh_days: dict[str, bool] = {}
    home_by_days: dict[str, str] = {}
    for key, value in form.items():
        m = _WFH_RE.match(key)
        if m:
            wfh_days[m.group(1)] = bool(value)
            continue
        m = _HOME_BY_RE.match(key)
        if m:
            home_by_days[m.group(1)] = (value or "").strip()
    all_days = sorted(set(list(wfh_days.keys()) + list(home_by_days.keys())))
    for d in all_days:
        home_schedule.append({
            "day": d,
            "wfh": wfh_days.get(d, False),
            "home_by": home_by_days.get(d, ""),
        })

    art_blocks: list[dict] = []
    for key, value in form.items():
        m = _ART_DATE_RE.match(key)
        if not m:
            continue
        idx = m.group(1)
        date_v = (value or "").strip()
        start_v = (form.get(f"art_start_{idx}") or "").strip()
        end_v = (form.get(f"art_end_{idx}") or "").strip()
        if not date_v and not start_v and not end_v:
            continue
        art_blocks.append({"date": date_v, "start": start_v, "end": end_v})

    babysitter = None
    if form.get("babysitter_needed"):
        babysitter = {
            "date": (form.get("babysitter_date") or "").strip(),
            "time": (form.get("babysitter_time") or "").strip(),
            "who": (form.get("babysitter_who") or "").strip(),
        }

    kids_activities: list[dict] = []
    for key, value in form.items():
        m = _KID_TITLE_RE.match(key)
        if not m:
            continue
        idx = m.group(1)
        title = (value or "").strip()
        if not title:
            continue
        kids_activities.append({
            "title": title,
            "date": (form.get(f"kid_activity_date_{idx}") or "").strip(),
            "time": (form.get(f"kid_activity_time_{idx}") or "").strip(),
            "owner": (form.get(f"kid_activity_owner_{idx}") or "Both").strip(),
        })

    date_night = None
    if (form.get("date_night_choice") or "").strip():
        date_night = {
            "date": (form.get("date_night_date") or "").strip(),
            "time": (form.get("date_night_time") or "").strip(),
            "choice": (form.get("date_night_choice") or "").strip(),
        }

    return {
        "retrospective_note": (form.get("retrospective_note") or "").strip(),
        "dinners": dinners,
        "new_meal": (form.get("new_meal") or "").strip(),
        "shopping_necessary": shopping_necessary,
        "shopping_wants": shopping_wants,
        "home_schedule": home_schedule,
        "art_blocks": art_blocks,
        "babysitter": babysitter,
        "kids_activities": kids_activities,
        "church_lines": _split_lines(form.get("church_notes", "")),
        "home_lines": _split_lines(form.get("home_notes", "")),
        "new_deadlines": _split_lines(form.get("new_deadlines", "")),
        "finances_notes": (form.get("finances_notes") or "").strip(),
        "cfm_notes": (form.get("cfm_notes") or "").strip(),
        "date_night": date_night,
    }


# -------- validation --------

def validate(decisions: dict) -> list[ValidationError]:
    """Return list of ValidationError. Empty = OK."""
    errors: list[ValidationError] = []

    bs = decisions.get("babysitter")
    if bs is not None:
        if not bs.get("date"):
            errors.append(ValidationError("babysitter_date", "Babysitter date is required when babysitter is needed"))
        if not bs.get("time"):
            errors.append(ValidationError("babysitter_time", "Babysitter time is required when babysitter is needed"))
        if not bs.get("who"):
            errors.append(ValidationError("babysitter_who", "Babysitter contact name is required"))

    for i, b in enumerate(decisions.get("art_blocks", [])):
        if not b.get("date"):
            errors.append(ValidationError(f"art_date_{i}", "Art block date is required"))
        if not b.get("start"):
            errors.append(ValidationError(f"art_start_{i}", "Art block start time is required"))
        if not b.get("end"):
            errors.append(ValidationError(f"art_end_{i}", "Art block end time is required"))

    for i, k in enumerate(decisions.get("kids_activities", [])):
        if not k.get("date"):
            errors.append(ValidationError(f"kid_activity_date_{i}", "Kid activity date is required"))

    dn = decisions.get("date_night")
    if dn is not None:
        if not dn.get("date"):
            errors.append(ValidationError("date_night_date", "Date night date is required when date night is set"))

    return errors


# -------- calendar writes --------

def _add_minutes(time_hhmm: str, minutes: int) -> str:
    """'17:00' + 15 → '17:15'."""
    h, m = [int(x) for x in time_hhmm.split(":")]
    total = h * 60 + m + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _try_create(args: list[str], result: CalendarWriteResult, error_label: str) -> None:
    """Run gcal-write/add-event.sh with args; record success/failure on result."""
    try:
        _run_skill(GCAL_WRITE, args)
        result.created += 1
    except subprocess.CalledProcessError as e:
        result.failed += 1
        result.errors.append(f"{error_label}: {e.stderr or e.output or 'failed'}")


def write_calendar(decisions: dict, cfg: Config) -> CalendarWriteResult:
    """Create calendar events for all calendar-bound decisions. Returns a result summary."""
    result = CalendarWriteResult()

    for d in decisions.get("dinners", []):
        if not d.get("meal"):
            continue
        _try_create(
            ["--calendar-id", cfg.calendars.shared_meals,
             "--title", d["meal"],
             "--all-day", "--date", d["day"]],
            result, f"{d['day']} {d['meal']}",
        )

    for h in decisions.get("home_schedule", []):
        day = h["day"]
        if h["wfh"]:
            _try_create(
                ["--calendar-id", cfg.calendars.shared_general,
                 "--title", "Dalton WFH",
                 "--all-day", "--date", day],
                result, f"WFH {day}",
            )
        elif h["home_by"]:
            _try_create(
                ["--calendar-id", cfg.calendars.shared_general,
                 "--title", "Dalton home",
                 "--start", f"{day}T{h['home_by']}",
                 "--end", f"{day}T{_add_minutes(h['home_by'], 15)}"],
                result, f"Home-by {day}",
            )

    for b in decisions.get("art_blocks", []):
        if not (b.get("date") and b.get("start") and b.get("end")):
            continue
        _try_create(
            ["--calendar-id", cfg.calendars.shared_general,
             "--title", "Maggie art",
             "--start", f"{b['date']}T{b['start']}",
             "--end", f"{b['date']}T{b['end']}"],
            result, f"Art {b['date']}",
        )

    bs = decisions.get("babysitter")
    if bs and bs.get("date") and bs.get("time"):
        end_time = _add_minutes(bs["time"], 240)
        _try_create(
            ["--calendar-id", cfg.calendars.shared_general,
             "--title", f"Babysitter — {bs['who']}",
             "--start", f"{bs['date']}T{bs['time']}",
             "--end", f"{bs['date']}T{end_time}"],
            result, "Babysitter",
        )

    for k in decisions.get("kids_activities", []):
        if not (k.get("title") and k.get("date")):
            continue
        if k.get("time"):
            end_time = _add_minutes(k["time"], 60)
            args = ["--calendar-id", cfg.calendars.shared_general,
                    "--title", k["title"],
                    "--start", f"{k['date']}T{k['time']}",
                    "--end", f"{k['date']}T{end_time}",
                    "--description", f"Owner: {k.get('owner', 'Both')}"]
        else:
            args = ["--calendar-id", cfg.calendars.shared_general,
                    "--title", k["title"],
                    "--all-day", "--date", k["date"],
                    "--description", f"Owner: {k.get('owner', 'Both')}"]
        _try_create(args, result, f"Kid activity '{k['title']}'")

    dn = decisions.get("date_night")
    if dn and dn.get("date") and dn.get("choice"):
        if dn.get("time"):
            end_time = _add_minutes(dn["time"], 180)
            args = ["--calendar-id", cfg.calendars.shared_general,
                    "--title", f"Date night — {dn['choice']}",
                    "--start", f"{dn['date']}T{dn['time']}",
                    "--end", f"{dn['date']}T{end_time}"]
        else:
            args = ["--calendar-id", cfg.calendars.shared_general,
                    "--title", f"Date night — {dn['choice']}",
                    "--all-day", "--date", dn["date"]]
        _try_create(args, result, "Date night")

    if result.failed == 0:
        result.detail = f"Created {result.created} events"
    else:
        result.detail = f"Created {result.created} events, {result.failed} failed"
    return result


# -------- todoist writes --------

def _try_create_todoist(
    content: str,
    project_id: str,
    role_label: str,
    result: TodoistWriteResult,
    *,
    due_string: str = "",
    priority: str = "",
) -> None:
    args = [
        "--content", content,
        "--project-id", project_id,
        "--due-string", due_string,
        "--priority", priority,
    ]
    try:
        _run_skill(TODOIST_ADD, args)
        result.created += 1
    except subprocess.CalledProcessError as e:
        result.failed += 1
        result.errors.append(f"'{content}' → {role_label}: {e.stderr or 'failed'}")


def write_todoist(decisions: dict, cfg: Config) -> TodoistWriteResult:
    """Create Todoist tasks for all task-bound decisions.

    Tasks default to no due date and no priority (the user sets these manually
    in Todoist). Exception: items entered under 'Major deadlines' carry the
    same defaults add-task.sh ships with (due today, priority p2) since by
    name they're expected to be timely.
    """
    result = TodoistWriteResult()
    # (items, role, due_string, priority)
    routes = [
        (decisions.get("shopping_necessary", []), "shopping",      "",      ""),
        (decisions.get("shopping_wants", []),     "shopping_wants", "",      ""),
        (decisions.get("home_lines", []),         "home",           "",      ""),
        (decisions.get("new_deadlines", []),      "general_todos",  "today", "3"),
        (decisions.get("church_lines", []),       "general_todos",  "",      ""),
    ]
    for items, role, due, prio in routes:
        try:
            project_id = cfg.todoist.project_id(role)
        except Exception as e:
            result.failed += len(items)
            result.errors.append(f"Project '{role}' not configured: {e}")
            continue
        for content in items:
            _try_create_todoist(content, project_id, role, result, due_string=due, priority=prio)

    new_meal = (decisions.get("new_meal") or "").strip()
    if new_meal:
        try:
            project_id = cfg.todoist.project_id("meals")
            _try_create_todoist(new_meal, project_id, "meals", result)
        except Exception as e:
            result.failed += 1
            result.errors.append(f"new meal '{new_meal}': {e}")

    if result.failed == 0:
        result.detail = f"Created {result.created} tasks"
    else:
        result.detail = f"Created {result.created} tasks, {result.failed} failed"
    return result


# -------- archive + save orchestrator --------

def _archive_session(summary_html: str, week_start_iso: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{week_start_iso}-session.html"
    path.write_text(summary_html)
    return path


def run_save(form: dict, cfg: Config) -> dict:
    """Top-level save orchestrator. Returns {status, summary_html|errors, results}."""
    decisions = parse_form(form)
    errors = validate(decisions)
    if errors:
        return {
            "status": "validation_error",
            "errors": [{"field": e.field, "message": e.message} for e in errors],
        }

    cal_result = write_calendar(decisions, cfg)
    todoist_result = write_todoist(decisions, cfg)

    succeeded = []
    failed = []
    if cal_result.created > 0:
        succeeded.append({"label": "Calendar events", "detail": cal_result.detail, "key": "calendar"})
    if cal_result.failed > 0:
        failed.append({"label": "Calendar events", "error": "; ".join(cal_result.errors), "key": "calendar"})
    if todoist_result.created > 0:
        succeeded.append({"label": "Todoist tasks", "detail": todoist_result.detail, "key": "todoist"})
    if todoist_result.failed > 0:
        failed.append({"label": "Todoist tasks", "error": "; ".join(todoist_result.errors), "key": "todoist"})

    week_start_iso = ""
    for d in decisions.get("dinners", []):
        if d.get("day"):
            week_start_iso = d["day"]
            break
    if not week_start_iso:
        week_start_iso = datetime.now().date().isoformat()

    week_start_display = datetime.fromisoformat(week_start_iso).strftime("%b %-d")
    saved_at = datetime.now().strftime("%a %b %-d %-I:%M %p")

    summary_html = render_summary(
        decisions=decisions,
        results={"succeeded": succeeded, "failed": failed},
        week_start_display=week_start_display,
        saved_at=saved_at,
    )

    _archive_session(summary_html, week_start_iso)

    return {
        "status": "ok",
        "summary_html": summary_html,
        "results": {"succeeded": succeeded, "failed": failed},
    }
