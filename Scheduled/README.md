# Scheduled Tasks — Index

Active scheduled remote agents for the Personal domain. Each task runs via Claude Cowork on a set schedule.

| Task | Schedule | Skill File | Status |
|---|---|---|---|
| daily-brief | Every day at 7:00 PM | [Projects/daily-brief/SKILL.md](../Projects/daily-brief/SKILL.md) | Active |
| weekly-newsletter-podcast | Every Monday at 8:00 PM | [Projects/weekly-newsletter-podcast/SKILL.md](../Projects/weekly-newsletter-podcast/SKILL.md) | Active |
| monthly-comms-maintenance | 1st of each month at 9:00 AM | [Projects/monthly-comms-maintenance/SKILL.md](../Projects/monthly-comms-maintenance/SKILL.md) | Active |
| email-to-todoist-tasks | Every day at 7:00 PM | [Projects/email-to-todoist-tasks/SKILL.md](../Projects/email-to-todoist-tasks/SKILL.md) | Active |

## How to Modify a Task

- **Change task logic**: Edit `SKILL.md` in the corresponding `Projects/<task>/` folder
- **Change the schedule**: Update the RemoteTrigger via the `/schedule` skill in Claude Code
- **Add a new task**: Create a `Projects/<new-task>/SKILL.md`, then register it via `/schedule`, and add an entry here

## Apple Shortcut Integration

See [shortcuts-setup.md](shortcuts-setup.md) for the full list of Apple Shortcuts that pick up output files from these tasks.
