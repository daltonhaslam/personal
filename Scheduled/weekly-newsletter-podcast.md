# weekly-newsletter-podcast

**Schedule:** Every Monday at 8:00 PM
**Skill file:** [Personal/Projects/weekly-newsletter-podcast/SKILL.md](../Projects/weekly-newsletter-podcast/SKILL.md)
**Status:** Active

## What It Does
Fetches the past week's newsletters from Gmail (Healthcare Brew, Health Tech Nerds, Book Freak, ACPA News to Note, Robert Oubre MD). Generates a two-host podcast script, writes it to `Projects/weekly-newsletter-podcast/podcast_script.txt`, and drops a `.podcast_ready` trigger file. The macOS LaunchAgent (`com.dalton.podcast-generator.plist`) picks up the trigger and synthesizes audio via `run_podcast_tts.sh`, saving the MP3 to iCloud Drive. Also writes `newsletters_processed.html` — Apple Shortcut at 8:15 PM creates an Apple Note for batch-delete from Gmail.

## Supporting Files
- `run_podcast_tts.sh` — TTS audio generation using macOS `say` + ffmpeg
- `com.dalton.podcast-generator.plist` — macOS LaunchAgent (watches for `.podcast_ready`)
- `generate_podcast.py` — supporting script

## To Modify
- Task logic → edit `Projects/weekly-newsletter-podcast/SKILL.md`
- TTS audio generation → edit `run_podcast_tts.sh`
- Schedule → update RemoteTrigger via `/schedule` skill in Claude Code
