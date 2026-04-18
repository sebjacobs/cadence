# running-playlists

Tools for building continuous, tempo-ramped run playlists from an audio file collection.

The pipeline:

1. **Index** a directory of audio files into a sqlite catalogue (`music.db`) via `ffprobe` tag extraction — `scripts/index_music.py`
2. **Pick** tracks by target BPM and genre — SQL against `music.db`
3. **Retempo** each track to an exact target BPM — `scripts/retempo.sh`
4. **Mix** retempoed tracks with crossfades — `scripts/mix.sh`
5. **Wrap** as mp4 with a cover image, ready to upload — `scripts/tovideo.sh`

`scripts/build-run-playlist.sh` orchestrates steps 3–5 from a ramp file (`path target_bpm` per line).

## BPM data

BPM data provided by [GetSongBPM.com](https://getsongbpm.com).

## Layout

```
scripts/       pipeline scripts
music.db       sqlite catalogue (gitignored)
tmp/           scratch output (gitignored)
```
