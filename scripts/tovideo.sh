#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") -i COVER -a AUDIO [-o OUTPUT]

Wrap an audio file as an mp4 with a static cover image, ready for YouTube upload.

  -i COVER     cover image (jpg/png)
  -a AUDIO     audio file (mp3/m4a/wav)
  -o OUTPUT    output mp4 (default: <audio-basename>.mp4)
  -h           show this help
EOF
  exit "${1:-0}"
}

cover=""
audio=""
output=""
while getopts ":i:a:o:h" opt; do
  case $opt in
    i) cover=$OPTARG ;;
    a) audio=$OPTARG ;;
    o) output=$OPTARG ;;
    h) usage 0 ;;
    *) usage 1 ;;
  esac
done

[[ -z "$cover" || -z "$audio" ]] && usage 1
[[ -f "$cover" ]] || { echo "cover not found: $cover" >&2; exit 1; }
[[ -f "$audio" ]] || { echo "audio not found: $audio" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "missing dependency: ffmpeg" >&2; exit 1; }

if [[ -z "$output" ]]; then
  base="${audio%.*}"
  output="${base}.mp4"
fi

printf 'wrapping %s + %s → %s\n' "$audio" "$cover" "$output"
# The image never changes — encode at 1 fps so we're not re-encoding
# thousands of identical frames. YouTube accepts low-fps static videos.
ffmpeg -y -loop 1 -framerate 1 -i "$cover" -i "$audio" \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:v libx264 -tune stillimage -pix_fmt yuv420p -r 1 \
  -c:a aac -b:a 192k -shortest "$output"
printf 'wrote %s\n' "$output"
