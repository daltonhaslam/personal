"""Load and validate config.yaml. Single source of truth for runtime settings."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


class ConfigError(ValueError):
    """Raised when config is missing required fields or has invalid types."""


@dataclass(frozen=True)
class SessionConfig:
    default_day: str
    default_time: str
    browser: str
    server_port: int
    server_abandon_timeout_hours: int


@dataclass(frozen=True)
class SchoolCalendar:
    id: str
    name: str


@dataclass(frozen=True)
class CalendarsConfig:
    shared_general: str
    shared_meals: str
    dalton_personal: str
    schools: list[SchoolCalendar]


@dataclass(frozen=True)
class GmailAccount:
    name: str
    address: str


@dataclass(frozen=True)
class GmailConfig:
    accounts: list[GmailAccount]
    kid_school_label_id: str
    default_query: str
    max_results_per_account: int

    def account_by_name(self, name: str) -> GmailAccount:
        for a in self.accounts:
            if a.name == name:
                return a
        raise ConfigError(f"No Gmail account named '{name}' in config")


@dataclass(frozen=True)
class TodoistProject:
    name: str
    id: str


@dataclass(frozen=True)
class TodoistConfig:
    projects: dict[str, TodoistProject]  # keyed by role (shopping, meals, etc.)
    collaborator_ids: dict[str, str]     # keyed by owner name (dalton, maggie)

    def project_id(self, role: str) -> str:
        if role not in self.projects:
            raise ConfigError(f"No Todoist project role '{role}' in config")
        return self.projects[role].id


@dataclass(frozen=True)
class Kid:
    name: str
    age: int


@dataclass(frozen=True)
class FamilyConfig:
    owners: list[str]
    kids: list[Kid]


@dataclass(frozen=True)
class Config:
    session: SessionConfig
    calendars: CalendarsConfig
    gmail: GmailConfig
    todoist: TodoistConfig
    family: FamilyConfig


def _require(d: dict, key: str, path: str) -> any:
    if key not in d:
        raise ConfigError(f"Missing required field: {path}.{key}")
    return d[key]


def load_config(path: Path) -> Config:
    """Load and validate config.yaml. Raises ConfigError on schema problems."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config root must be a mapping, got {type(raw).__name__}")

    s = _require(raw, "session", "")
    session = SessionConfig(
        default_day=_require(s, "default_day", "session"),
        default_time=_require(s, "default_time", "session"),
        browser=_require(s, "browser", "session"),
        server_port=int(_require(s, "server_port", "session")),
        server_abandon_timeout_hours=int(_require(s, "server_abandon_timeout_hours", "session")),
    )

    c = _require(raw, "calendars", "")
    calendars = CalendarsConfig(
        shared_general=_require(c, "shared_general", "calendars"),
        shared_meals=_require(c, "shared_meals", "calendars"),
        dalton_personal=_require(c, "dalton_personal", "calendars"),
        schools=[
            SchoolCalendar(id=_require(sc, "id", "calendars.schools[]"),
                           name=_require(sc, "name", "calendars.schools[]"))
            for sc in c.get("schools", [])
        ],
    )

    g = _require(raw, "gmail", "")
    gmail = GmailConfig(
        accounts=[
            GmailAccount(name=_require(a, "name", "gmail.accounts[]"),
                         address=_require(a, "address", "gmail.accounts[]"))
            for a in _require(g, "accounts", "gmail")
        ],
        kid_school_label_id=_require(g, "kid_school_label_id", "gmail"),
        default_query=_require(g, "default_query", "gmail"),
        max_results_per_account=int(_require(g, "max_results_per_account", "gmail")),
    )

    t = _require(raw, "todoist", "")
    projects_raw = _require(t, "projects", "todoist")
    projects = {
        role: TodoistProject(
            name=_require(v, "name", f"todoist.projects.{role}"),
            id=str(_require(v, "id", f"todoist.projects.{role}")),
        )
        for role, v in projects_raw.items()
    }
    todoist = TodoistConfig(
        projects=projects,
        collaborator_ids={k: str(v) for k, v in _require(t, "collaborator_ids", "todoist").items()},
    )

    f_raw = _require(raw, "family", "")
    family = FamilyConfig(
        owners=list(_require(f_raw, "owners", "family")),
        kids=[
            Kid(name=_require(k, "name", "family.kids[]"), age=int(_require(k, "age", "family.kids[]")))
            for k in f_raw.get("kids", [])
        ],
    )

    return Config(session=session, calendars=calendars, gmail=gmail, todoist=todoist, family=family)
