#!/usr/bin/env python3
"""Audit shipped playlists against current beat-clarity exclusions.

Parses every `*_tracklist.txt` under tmp/playlists/, extracts the
Artist - Title pairs, looks each up in music.db, and reports how many
are now flagged run_exclude=1 (and why). Useful as a sanity check
that the detector hasn't cut tracks you've already happily shipped.

Usage:
  uv run scripts/audit_shipped_playlists.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "music.db"
PLAYLIST_DIR = ROOT / "tmp" / "playlists"

LINE_RE = re.compile(r"^\d+:\d+\s+(.+?)\s+-\s+(.+)$")


def parse_tracklists() -> list[tuple[str, str, Path]]:
    entries = []
    for f in PLAYLIST_DIR.rglob("*_tracklist.txt"):
        for line in f.read_text().splitlines():
            m = LINE_RE.match(line.strip())
            if m:
                entries.append((m.group(1).strip(), m.group(2).strip(), f))
    return entries


def main() -> int:
    if not PLAYLIST_DIR.exists():
        print(f"no playlist dir at {PLAYLIST_DIR}", file=sys.stderr)
        return 1

    entries = parse_tracklists()
    unique = {(a, t) for a, t, _ in entries}
    print(f"parsed {len(entries)} tracklist lines across {len({e[2] for e in entries})} playlists")
    print(f"unique artist/title pairs: {len(unique)}")

    conn = sqlite3.connect(DB_PATH)
    matched = 0
    unmatched: list[tuple[str, str]] = []
    reasons: Counter[str] = Counter()
    flagged_rows: list[tuple[int, str, str, str]] = []

    for artist, title in unique:
        row = conn.execute(
            "SELECT id, run_exclude, run_exclude_reason FROM tracks WHERE artist=? AND title=?",
            (artist, title),
        ).fetchone()
        if not row:
            unmatched.append((artist, title))
            continue
        matched += 1
        tid, excl, reason = row
        if excl:
            reasons[reason or "(no reason)"] += 1
            flagged_rows.append((tid, artist, title, reason or ""))

    print(f"matched in DB: {matched}  unmatched: {len(unmatched)}")
    print()
    print("Exclusions among shipped-playlist tracks:")
    if not reasons:
        print("  (none — detector didn't cut any track you've already used)")
    else:
        for reason, n in reasons.most_common():
            print(f"  {reason:12}  {n}")

    if flagged_rows:
        print()
        print("Flagged tracks (used in shipped playlists but now excluded):")
        for tid, artist, title, reason in sorted(flagged_rows, key=lambda r: (r[3], r[1])):
            print(f"  {tid:>5}  {reason:10}  {artist:30.30}  {title:50.50}")

    if unmatched:
        print()
        print(f"Unmatched (first 10 of {len(unmatched)} — likely renamed in DB):")
        for a, t in unmatched[:10]:
            print(f"  {a} - {t}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
