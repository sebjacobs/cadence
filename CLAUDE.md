# running-playlists

Tools for building tempo-ramped run playlists. See `README.md` for the pipeline overview.

## Conventions

- **Python:** use `uv` — never `pip` or bare `python3`. `.venv/` is local
- **Scratch:** put temporary output in `tmp/` (gitignored). Never `/tmp`
- **DB:** `music.db` lives at the repo root, gitignored — it's data, regenerable via `scripts/index_music.py`

## Current focus

Populating `bpm` across the catalogue — see `ROADMAP.md`. Lookup-first (GetSongBPM) with aubio as last-resort fallback; auto-detection proved unreliable on breakbeat-led genres.

## Tools

- `ffmpeg` / `ffprobe` — tag extraction, stream inspection, audio conversion
- `aubio` — BPM detection (fallback only; unreliable on breakbeat-led genres)
- `rubberband` / `ffmpeg atempo` — tempo adjustment without pitch change

## External data

BPM values from GetSongBPM.com — attribution required, see `README.md`.
