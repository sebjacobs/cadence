#!/usr/bin/env python3
"""Index a music library into a sqlite db using ffprobe tag extraction."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".ogg", ".opus"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
  id           INTEGER PRIMARY KEY,
  path         TEXT UNIQUE NOT NULL,
  artist       TEXT,
  release      TEXT,
  title        TEXT,
  track_no     INTEGER,
  year         INTEGER,
  genre        TEXT,
  duration_s   REAL,
  bpm          REAL,
  mtime        REAL,
  indexed_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_tracks_genre  ON tracks(genre);
CREATE INDEX IF NOT EXISTS idx_tracks_bpm    ON tracks(bpm);
CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);
CREATE INDEX IF NOT EXISTS idx_tracks_year   ON tracks(year);
"""


def ffprobe(path: Path) -> dict | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def extract(probe: dict, path: Path) -> dict:
    fmt = probe.get("format", {})
    tags = {k.lower(): v for k, v in fmt.get("tags", {}).items()}

    def num(v):
        try: return float(v) if v is not None else None
        except (TypeError, ValueError): return None

    def year(v):
        if not v: return None
        s = str(v)[:4]
        return int(s) if s.isdigit() else None

    def track(v):
        if not v: return None
        s = str(v).split("/")[0]
        return int(s) if s.isdigit() else None

    bpm = tags.get("bpm") or tags.get("tbpm") or tags.get("tmpo")

    return {
        "artist":     tags.get("artist"),
        "release":    tags.get("album"),
        "title":      tags.get("title"),
        "track_no":   track(tags.get("track")),
        "year":       year(tags.get("date") or tags.get("year")),
        "genre":      tags.get("genre"),
        "duration_s": num(fmt.get("duration")),
        "bpm":        num(bpm),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--library", required=True, type=Path)
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--limit", type=int, default=None, help="cap number of files (for testing)")
    p.add_argument("--force", action="store_true", help="re-probe even if mtime unchanged")
    args = p.parse_args()

    if not args.library.is_dir():
        print(f"library not found: {args.library}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(args.db)
    conn.executescript(SCHEMA)

    existing = {row[0]: row[1] for row in conn.execute("SELECT path, mtime FROM tracks")}

    files = [f for f in args.library.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS]
    if args.limit:
        files = files[: args.limit]
    total = len(files)
    print(f"found {total} audio files under {args.library}")

    inserted = updated = skipped = failed = 0
    start = time.time()

    for i, f in enumerate(files, 1):
        path_str = str(f)
        mtime = f.stat().st_mtime
        if not args.force and existing.get(path_str) == mtime:
            skipped += 1
        else:
            probe = ffprobe(f)
            if probe is None:
                failed += 1
            else:
                row = extract(probe, f)
                row["path"] = path_str
                row["mtime"] = mtime
                row["indexed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                cols = ", ".join(row.keys())
                placeholders = ", ".join(f":{k}" for k in row.keys())
                conn.execute(
                    f"INSERT INTO tracks ({cols}) VALUES ({placeholders}) "
                    f"ON CONFLICT(path) DO UPDATE SET "
                    + ", ".join(f"{k}=excluded.{k}" for k in row.keys() if k != "path"),
                    row,
                )
                if path_str in existing:
                    updated += 1
                else:
                    inserted += 1

        if i % 200 == 0 or i == total:
            conn.commit()
            elapsed = time.time() - start
            rate = i / elapsed if elapsed else 0
            eta = (total - i) / rate if rate else 0
            print(f"  [{i}/{total}] inserted={inserted} updated={updated} "
                  f"skipped={skipped} failed={failed} ({rate:.1f}/s, eta {eta:.0f}s)")

    conn.commit()
    conn.close()
    print(f"\ndone — inserted={inserted} updated={updated} skipped={skipped} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
