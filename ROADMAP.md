# Roadmap

## Populate bpm for the catalogue — lookup first, detect as fallback

The indexer populates bpm for only a small fraction of tracks (mostly those already tagged at source). Aubio detection alone is unreliable for breakbeat-led genres (detected 109.40 for a 175-bpm track — tracks breakbeat, not kick; half-tempo heuristic doesn't cover this case).

- Add `bpm_source` column to `tracks` (values: `lookup`, `detected`, `manual`)
- Lookup step keyed on `artist + title` — API survey done:
  - **GetSongBPM** (preferred) — free, text lookup, returns BPM; was down for maintenance on 2026-04-17, retry
  - **Discogs** — fallback; BPM patchy but coverage good
  - ~~Shazam via `shazamio`~~ — `search_track` broken (404/XML); also needs audio not text
  - ~~Spotify `audio_features`~~ — endpoint restricted for new apps since late 2024
  - ~~AcousticBrainz~~ — shut down 2022
- Fall back to aubio only when no API match; cross-check with a second detector (`bpm-tools`, essentia) before trusting
- Never overwrite `manual` values

## First lookup target

Prototype the GetSongBPM lookup against a small set of artists with well-catalogued discographies (excluding DJ mixes > 10 min). Confirms coverage and BPM accuracy on a tight genre cluster before rolling out to the full catalogue.
