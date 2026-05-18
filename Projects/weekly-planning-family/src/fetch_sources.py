"""Pull data from Google Calendar, Gmail, and Todoist into a Context.

All I/O goes through `_run_skill`, which subprocesses out to the existing
bash skills under Personal/skills/. Tests monkeypatch this helper instead
of `subprocess.run` directly.
"""
from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.constants import GCAL_FETCH, GMAIL_SEARCH


@dataclass
class Event:
    title: str
    date: str          # YYYY-MM-DD
    start: str         # "5:00 PM" or "all-day"
    end: str           # "5:30 PM" or "all-day"
    location: str = ""
    source: str = ""   # "general", "meals", "personal", "school"


@dataclass
class Message:
    id: str
    subject: str
    sender: str
    snippet: str
    date: str
    account: str = ""  # "dalton", "maggie", or "kid_school"


@dataclass
class Task:
    id: str
    content: str
    description: str = ""
    deadline: str = ""  # YYYY-MM-DD or ""
    project_id: str = ""


@dataclass
class Context:
    week_start: date
    week_end: date
    horizon_end: date
    general_events: list[Event] = field(default_factory=list)
    meal_events_last: list[Event] = field(default_factory=list)
    personal_events: list[Event] = field(default_factory=list)
    school_events: list[Event] = field(default_factory=list)
    dalton_gmail: list[Message] = field(default_factory=list)
    maggie_gmail: list[Message] = field(default_factory=list)
    kid_school_emails: list[Message] = field(default_factory=list)
    meals_library: list[Task] = field(default_factory=list)
    date_night_ideas: list[Task] = field(default_factory=list)
    screen_time_ideas: list[Task] = field(default_factory=list)
    upcoming_deadlines: list[Task] = field(default_factory=list)
    inbox_volume_flag: bool = False

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict for context.json."""
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "horizon_end": self.horizon_end.isoformat(),
            "general_events": [e.__dict__ for e in self.general_events],
            "meal_events_last": [e.__dict__ for e in self.meal_events_last],
            "personal_events": [e.__dict__ for e in self.personal_events],
            "school_events": [e.__dict__ for e in self.school_events],
            "dalton_gmail": [m.__dict__ for m in self.dalton_gmail],
            "maggie_gmail": [m.__dict__ for m in self.maggie_gmail],
            "kid_school_emails": [m.__dict__ for m in self.kid_school_emails],
            "meals_library": [t.__dict__ for t in self.meals_library],
            "date_night_ideas": [t.__dict__ for t in self.date_night_ideas],
            "screen_time_ideas": [t.__dict__ for t in self.screen_time_ideas],
            "upcoming_deadlines": [t.__dict__ for t in self.upcoming_deadlines],
            "inbox_volume_flag": self.inbox_volume_flag,
        }


def _run_skill(skill_path: str | Path, args: list[str]) -> Any:
    """Run a bash skill, parse stdout as JSON, return parsed value.

    Raises CalledProcessError on non-zero exit. Tests should monkeypatch this.
    """
    result = subprocess.run(
        [str(skill_path)] + args,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def compute_week_window(today: date | None = None) -> tuple[date, date, date]:
    """Return (week_start, week_end, horizon_end).

    week_start is the next Friday on/after `today` (Friday=Friday counts as start).
    week_end is week_start + 6 days (Thursday).
    horizon_end is week_end + 21 days.
    """
    if today is None:
        today = date.today()
    # Python weekday: Mon=0 ... Sun=6. Friday = 4.
    days_until_friday = (4 - today.weekday()) % 7
    week_start = today + timedelta(days=days_until_friday)
    week_end = week_start + timedelta(days=6)
    horizon_end = week_end + timedelta(days=21)
    return week_start, week_end, horizon_end


def fetch_calendar_range(
    *,
    calendar_id: str,
    start: date,
    end: date,
    source_tag: str,
    exclude_recurring: bool = False,
) -> list[Event]:
    """Fetch events from a single calendar across an inclusive date range.

    Calls the gcal-fetch skill once per day in the range, merges, tags each
    event with `source_tag`.
    """
    events: list[Event] = []
    cur = start
    while cur <= end:
        args = ["--calendar-id", calendar_id, "--date", cur.isoformat()]
        if exclude_recurring:
            args.append("--exclude-recurring")
        raw = _run_skill(GCAL_FETCH, args)
        for e in raw:
            events.append(Event(
                title=e.get("title", "(no title)"),
                date=cur.isoformat(),
                start=e.get("start", ""),
                end=e.get("end", ""),
                location=e.get("location", ""),
                source=source_tag,
            ))
        cur += timedelta(days=1)
    return events


def fetch_gmail(
    *,
    account: str,
    query: str,
    max_results: int,
    label_id: str | None = None,
) -> tuple[list[Message], bool]:
    """Fetch Gmail messages for an account.

    Returns (messages, hit_volume_cap).
    `hit_volume_cap` is True if the skill returned >= max_results items
    (likely truncation in the actual inbox).

    `label_id`, when provided, is appended to `query` as `label:<id>`.
    Returned Messages are tagged with account="kid_school" when label_id is set,
    otherwise with the account name.
    """
    full_query = query
    if label_id:
        full_query = f"{query} label:{label_id}".strip()

    args = [
        "--account", account,
        "--query", full_query,
        "--max-results", str(max_results),
    ]
    raw = _run_skill(GMAIL_SEARCH, args)

    hit_cap = len(raw) >= max_results
    items = raw[:max_results]

    tag = "kid_school" if label_id else account
    messages = [
        Message(
            id=m.get("id", ""),
            subject=m.get("subject", "(no subject)"),
            sender=m.get("from", ""),
            snippet=m.get("snippet", ""),
            date=m.get("date", ""),
            account=tag,
        )
        for m in items
    ]
    return messages, hit_cap


def _todoist_token() -> str:
    """Read Todoist API token from macOS Keychain. Tests should monkeypatch this."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "TODOIST_API_TOKEN", "-w"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _todoist_get(path: str, params: dict | None = None) -> Any:
    """GET against Todoist API v1. Returns parsed JSON (list or dict).

    Tests should monkeypatch this directly to return canned fixtures.
    """
    token = _todoist_token()
    url = f"https://api.todoist.com/api/v1{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    # API may wrap in {"results": [...]} or return a list directly
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def fetch_todoist_project(*, project_id: str) -> list[Task]:
    """List all active tasks in a Todoist project."""
    raw = _todoist_get("/tasks", {"project_id": project_id})
    return [
        Task(
            id=t["id"],
            content=t.get("content", ""),
            description=t.get("description", ""),
            deadline=(t.get("deadline") or {}).get("date", "") if isinstance(t.get("deadline"), dict) else (t.get("deadline") or ""),
            project_id=t.get("project_id", project_id),
        )
        for t in raw
    ]


def fetch_todoist_deadlines(*, window_days: int, today: date | None = None) -> list[Task]:
    """Tasks with a `deadline` falling within `window_days` of `today`.

    Pulls all tasks (no project filter), filters locally. Token-light alternative
    to the project-by-project scan.
    """
    if today is None:
        today = date.today()
    window_end = today + timedelta(days=window_days)
    raw = _todoist_get("/tasks")
    out: list[Task] = []
    for t in raw:
        dl_raw = t.get("deadline")
        dl_str = ""
        if isinstance(dl_raw, dict):
            dl_str = dl_raw.get("date", "")
        elif isinstance(dl_raw, str):
            dl_str = dl_raw
        if not dl_str:
            continue
        try:
            dl_date = date.fromisoformat(dl_str)
        except ValueError:
            continue
        if today <= dl_date <= window_end:
            out.append(Task(
                id=t["id"],
                content=t.get("content", ""),
                description=t.get("description", ""),
                deadline=dl_str,
                project_id=t.get("project_id", ""),
            ))
    return out
