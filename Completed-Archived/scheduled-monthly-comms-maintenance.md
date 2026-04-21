# monthly-comms-maintenance

**Schedule:** 1st of each month at 7:00 PM
**Skill file:** [Personal/Projects/monthly-comms-maintenance/SKILL.md](../Projects/monthly-comms-maintenance/SKILL.md)
**Status:** Active

## What It Does
Audits the Gmail Communication OS setup: checks that known newsletter senders have the "Newsletters" label (30-day window), flags inactive newsletters (no emails in 45 days), and hunts for new newsletter candidates. Writes results to `Projects/monthly-comms-maintenance/maintenance.html`. Apple Shortcut at 7:15 PM creates an Apple Note titled "Comm OS Maintenance".

## To Modify
- Task logic → edit `Projects/monthly-comms-maintenance/SKILL.md`
- Schedule → update RemoteTrigger via `/schedule` skill in Claude Code
