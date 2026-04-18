# Scheduled Tasks — Index

Active scheduled tasks for the Personal domain. Each task runs via the Claude Code local scheduler (no Cowork required) — fires automatically when the Mac is awake.

| Task | Schedule | Skill File | Status |
|---|---|---|---|
| daily-brief | Every day at 7:00 PM | [Projects/daily-brief/SKILL.md](../Projects/daily-brief/SKILL.md) | Active — runs via LaunchAgent (`com.dalton.daily-brief`), not Claude Code scheduler |
| weekly-newsletter-podcast | Every Monday at 7:00 PM | [Projects/weekly-newsletter-podcast/SKILL.md](../Projects/weekly-newsletter-podcast/SKILL.md) | Active |
| monthly-comms-maintenance | 1st of each month at 7:00 PM | [Projects/monthly-comms-maintenance/SKILL.md](../Projects/monthly-comms-maintenance/SKILL.md) | Active |
| email-to-todoist-tasks | Every day at 7:00 PM | [Projects/email-to-todoist-tasks/SKILL.md](../Projects/email-to-todoist-tasks/SKILL.md) | Active |

## How to Modify a Task

- **Change task logic**: Edit `SKILL.md` in the corresponding `Projects/<task>/` folder
- **Change the schedule**: Use the `/schedule` skill in Claude Code to update the task
- **Add a new task**: Create a `Projects/<new-task>/SKILL.md`, run `/schedule` in Claude Code, and add an entry here

## Apple Shortcut Integration

See [shortcuts-setup.md](shortcuts-setup.md) for the full list of Apple Shortcuts that pick up output files from these tasks.
