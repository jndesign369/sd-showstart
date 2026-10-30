"""Humphreys Concerts by the Bay (Shelter Island) schedule scraper.

humphreysconcerts.com/schedule.cfm lists the full season as rows; each
row embeds an AddEvent calendar widget whose spans carry the exact start
and end datetimes (with year), plus a Ticketmaster purchase link for the
show. The page needs JavaScript, so it is rendered in a headless browser.
"""
from __future__ import annotations

import re
from datetime import datetime

from .common import Browser

PAGE_URL = "https://www.humphreysconcerts.com/schedule.cfm"

# Non-music events (comedy nights) are out of scope for a music site.
NON_MUSIC = re.compile(r"\bcomedy\b|\bcomedian\b|stand-?up", re.I)

START_SPAN = re.compile(
    r'<span class="start atc_node notranslate">\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2} [AP]M)'
)
TITLE_SPAN = re.compile(r'<span class="title atc_node notranslate">([^<]+)')


async def scrape(browser: Browser) -> list[dict]:
    page = await browser.page()
    try:
        await page.goto(PAGE_URL, timeout=45000, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        cards = await page.evaluate(
            """() => {
                const out = [];
                for (const w of document.querySelectorAll('.addeventatc')) {
                    const get = (cls) => {
                        const s = w.querySelector('span.' + cls);
                        return s ? s.textContent.trim() : null;
                    };
                    // Bounded to this show's own row: the first ancestor
                    // div.row is the per-event row; never climb to the
                    // schedule container (a link-less row must not borrow
                    // a neighboring show's purchase link).
                    const row = w.closest('div.row');
                    if (!row) continue;
                    const tm = row.querySelector('a[href*="ticketmaster.com/event"]');
                    const text = row.innerText || '';
                    out.push({
                        start: get('start'),
                        end: get('end'),
                        title: get('title'),
                        description: get('description'),
                        ticket: tm ? tm.href : null,
                        soldOut: /SOLD OUT/i.test(text),
                    });
                }
                return out;
            }"""
        )
    finally:
        await page.close()

    shows = cards_to_shows(cards)
    if not shows:
        raise RuntimeError("Humphreys: no schedule rows parsed (layout changed?)")
    return shows


def cards_to_shows(cards: list[dict]) -> list[dict]:
    """Convert rendered row data to shows. A row without its own
    Ticketmaster link gets no link — never a neighboring row's."""
    shows: list[dict] = []
    for c in cards:
        start, title = c.get("start"), c.get("title")
        if not (start and title):
            continue
        # Comedy and other non-music events are out of scope.
        if NON_MUSIC.search(title) or NON_MUSIC.search(c.get("description") or ""):
            continue
        try:
            dt = datetime.strptime(start, "%m/%d/%Y %I:%M %p")
        except ValueError:
            continue
        shows.append(
            {
                "id": f"humphreys:{dt.date().isoformat()}:{title[:30]}",
                "source": "humphreys",
                "title": title.strip(),
                "venue": "Humphreys Concerts by the Bay",
                "date": dt.date().isoformat(),
                "show_time": dt.strftime("%H:%M"),
                "doors_time": None,
                "age_limit": None,
                "event_url": c.get("ticket"),
                "ticket_url": c.get("ticket"),
                "ticket_kind": "direct" if c.get("ticket") else None,
                "sold_out": bool(c.get("soldOut")),
                "band_url": None,
                "venue_url": "https://www.humphreysconcerts.com/",
                "timezone": "America/Los_Angeles",
            }
        )

    return shows
