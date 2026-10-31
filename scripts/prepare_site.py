#!/usr/bin/env python3
"""Validate a snapshot and stage only public files for GitHub Pages."""
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from artist_links import verified_record
PUBLIC_FILES = ("index.html", "shows.json")


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("shows"), list):
        raise ValueError("shows.json must contain a shows array")
    datetime.fromisoformat(data["generated_at"])
    if not isinstance(data.get("sources"), dict):
        raise ValueError("shows.json must contain source status metadata")
    for i, show in enumerate(data["shows"]):
        for field in ("id", "source", "title", "venue", "date"):
            if not isinstance(show.get(field), str) or not show[field].strip():
                raise ValueError(f"Show {i}: missing {field}")
        date.fromisoformat(show["date"])
        for field in ("show_time", "doors_time"):
            if show.get(field):
                datetime.strptime(show[field], "%H:%M")
        for field in ("event_url", "ticket_url", "band_url", "venue_url"):
            url = show.get(field)
            if url:
                parsed = urlsplit(url)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    raise ValueError(f"Show {i}: invalid {field}")
        for artist in show.get("artists", []):
            if not isinstance(artist, dict) or not isinstance(artist.get("name"), str) or not artist["name"].strip():
                raise ValueError(f"Show {i}: artist needs an explicit name")
            record = dict(artist, verified=artist.get("website_verified"))
            if artist.get("official_url") and not verified_record(record, show):
                raise ValueError(f"Show {i}: artist URL lacks valid verification")
            if artist.get("website_verified") is True and not verified_record(record, show):
                raise ValueError(f"Show {i}: invalid verified artist record")
        if show.get("band_url"):
            artists = show.get("artists", [])
            if len(artists) != 1 or artists[0].get("official_url") != show["band_url"]:
                raise ValueError(f"Show {i}: legacy band_url cannot link a whole lineup")


def main():
    data = json.loads((ROOT / "shows.json").read_text(encoding="utf-8"))
    validate(data)
    site = ROOT / "site"
    # Only replace our public build directory, never repository source.
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()
    for name in PUBLIC_FILES:
        shutil.copy2(ROOT / name, site / name)
    (site / ".nojekyll").touch()
    print(f"Ready: {len(data['shows'])} snapshot listings; only public files staged.")
    print(f"Snapshot generated: {data['generated_at']}")


if __name__ == "__main__":
    main()
