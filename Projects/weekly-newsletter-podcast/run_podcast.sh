#!/bin/bash
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

CLAUDE=$(ls -td /Users/daltonhaslam/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | head -1)
SKILL="/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/SKILL.md"
SCRIPT_FILE="/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/podcast_script.txt"
PROCESSED_HTML="/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/newsletters_processed.html"
AUDIO_FOLDER="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Claude-Audio"
DATE=$(date +%Y%m%d)
OUTPUT="$AUDIO_FOLDER/podcast_$DATE.mp3"
LOG="/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/podcast.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

log "Starting weekly podcast..."

if [ -z "$CLAUDE" ] || [ ! -x "$CLAUDE" ]; then
    log "ERROR: claude binary not found under ~/.vscode/extensions"
    exit 1
fi

log "Using claude: $CLAUDE"

# ── Phase 1: Claude fetches newsletters and writes podcast_script.txt ──────────

"$CLAUDE" --print --dangerously-skip-permissions < "$SKILL" >> "$LOG" 2>&1

if [ ! -f "$SCRIPT_FILE" ]; then
    log "ERROR: podcast_script.txt was not written by claude"
    exit 1
fi

log "podcast_script.txt written. Starting TTS synthesis..."

# ── Phase 2: TTS synthesis → MP3 in iCloud Drive ──────────────────────────────

TMP_DIR=$(mktemp -d)

FFMPEG=""
for p in /opt/homebrew/bin/ffmpeg /usr/local/bin/ffmpeg; do
    [[ -x "$p" ]] && FFMPEG="$p" && break
done
if [[ -z "$FFMPEG" ]]; then
    log "ERROR: ffmpeg not found. Install with: brew install ffmpeg"
    exit 1
fi

VOICE_LIST=$(/usr/bin/say -v '?' 2>/dev/null)

if echo "$VOICE_LIST" | grep -qi "^Lee "; then
    HOST_A_VOICE="Lee"
else
    HOST_A_VOICE="Alex"
fi

if echo "$VOICE_LIST" | grep -qi "^Ava "; then
    HOST_B_VOICE="Ava"
else
    HOST_B_VOICE="Samantha"
fi

log "Voices: Host A=$HOST_A_VOICE  Host B=$HOST_B_VOICE"

mkdir -p "$AUDIO_FOLDER"
find "$AUDIO_FOLDER" -name "podcast_*.mp3" ! -name "podcast_$DATE.mp3" -delete 2>/dev/null || true

i=0
while IFS= read -r line; do
    if [[ "$line" == "Host A:"* ]]; then
        text="${line:8}"
        voice="$HOST_A_VOICE"
    elif [[ "$line" == "Host B:"* ]]; then
        text="${line:8}"
        voice="$HOST_B_VOICE"
    else
        continue
    fi

    [[ -z "$text" ]] && continue

    seg_txt="$TMP_DIR/seg_$(printf '%04d' $i).txt"
    seg_aiff="$TMP_DIR/seg_$(printf '%04d' $i).aiff"
    printf '%s' "$text" > "$seg_txt"
    /usr/bin/say -v "$voice" -f "$seg_txt" -o "$seg_aiff" 2>>"$LOG"
    i=$((i + 1))
done < "$SCRIPT_FILE"

log "Generated $i audio segments."

if [[ $i -eq 0 ]]; then
    log "ERROR: No segments generated. Check script format."
    rm -rf "$TMP_DIR"
    exit 1
fi

concat_file="$TMP_DIR/concat.txt"
for f in $(ls "$TMP_DIR"/seg_*.aiff | sort); do
    echo "file '$f'" >> "$concat_file"
done

"$FFMPEG" -f concat -safe 0 -i "$concat_file" -acodec libmp3lame -q:a 3 "$OUTPUT" -y 2>>"$LOG"
rm -rf "$TMP_DIR"

log "MP3 written: $OUTPUT"

# ── Phase 3: Create Apple Note from newsletters_processed.html ─────────────────

if [ ! -f "$PROCESSED_HTML" ]; then
    log "WARNING: newsletters_processed.html not found — skipping Apple Note"
    log "Podcast complete."
    exit 0
fi

log "Creating Apple Note..."

export PROCESSED_PATH="$PROCESSED_HTML"
export NOTE_TITLE="Newsletters Processed — $(date +'%B %-d, %Y')"

python3 << 'PYEOF'
import subprocess, os, tempfile

processed_path = os.environ['PROCESSED_PATH']
note_title = os.environ['NOTE_TITLE']

script = f'''tell application "Notes"
    tell account "iCloud"
        set noteTitle to "{note_title}"
        set htmlContent to do shell script "cat " & quoted form of "{processed_path}"
        try
            set matchingNotes to every note whose name is noteTitle
            repeat with n in matchingNotes
                delete n
            end repeat
        end try
        make new note with properties {{name:noteTitle, body:htmlContent}}
    end tell
end tell'''

with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False) as f:
    f.write(script)
    tmp = f.name

try:
    result = subprocess.run(['osascript', tmp], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"osascript error: {result.stderr}")
        raise SystemExit(1)
    print("Apple Note created successfully")
finally:
    os.unlink(tmp)
PYEOF

log "Apple Note created successfully."
log "Podcast complete."
