# daily-brief

**Schedule:** Every day at 7:00 PM
**Skill file:** [Personal/Projects/daily-brief/SKILL.md](../Projects/daily-brief/SKILL.md)
**Status:** Active

## What It Does
Pulls tomorrow's calendar, overdue/upcoming Todoist tasks, and today's Gmail. Writes a formatted HTML brief to `Projects/daily-brief/brief.html`. Apple Shortcut picks it up at 7:15 PM and creates an Apple Note titled "Daily Brief".

## To Modify
- Task logic → edit `Projects/daily-brief/SKILL.md`
- Schedule → update RemoteTrigger via `/schedule` skill in Claude Code
