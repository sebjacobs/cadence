#!/usr/bin/env bash
set -euo pipefail

MIN_BPM=170
MAX_BPM=180

usage() {
  cat <<EOF
Usage: $(basename "$0") -t TARGET_BPM INPUT [OUTPUT]

Detect the BPM of INPUT and time-stretch it to TARGET_BPM (pitch preserved).
Fails if the detected BPM is outside ${MIN_BPM}-${MAX_BPM}.

  -t TARGET_BPM   target tempo (e.g. 178)
  -h              show this help
EOF
  exit "${1:-0}"
}

target=""
while getopts ":t:h" opt; do
  case $opt in
    t) target=$OPTARG ;;
    h) usage 0 ;;
    *) usage 1 ;;
  esac
done
shift $((OPTIND - 1))

[[ -z "$target" || $# -lt 1 ]] && usage 1

input=$1
output=${2:-}

if [[ -z "$output" ]]; then
  ext="${input##*.}"
  base="${input%.*}"
  output="${base}.${target}bpm.${ext}"
fi

for cmd in aubio rubberband bc; do
  command -v "$cmd" >/dev/null || { echo "missing dependency: $cmd" >&2; exit 1; }
done

detected=$(aubio tempo "$input" 2>/dev/null | awk '{print $1}')
[[ -z "$detected" ]] && { echo "could not detect bpm for $input" >&2; exit 1; }

detected_int=${detected%.*}
if (( detected_int < MIN_BPM || detected_int > MAX_BPM )); then
  printf 'detected bpm %s is outside %d-%d — skipping\n' "$detected" "$MIN_BPM" "$MAX_BPM" >&2
  exit 2
fi

ratio=$(echo "scale=6; $target / $detected" | bc -l)
printf 'detected: %s bpm  →  target: %s bpm  (ratio %s)\n' "$detected" "$target" "$ratio"

rubberband --tempo "$ratio" --crisp 6 "$input" "$output"
printf 'wrote %s\n' "$output"
