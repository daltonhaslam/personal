# Personal — Dalton Haslam

**Public repository** | Owner: Dalton Haslam

Personal workspace covering family, church, home, health, and personal projects.

See `CLAUDE.md` for AI context and `personal_detail.md` for family/church detail.

---

## Scheduled Tasks

All tasks run via macOS LaunchAgents using the osascript executor pattern. No Apple Shortcuts or remote triggers required — fires automatically when the Mac is awake.

| Task | Schedule | Skill File | LaunchAgent |
|---|---|---|---|
| daily-brief | Every day at 7:00 PM | [Projects/daily-brief/SKILL.md](Projects/daily-brief/SKILL.md) | `com.dalton.dailybrief` |
| email-to-todoist-tasks | Every day at 7:00 PM | [Projects/email-to-todoist-tasks/SKILL.md](Projects/email-to-todoist-tasks/SKILL.md) | `com.dalton.emailtodoist` |
| weekly-newsletter-podcast | Every Monday at 7:30 PM | [Projects/weekly-newsletter-podcast/SKILL.md](Projects/weekly-newsletter-podcast/SKILL.md) | `com.dalton.podcast-generator` |
| monthly-comms-maintenance | 1st of each month at 7:00 PM | [Projects/monthly-comms-maintenance/SKILL.md](Projects/monthly-comms-maintenance/SKILL.md) | `com.dalton.commsmaintenance` |

Each task follows the same pattern:
1. LaunchAgent fires via `osascript -e 'do shell script "..."'`
2. `run_*.sh` locates the Claude binary, sets env vars, runs `claude --print --dangerously-skip-permissions < SKILL.md`
3. Output is delivered (Todoist tasks added, Apple Note created, MP3 written to iCloud)
4. Everything logged to `*.log` in the project folder

### Modify a task
- **Logic**: Edit `SKILL.md` in the project folder
- **Schedule**: Edit the `.plist` in the project folder, copy to `~/Library/LaunchAgents/`, then reload:
  ```bash
  launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/<plist>
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<plist>
  ```

### Debug
```bash
# All agents should show exit code 0
launchctl list | grep com.dalton

# Force-run any task manually
/bin/bash /Users/daltonhaslam/Documents/Claude/Personal/Projects/<task>/run_*.sh
```
