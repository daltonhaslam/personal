#!/bin/bash
# Weekly Newsletter Podcast — TTS Generator
# Triggered by LaunchAgent (WatchPaths + Tuesday 6am fallback)
# Uses macOS built-in `say` command — no network or API keys needed

SCRIPT_FILE="$HOME/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/podcast_script.txt"
AUDIO_FOLDER="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Claude-Audio"
DATE=$(date +%Y%m%d)
OUTPUT="$AUDIO_FOLDER/podcast_$DATE.mp3"
TMP_DIR=$(mktemp -d)
LOG="$HOME/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/podcast_tts.log"
TRIGGER="$HOME/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/.podcast_ready"

echo "[$(date)] Podcast generator triggered." >> "$LOG"

# Bail if no script file
if [[ ! -f "$SCRIPT_FILE" ]]; then
    echo "[$(date)] No script file found. Exiting." >> "$LOG"
    exit 0
fi

# Bail if script is older than 36 hours (stale from a previous week)
if [[ -n "$(find "$SCRIPT_FILE" -mmin +2160 2>/dev/null)" ]]; then
    echo "[$(date)] Script file too old. Exiting." >> "$LOG"
    rm -f "$TRIGGER"
    exit 0
fi

# Find ffmpeg (Homebrew Intel or Apple Silicon)
FFMPEG=""
for p in /opt/homebrew/bin/ffmpeg /usr/local/bin/ffmpeg; do
    [[ -x "$p" ]] && FFMPEG="$p" && break
done
if [[ -z "$FFMPEG" ]]; then
    echo "[$(date)] ERROR: ffmpeg not found. Install with: brew install ffmpeg" >> "$LOG"
    exit 1
fi

# Select voices by checking installed voice list directly
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

echo "[$(date)] Voices: Host A=$HOST_A_VOICE  Host B=$HOST_B_VOICE" >> "$LOG"

mkdir -p "$AUDIO_FOLDER"

# Remove any old podcast MP3s
find "$AUDIO_FOLDER" -name "podcast_*.mp3" ! -name "podcast_$DATE.mp3" -delete 2>/dev/null || true

# Parse script and generate one AIFF per line
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

echo "[$(date)] Generated $i audio segments." >> "$LOG"

if [[ $i -eq 0 ]]; then
    echo "[$(date)] ERROR: No segments generated. Check script format." >> "$LOG"
    rm -rf "$TMP_DIR"
    exit 1
fi

# Build ffmpeg concat list
concat_file="$TMP_DIR/concat.txt"
for f in $(ls "$TMP_DIR"/seg_*.aiff | sort); do
    echo "file '$f'" >> "$concat_file"
done

# Concatenate and convert to MP3
"$FFMPEG" -f concat -safe 0 -i "$concat_file" -acodec libmp3lame -q:a 3 "$OUTPUT" -y 2>>"$LOG"

if [[ $? -eq 0 ]]; then
    echo "[$(date)] SUCCESS: $OUTPUT" >> "$LOG"
else
    echo "[$(date)] ERROR: ffmpeg failed. Check podcast_tts.log." >> "$LOG"
    rm -rf "$TMP_DIR"
    exit 1
fi

# Cleanup
rm -rf "$TMP_DIR"
rm -f "$TRIGGER"
echo "[$(date)] Done." >> "$LOG"
