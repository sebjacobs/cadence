# cadence

Tools for building tempo-ramped run playlists. See `README.md` for the pipeline overview.

## Conventions

- **Python:** use `uv` — never `pip` or bare `python3`. `.venv/` is local
- **Scratch:** put temporary output in `tmp/` (gitignored). Never `/tmp`
- **DB:** `music.db` lives at the repo root, gitignored — it's data, regenerable via `scripts/index_music.py`

## Current focus

Playlist generation is the active layer: `scripts/generate_run_playlists.py` selects tracks at a target BPM from `music.db`, retempos, mixes with crossfades, wraps as mp4 under `tmp/playlists/<bpm>bpm/<mins>mins/`, and emits a `{slug}_tracklist.txt` sidecar with crossfade-adjusted timestamps for YouTube descriptions. `scripts/extend_playlist_tsvs.py` tops up short tsvs. `scripts/write_tracklists.py` backfills tracklists for already-rendered mixes without re-mixing. BPM ingestion pipeline is complete — see `ROADMAP.md` for done/open items.

Track selection respects `run_exclude=1` on `tracks`. Exclusions come from: `scripts/analyse_beat_clarity.py` (auto-sets `run_exclude_reason='half-step'` when `groove_delta < 0.05`); and `scripts/reject_track.py <id> "reason"` for manual cuts. `scripts/reject_track.py --review --m3u` exports beat-review candidates as a playlist for audition; `scripts/audit_shipped_playlists.py` reports which shipped-playlist tracks are now excluded. `scripts/probe_beat_clarity.py` is the diagnostic spike — calibrate thresholds before rerunning the batch analyser.

## Tools

- `ffmpeg` / `ffprobe` — tag extraction, stream inspection, audio conversion
- `aubio` — BPM detection (fallback only; unreliable on breakbeat-led genres)
- `rubberband` / `ffmpeg atempo` — tempo adjustment without pitch change

## External data

BPM values from GetSongBPM.com — attribution required, see `README.md`.
