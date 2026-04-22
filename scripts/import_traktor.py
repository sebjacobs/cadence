#!/usr/bin/env python3
"""Import Traktor analysis data from collection.nml into music.db.

Populates per-track columns (no overwrite of existing bpm/genre):
  - traktor_bpm           float BPM from <TEMPO>
  - traktor_key           integer 0-23 from <MUSICAL_KEY>
  - traktor_beatgrid_ms   float ms from <CUE_V2 TYPE="4"> (AutoGrid anchor)
  - traktor_imported_at   ISO timestamp

Matches NML entries to music.db rows by absolute file path.

Usage:
  uv run scripts/import_traktor.py [--nml path] [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "music.db"
DEFAULT_NML = REPO / "collection.nml"

COLUMNS = {
    "traktor_bpm": "REAL",
    "traktor_key": "INTEGER",
    "traktor_beatgrid_ms": "REAL",
    "traktor_imported_at": "TEXT",
}


def ensure_columns(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tracks)")}
    for name, decl in COLUMNS.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE tracks ADD COLUMN {name} {decl}")
    conn.commit()


def reconstruct_path(loc: ET.Element) -> str | None:
    """Traktor LOCATION: DIR uses '/:' as separator, FILE is basename."""
    d = loc.get("DIR")
    f = loc.get("FILE")
    if not d or not f:
        return None
    return d.replace("/:", "/") + f


def parse_entry(entry: ET.Element) -> dict | None:
    loc = entry.find("LOCATION")
    if loc is None:
        return None
    path = reconstruct_path(loc)
    if not path:
        return None
    tempo = entry.find("TEMPO")
    key = entry.find("MUSICAL_KEY")
    # AutoGrid is TYPE=4; there's typically exactly one per track
    grid_ms = None
    for cue in entry.findall("CUE_V2"):
        if cue.get("TYPE") == "4":
            try:
                grid_ms = float(cue.get("START", ""))
            except ValueError:
                grid_ms = None
            break
    return {
        "path": path,
        "bpm": float(tempo.get("BPM")) if tempo is not None and tempo.get("BPM") else None,
        "key": int(key.get("VALUE")) if key is not None and key.get("VALUE") else None,
        "beatgrid_ms": grid_ms,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nml", type=Path, default=DEFAULT_NML, help="Path to collection.nml")
    ap.add_argument("--dry-run", action="store_true", help="Parse and report; do not write")
    ap.add_argument("--limit", type=int, help="Process only the first N entries")
    args = ap.parse_args()

    if not args.nml.exists():
        raise SystemExit(f"NML not found: {args.nml}")
    if not DB_PATH.exists():
        raise SystemExit(f"music.db not found: {DB_PATH}")

    print(f"Parsing {args.nml} ...", flush=True)
    tree = ET.parse(args.nml)
    entries = tree.getroot().findall(".//ENTRY")
    if args.limit:
        entries = entries[: args.limit]
    print(f"  {len(entries)} entries")

    parsed: list[dict] = []
    skipped = 0
    for e in entries:
        row = parse_entry(e)
        if row is None or row["bpm"] is None:
            skipped += 1
            continue
        parsed.append(row)
    print(f"  {len(parsed)} parseable, {skipped} skipped (no path or no BPM)")

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_columns(conn)
        db_paths = {r[0]: r[1] for r in conn.execute("SELECT path, id FROM tracks")}

        matched: list[tuple[int, dict]] = []
        unmatched: list[str] = []
        for row in parsed:
            tid = db_paths.get(row["path"])
            if tid is None:
                unmatched.append(row["path"])
            else:
                matched.append((tid, row))

        print(f"  {len(matched)} matched to music.db, {len(unmatched)} unmatched")
        if unmatched[:3]:
            print("  sample unmatched:")
            for p in unmatched[:3]:
                print(f"    {p}")

        if args.dry_run:
            print("\n[dry-run] no writes")
            return

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.executemany(
            """UPDATE tracks
               SET traktor_bpm = ?, traktor_key = ?, traktor_beatgrid_ms = ?,
                   traktor_imported_at = ?
               WHERE id = ?""",
            [
                (r["bpm"], r["key"], r["beatgrid_ms"], now, tid)
                for tid, r in matched
            ],
        )
        conn.commit()
        print(f"\nUpdated {len(matched)} rows at {now}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
