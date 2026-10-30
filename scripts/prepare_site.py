#!/usr/bin/env python3
"""Validate a snapshot and stage only public files for GitHub Pages."""
import json
import shutil
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
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
