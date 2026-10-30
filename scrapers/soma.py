"""SOMA San Diego (all-ages club, Midtown) calendar scraper.

somasandiego.com/events/ is a WordPress Modern Events Calendar list,
fully static: each <li> has month/day/year/weekday spans, the event
title link, an event-time line ("Doors 6 pm - Sidestage",
"Mainstage - 8pm") and a Tickets button. Some shows are sold out
(li class event-soldout) and keep no ticket link.
"""
from __future__ import annotations

import re

from .common import http_get, parse_clock

PAGE_URL = "https://www.somasandiego.com/events/"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

DOORS = re.compile(r"Doors?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)", re.I)
STAGE_TIME = re.compile(r"(?:Mainstage|Sidestage)\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*[ap]m)", re.I)


def _times(text: str) -> tuple[str | None, str | None]:
    """SOMA time lines mix doors and stage times; take what's published."""
    doors = show = None
    m = DOORS.search(text)
    if m:
        doors = parse_clock(m.group(1))
    m = STAGE_TIME.search(text)
    if m:
        show = parse_clock(m.group(1))
    if not show:
        m = re.search(r"(\d{1,2}(?::\d{2})?\s*[ap]m)", text, re.I)
        if m and not doors:
            show = parse_clock(m.group(1))
    return doors, show


def parse_page(html: str) -> list[dict]:
    shows: list[dict] = []
    for m in re.finditer(
        r'<li class="(event-(?:onsale|soldout))">(.*?)</li>', html, re.S
    ):
        block_cls, block = m.group(1), m.group(2)

        month = day = year = None
        dm = re.search(
            r'<span class="event-month">([A-Za-z]{3})[a-z]*</span>\s*'
            r'<span class="event-day">(\d{1,2})</span>\s*'
            r'<span class="event-year">(\d{4})</span>',
            block,
        )
        if dm:
            month, day, year = (
                MONTHS.get(dm.group(1).lower()),
                int(dm.group(2)),
                int(dm.group(3)),
            )
        if not (month and day and year):
            continue

        tm = re.search(r'<h3><a href="([^"]+)">([^<]+)</a></h3>', block)
        if not tm:
            continue
        event_url, title = tm.group(1), tm.group(2).strip()

        time_text = ""
        ttm = re.search(r'class="event-time">([^<]*)<', block)
        if ttm:
            time_text = ttm.group(1)
        doors, show = _times(time_text)

        ticket = None
        ptm = re.search(r'<a href="([^"]+)"[^>]*class="button event-tickets"', block)
        if ptm:
            ticket = ptm.group(1)

        shows.append(
            {
                "id": f"soma:{year}{month:02d}{day:02d}:{title[:30]}",
                "source": "soma",
                "title": title,
                "venue": "SOMA San Diego",
                "date": f"{year}-{month:02d}-{day:02d}",
                "show_time": show,
                "doors_time": doors,
                "age_limit": None,
                "event_url": event_url,
                "ticket_url": ticket,
                "ticket_kind": "direct" if ticket else None,
                "sold_out": "soldout" in block_cls,
                "band_url": None,
                "venue_url": "https://www.somasandiego.com/",
                "timezone": "America/Los_Angeles",
            }
        )

    return shows


async def scrape(browser=None) -> list[dict]:
    html = http_get(PAGE_URL)
    shows = parse_page(html)
    if not shows:
        raise RuntimeError("SOMA: no event blocks found (layout changed?)")
    return shows
