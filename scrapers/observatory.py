"""The Observatory North Park calendar scraper.

observatorysd.com embeds schema.org MusicEvent JSON-LD for its upcoming
shows in the static homepage HTML. Each event links straight to its
Ticketmaster page. Start dates are naive local (Pacific) times.

Only events whose venue address is in San Diego are kept (the site
sometimes cross-lists the Santa Ana location).
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from .common import http_get

PAGE_URL = "https://www.observatorysd.com/"

VENUE_URLS = {
    "the observatory north park": "https://www.observatorysd.com",
    "observatory north park": "https://www.observatorysd.com",
}

AGE_SUFFIX = re.compile(r"\s*[-–]\s*(\d+)\+\s*$")


def _show_from_ld(ev: dict) -> dict | None:
    loc = ev.get("location") or {}
    addr = (loc.get("address") or {}).get("addressLocality") or ""
    if addr.strip().lower() not in ("san diego", ""):
        return None  # e.g. the Santa Ana room

    venue = (loc.get("name") or "The Observatory North Park").strip()
    title = (ev.get("name") or "").strip()
    age = None
    m = AGE_SUFFIX.search(title)
    if m:
        age = f"{m.group(1)}+"
        title = title[: m.start()].strip()

    start = ev.get("startDate")
    if not start:
        return None
    dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(start, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        return None  # not a plain local datetime

    ticket = ev.get("url")
    return {
        "id": f"observatory:{ev.get('@id') or ticket}",
        "source": "observatory",
        "title": title,
        "venue": venue,
        "date": dt.date().isoformat(),
        "show_time": dt.strftime("%H:%M"),
        "doors_time": None,
        "age_limit": age,
        "event_url": ticket,
        "ticket_url": ticket,
        "ticket_kind": "direct",
        "sold_out": False,
        "band_url": None,
        "venue_url": VENUE_URLS.get(venue.lower(), "https://www.observatorysd.com"),
        "timezone": "America/Los_Angeles",
    }


def parse_page(html: str) -> list[dict]:
    shows: list[dict] = []
    for raw in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "MusicEvent":
                show = _show_from_ld(item)
                if show:
                    shows.append(show)
    return shows


async def scrape(browser=None) -> list[dict]:
    html = http_get(PAGE_URL)
    shows = parse_page(html)
    if not shows:
        raise RuntimeError(
            "Observatory: no MusicEvent JSON-LD found (layout changed?)"
        )
    return shows
