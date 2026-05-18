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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.config import Config, load_config
from src.constants import CONFIG_PATH, GCAL_FETCH, GMAIL_SEARCH, PROJECT_ROOT


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


_TODOIST_TOKEN_CACHE: str | None = None


def _todoist_token() -> str:
    """Read Todoist API token from macOS Keychain. Tests should monkeypatch this.

    The token is cached for the lifetime of the process — assemble_context
    issues several Todoist GETs and each was otherwise re-spawning `security`.
    """
    global _TODOIST_TOKEN_CACHE
    if _TODOIST_TOKEN_CACHE is None:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "TODOIST_API_TOKEN", "-w"],
            capture_output=True, text=True, check=True,
        )
        _TODOIST_TOKEN_CACHE = result.stdout.strip()
    return _TODOIST_TOKEN_CACHE


def _extract_deadline_str(raw: Any) -> str:
    """Normalize Todoist's deadline field to a YYYY-MM-DD string (or '')."""
    if isinstance(raw, dict):
        return raw.get("date", "")
    if isinstance(raw, str):
        return raw
    return ""


def _todoist_get(path: str, params: dict | None = None) -> Any:
    """GET against Todoist API v1. Returns parsed JSON.

    Auto-paginates endpoints that return ``{"results": [...], "next_cursor": str}``
    (Todoist's default page size is 50; without pagination this would silently
    truncate any project with >50 active tasks). For non-paginated endpoints,
    returns the response as-is.

    Tests should monkeypatch this directly to return canned fixtures.
    """
    token = _todoist_token()
    base = f"https://api.todoist.com/api/v1{path}"
    accumulated: list = []
    cursor: str | None = None
    while True:
        q = dict(params or {})
        if cursor:
            q["cursor"] = cursor
        url = base + (("?" + urllib.parse.urlencode(q)) if q else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        if isinstance(data, dict) and "results" in data:
            accumulated.extend(data["results"])
            cursor = data.get("next_cursor")
            if not cursor:
                return accumulated
            continue
        return data


def fetch_todoist_project(*, project_id: str) -> list[Task]:
    """List all active tasks in a Todoist project."""
    raw = _todoist_get("/tasks", {"project_id": project_id})
    return [
        Task(
            id=t["id"],
            content=t.get("content", ""),
            description=t.get("description", ""),
            deadline=_extract_deadline_str(t.get("deadline")),
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
        dl_str = _extract_deadline_str(t.get("deadline"))
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


def assemble_context(cfg: Config, *, today: date | None = None) -> Context:
    """Pull every source defined in config and return a populated Context.

    All fetchers are independent and run in parallel via a thread pool. Each
    fetcher is itself either a bash subprocess (Calendar/Gmail) or an HTTPS
    GET (Todoist), so the GIL is irrelevant — wall-clock time collapses to
    the slowest single fetcher rather than the sum.
    """
    week_start, week_end, horizon_end = compute_week_window(today)

    with ThreadPoolExecutor(max_workers=12) as ex:
        fut_general = ex.submit(
            fetch_calendar_range,
            calendar_id=cfg.calendars.shared_general,
            start=week_start, end=week_end,
            source_tag="general",
            exclude_recurring=True,
        )
        fut_horizon = ex.submit(
            fetch_calendar_range,
            calendar_id=cfg.calendars.shared_general,
            start=week_end + timedelta(days=1), end=horizon_end,
            source_tag="general-horizon",
            exclude_recurring=True,
        )
        fut_meals_last = ex.submit(
            fetch_calendar_range,
            calendar_id=cfg.calendars.shared_meals,
            start=week_start - timedelta(days=7),
            end=week_start - timedelta(days=1),
            source_tag="meals",
        )
        fut_personal = ex.submit(
            fetch_calendar_range,
            calendar_id=cfg.calendars.dalton_personal,
            start=week_start, end=week_end,
            source_tag="personal",
            exclude_recurring=True,
        )
        fut_schools = [
            ex.submit(
                fetch_calendar_range,
                calendar_id=sc.id,
                start=week_start, end=week_end,
                source_tag=f"school:{sc.name}",
            )
            for sc in cfg.calendars.schools
        ]
        fut_dalton = ex.submit(
            fetch_gmail,
            account="dalton",
            query=cfg.gmail.default_query,
            max_results=cfg.gmail.max_results_per_account,
        )
        fut_maggie = ex.submit(
            fetch_gmail,
            account="maggie",
            query=cfg.gmail.default_query,
            max_results=cfg.gmail.max_results_per_account,
        )
        fut_kid_school = ex.submit(
            fetch_gmail,
            account="dalton",
            query="newer_than:7d",
            max_results=cfg.gmail.max_results_per_account,
            label_id=cfg.gmail.kid_school_label_id,
        )
        fut_meals_lib = ex.submit(
            fetch_todoist_project,
            project_id=cfg.todoist.project_id("meals"),
        )
        fut_date_night = ex.submit(
            fetch_todoist_project,
            project_id=cfg.todoist.project_id("date_night_ideas"),
        )
        fut_screen_time = ex.submit(
            fetch_todoist_project,
            project_id=cfg.todoist.project_id("screen_time"),
        )
        fut_deadlines = ex.submit(
            fetch_todoist_deadlines,
            window_days=14, today=today,
        )

    general = fut_general.result()
    horizon = fut_horizon.result()
    meals_last = fut_meals_last.result()
    personal = fut_personal.result()
    school: list[Event] = [e for fut in fut_schools for e in fut.result()]
    dalton_msgs, dalton_cap = fut_dalton.result()
    maggie_msgs, maggie_cap = fut_maggie.result()
    kid_school_msgs, kid_cap = fut_kid_school.result()
    meals_lib = fut_meals_lib.result()
    date_night = fut_date_night.result()
    screen_time = fut_screen_time.result()
    deadlines = fut_deadlines.result()

    return Context(
        week_start=week_start,
        week_end=week_end,
        horizon_end=horizon_end,
        general_events=general + horizon,
        meal_events_last=meals_last,
        personal_events=personal,
        school_events=school,
        dalton_gmail=dalton_msgs,
        maggie_gmail=maggie_msgs,
        kid_school_emails=kid_school_msgs,
        meals_library=meals_lib,
        date_night_ideas=date_night,
        screen_time_ideas=screen_time,
        upcoming_deadlines=deadlines,
        inbox_volume_flag=any([dalton_cap, maggie_cap, kid_cap]),
    )


def main() -> None:
    """CLI entry: assemble context, write to context.json at project root."""
    cfg = load_config(CONFIG_PATH)
    ctx = assemble_context(cfg)
    out = PROJECT_ROOT / "context.json"
    with open(out, "w") as f:
        json.dump(ctx.to_dict(), f, indent=2)
    print(f"context.json written: {out}")
    print(f"  general events: {len(ctx.general_events)}")
    print(f"  meal events (last 7d): {len(ctx.meal_events_last)}")
    print(f"  school events: {len(ctx.school_events)}")
    print(f"  dalton gmail: {len(ctx.dalton_gmail)}")
    print(f"  maggie gmail: {len(ctx.maggie_gmail)}")
    print(f"  kid_school emails: {len(ctx.kid_school_emails)}")
    print(f"  meals library: {len(ctx.meals_library)}")
    print(f"  date night ideas: {len(ctx.date_night_ideas)}")
    print(f"  screen time ideas: {len(ctx.screen_time_ideas)}")
    print(f"  upcoming deadlines: {len(ctx.upcoming_deadlines)}")
    if ctx.inbox_volume_flag:
        print("  [!] inbox volume cap hit on at least one Gmail account")


if __name__ == "__main__":
    main()
