#!/usr/bin/env python3
"""Run all venue scrapers, merge, dedupe, and write shows.json.

Usage: python run.py [--keep-past] [--from-cache] [--enrich-artists]

A failed source keeps its last successful data (stored in data/). The
script exits 1 only if every source fails, so one flaky venue never
blanks the website.
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from artist_links import apply_artist_links
from artist_enrichment import merge_registries, run_enrichment

from scrapers import bellyup, humphreys, observatory, quartyard, radyshell, soma, sodabar
from scrapers.common import (
    Browser,
    ROOT,
    dedupe_key,
    load_source,
    save_source,
)

LA = ZoneInfo("America/Los_Angeles")
SOURCES = {
    "bellyup": bellyup,
    "sodabar": sodabar,
    "quartyard": quartyard,
    "observatory": observatory,
    "humphreys": humphreys,
    "radyshell": radyshell,
    "soma": soma,
}
OVERRIDES_FILE = ROOT / "band_overrides.json"
LINEUPS_FILE = ROOT / "event_lineups.json"


def apply_band_overrides(shows: list[dict], overrides: dict, lineups=None) -> None:
    """Compatibility entry point using the exact, evidence-backed artist policy."""
    apply_artist_links(shows, overrides, lineups)


def merged_and_sorted(source_payloads: dict[str, dict], keep_past: bool) -> list[dict]:
    today = datetime.now(LA).date().isoformat()
    by_key: dict[tuple, dict] = {}
    for name in sorted(source_payloads):
        for show in source_payloads[name]["shows"]:
            if not keep_past and show.get("date", "") < today:
                continue
            key = dedupe_key(show)
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = show
                continue
            # Duplicate (same band + venue + date from two sources):
            # keep whichever row is more complete, fill any gaps.
            best, worst = (
                (existing, show)
                if sum(bool(v) for v in existing.values()) >= sum(bool(v) for v in show.values())
                else (show, existing)
            )
            for k, v in worst.items():
                if not best.get(k) and v:
                    best[k] = v
            by_key[key] = best

    shows = sorted(
        by_key.values(),
        key=lambda s: (s.get("date", ""), s.get("show_time") or "", s.get("venue", "")),
    )
    for s in shows:
        ensure_ticket_kind(s)
    return shows


def ensure_ticket_kind(show: dict) -> None:
    """Label each ticket link as a direct purchase link or an event-page
    fallback. New scrapers set this; rows rebuilt from cached data get the
    equivalent heuristic so the site can label links honestly."""
    if not show.get("ticket_url") or show.get("ticket_kind"):
        return
    if show["source"] == "bellyup":
        show["ticket_kind"] = (
            "direct" if "ticketweb.com" in show["ticket_url"] else "event_page"
        )
    else:
        show["ticket_kind"] = "direct"


async def main() -> int:
    keep_past = "--keep-past" in sys.argv
    from_cache = "--from-cache" in sys.argv
    if from_cache:
        print("Rebuilding shows.json from cached venue data"
              + ("; artist API enabled" if "--enrich-artists" in sys.argv else " (no network)"))
    else:
        browser = Browser()
        await browser.start()
        try:
            for name, module in SOURCES.items():
                try:
                    shows = await module.scrape(browser)
                    save_source(name, shows, ok=True)
                    print(f"[{name}] ok - {len(shows)} shows")
                except Exception as e:
                    save_source(name, [], ok=False)
                    print(f"[{name}] FAILED - {e}", file=sys.stderr)
        finally:
            await browser.close()

    payloads = {}
    any_ok = False
    for name in SOURCES:
        payload = load_source(name) or {"status": "failed", "shows": []}
        payloads[name] = payload
        if payload.get("status") == "ok":
            any_ok = True
        else:
            print(
                f"[{name}] keeping last good data "
                f"({len(payload.get('shows', []))} shows, "
                f"from {payload.get('last_success', 'never')})",
                file=sys.stderr,
            )
    if not any_ok:
        print("All sources failed - not updating shows.json", file=sys.stderr)
        return 1

    shows = merged_and_sorted(payloads, keep_past)
    # A malformed registry or lineup must never preserve cached artist URLs.
    try:
        overrides = json.loads(OVERRIDES_FILE.read_text()) if OVERRIDES_FILE.exists() else {}
        lineups = json.loads(LINEUPS_FILE.read_text()) if LINEUPS_FILE.exists() else {}
        if not isinstance(overrides, dict) or not isinstance(lineups, dict):
            raise ValueError("Artist registry and lineups must be objects")
        try:
            automatic, artist_status = run_enrichment(
                shows, lineups, online=not from_cache or "--enrich-artists" in sys.argv)
        except Exception as exc:
            # Optional artist metadata must not prevent venue-data publication.
            print(f"Artist enrichment unavailable: {exc}", file=sys.stderr)
            automatic, artist_status = {}, {"status": "unavailable"}
        apply_band_overrides(shows, merge_registries(automatic, overrides), lineups)
    except (ValueError, TypeError) as exc:
        print(f"Artist links disabled: {exc}", file=sys.stderr)
        apply_band_overrides(shows, {}, {})
        artist_status = {"status": "invalid_registry"}

    out = {
        "generated_at": datetime.now(LA).isoformat(timespec="seconds"),
        "artist_enrichment": artist_status,
        "sources": {
            name: {
                "status": p.get("status"),
                "last_success": p.get("last_success"),
                "show_count": len(p.get("shows", [])),
            }
            for name, p in payloads.items()
        },
        "shows": shows,
    }
    (ROOT / "shows.json").write_text(json.dumps(out, indent=1))
    print(f"shows.json written - {len(shows)} shows")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
