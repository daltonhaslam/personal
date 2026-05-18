"""Shared constants. Imported by every module that needs paths or format strings."""
from pathlib import Path

PROJECT_ROOT = Path("/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family")
SKILLS_ROOT = Path("/Users/daltonhaslam/Documents/Claude/Personal/skills")

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
SESSIONS_DIR = PROJECT_ROOT / "sessions"

GCAL_FETCH = SKILLS_ROOT / "gcal-fetch" / "list-events.sh"
GCAL_WRITE = SKILLS_ROOT / "gcal-write" / "add-event.sh"
GMAIL_SEARCH = SKILLS_ROOT / "gmail-fetch" / "search-emails.sh"
GMAIL_READ = SKILLS_ROOT / "gmail-fetch" / "read-email.sh"
TODOIST_ADD = SKILLS_ROOT / "todoist-write" / "add-task.sh"
TODOIST_FIND = SKILLS_ROOT / "todoist-write" / "find-tasks.sh"

# Date formats
DATE_ISO = "%Y-%m-%d"
DATE_DISPLAY = "%a %b %-d"  # "Fri May 22"
TIME_DISPLAY = "%-I:%M %p"  # "5:00 PM"

# Owner enum values (used in form + summary)
OWNER_DALTON = "Dalton"
OWNER_MAGGIE = "Maggie"
OWNER_BOTH = "Both"
OWNERS = [OWNER_DALTON, OWNER_MAGGIE, OWNER_BOTH]
