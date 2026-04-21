# email-to-todoist-tasks

**Schedule:** Every day at 7:00 PM (runs alongside daily-brief)
**Skill file:** [Personal/Projects/email-to-todoist-tasks/SKILL.md](../Projects/email-to-todoist-tasks/SKILL.md)
**Status:** Active

## What It Does
Scans the past 24 hours of Gmail for actionable emails (replies needed, approvals, RSVPs, bills/payments, decisions). Deduplicates against existing Todoist tasks, then adds new tasks to the Personal project (ID: 6Crg6xfrxV9Pj3x8). On success, deletes `todoistfailure/todoist_failure.txt` if it exists. On failure, writes that file — an Apple Shortcut monitors for it and creates an Apple Note alert.

## To Modify
- Task logic → edit `Projects/email-to-todoist-tasks/SKILL.md`
- Schedule → update RemoteTrigger via `/schedule` skill in Claude Code
