"""Belly Up (Solana Beach) calendar scraper.

The calendar page at https://bellyup.com/calendar/ embeds a JavaScript
array of every listed event with id, start datetime, title and venue.
Event page URLs are collected from the static event list markup.

The Belly Up calendar also lists shows promoted at other venues (Music
Box, The Sound, etc.); those are kept with their own venue name and
website when known, and venue_url left null when not.

Ticket links: the calendar itself does not contain purchase URLs. Each
event page (rendered with JS) carries a "TICKETS" button pointing at
TicketWeb plus the doors time, so by default this scraper visits each
upcoming event page to collect them. Pass deep=False to skip that (much
faster, but ticket_url falls back to the event page and doors are
unknown). The fallback is labeled by leaving ticket_url == event_url.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime

from .common import Browser, http_get, strip_tags
from .common import LA as PACIFIC

CALENDAR_URL = "https://bellyup.com/calendar/"

# Verified official venue websites for venues that appear on the calendar.
VENUE_URLS = {
    "belly up": "https://bellyup.com/",
    "the sound": "https://thesoundsd.com/",
    "music box": "https://www.musicboxsd.com/",
    "the observatory north park": "https://www.observatorysd.com/",
    "casbah": "https://www.casbahmusic.com/",
    "soda bar": "https://sodabarmusic.com/",
}

TICKETS_LINK = re.compile(r"ticketweb|tickets?", re.I)
DOORS_TEXT = re.compile(r"Doors:?\s*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", re.I)


def _venue_url(venue_name: str) -> str | None:
    return VENUE_URLS.get(venue_name.strip().lower())


def _unescape_js(s: str) -> str:
    """Undo JS string escapes (\\' and \\\\) in embedded literals."""
    return s.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")


async def _deep_scan(
    browser: Browser, shows: list[dict], today: str
) -> None:
    """Visit each upcoming event page to grab its TicketWeb link + doors.

    Runs a few pages at a time; the whole scan is a few minutes for a
    full calendar. One page failing must not break the run.
    """
    pending = [s for s in shows if s["date"] >= today and s.get("event_url")]
    sem = asyncio.Semaphore(4)

    async def one(show: dict) -> None:
        async with sem:
            page = await browser.page()
            try:
                await page.goto(
                    show["event_url"], timeout=30000, wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(800)
                data = await page.evaluate(
                    """() => {
                        const out = {ticket: null, doors: null};
                        for (const a of document.querySelectorAll('a')) {
                            const t = (a.innerText || '').trim();
                            if (/^tickets?$/i.test(t) || /ticketweb\\.com/.test(a.href)) {
                                out.ticket = a.href;
                                break;
                            }
                        }
                        const m = document.body.innerText.match(/Doors:?\\s*([0-9]{1,2}(:[0-9]{2})?\\s*[ap]\\.?m\\.?)/i);
                        if (m) out.doors = m[1];
                        return out;
                    }"""
                )
            except Exception:
                data = {}
            finally:
                await page.close()
        if data.get("ticket"):
            show["ticket_url"] = data["ticket"]
            show["ticket_kind"] = "direct"
        if data.get("doors"):
            from .common import parse_clock

            show["doors_time"] = parse_clock(data["doors"])
        await asyncio.sleep(0.3)  # be polite to the venue's site

    await asyncio.gather(*(one(s) for s in pending))


async def scrape(browser: Browser | None = None, deep: bool = True) -> list[dict]:
    html = http_get(CALENDAR_URL)
    shows = parse_calendar(html)
    if not shows:
        raise RuntimeError("Belly Up calendar: no events found (page layout changed?)")

    if deep and browser is not None:
        today = datetime.now(PACIFIC).date().isoformat()
        await _deep_scan(browser, shows, today)

    return shows


def parse_calendar(html: str) -> list[dict]:

    # Event page URL for each event id, from the static list markup.
    event_urls: dict[str, str] = {}
    for full, ev_id in re.findall(
        r'href="(https://bellyup\.com/calendar/(\d+)/[a-z0-9-]+)"', html
    ):
        event_urls.setdefault(ev_id, full)

    # The embedded JS array, one object per event. Title/venue strings may
    # contain escaped apostrophes (Jimmy\\'s), so the patterns are
    # escape-aware.
    pat = re.compile(
        r"""\{\s*
            id:\s*'(?P<id>\d+)',\s*
            start:\s*'(?P<start>\d{4}-\d{2}-\d{2})[ T](?P<time>\d{2}:\d{2})[^']*',\s*
            title:\s*'(?P<title>(?:[^'\\]|\\.)*)',\s*
            venue:\s*'(?P<venue>(?:[^'\\]|\\.)*)',""",
        re.X | re.S,
    )

    shows: list[dict] = []
    seen: set[str] = set()
    for m in pat.finditer(html):
        ev_id = m.group("id")
        if ev_id in seen:
            continue
        seen.add(ev_id)
        venue = strip_tags(_unescape_js(m.group("venue"))) or "Belly Up"
        event_url = event_urls.get(ev_id)
        # Constructed pattern works even without a list link (verified:
        # the venue redirects /calendar/<id>/ to the event page).
        fallback_url = f"https://bellyup.com/calendar/{ev_id}/"
        shows.append(
            {
                "id": f"bellyup:{ev_id}",
                "source": "bellyup",
                "title": _unescape_js(m.group("title")).strip(),
                "venue": venue,
                "date": m.group("start"),
                "show_time": m.group("time"),
                "doors_time": None,
                "age_limit": None,
                "event_url": event_url,
                "ticket_url": event_url or fallback_url,  # until deep scan
                "ticket_kind": "event_page",  # upgraded to "direct" by deep scan
                "band_url": None,
                "venue_url": _venue_url(venue),
                "timezone": "America/Los_Angeles",
            }
        )

    return shows
