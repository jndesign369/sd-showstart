"""Soda Bar (San Diego) calendar scraper.

sodabarmusic.com renders its show list through Dice's event-list widget,
so the page is loaded in a headless browser. The widget lazy-loads cards,
so the page is scrolled until the card count stops growing. Each rendered
event card embeds schema.org JSON-LD with exact start/door times (ISO,
timezone-aware), which is more reliable than parsing the displayed text.

The widget also lists shows Soda Bar promotes at OTHER venues (Casbah,
Quartyard, ...). Those are dropped here: Soda Bar's ticket policy and
website apply only to its own shows, and the other venues have their own
collectors. Set INCLUDE_ALL_VENUES = True to keep them.
"""
from __future__ import annotations

import json

from .common import Browser, iso_to_pt

PAGE_URL = "https://sodabarmusic.com/"
INCLUDE_ALL_VENUES = False


def _first_jsonld(script_texts: list[str]) -> dict | None:
    for t in script_texts:
        try:
            data = json.loads(t)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") in ("MusicEvent", "Event"):
                return item
    return None


async def scrape(browser: Browser) -> list[dict]:
    page = await browser.page()
    try:
        await page.goto(PAGE_URL, timeout=45000, wait_until="domcontentloaded")
        # Wait for the Dice widget to finish rendering its cards.
        await page.wait_for_selector("#dice-event-list-widget article", timeout=30000)
        await page.wait_for_timeout(2500)

        # The widget lazy-loads cards: scroll until the count is stable.
        prev = -1
        while True:
            n = await page.locator("#dice-event-list-widget article").count()
            if n == prev:
                break
            prev = n
            await page.evaluate(
                "() => document.querySelector('#dice-event-list-widget')"
                ".scrollIntoView({block:'end'})"
            )
            await page.wait_for_timeout(2000)

        cards = await page.evaluate(
            """() => {
                const out = [];
                for (const art of document.querySelectorAll('#dice-event-list-widget article')) {
                    const lines = art.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                    const ld = [...art.querySelectorAll('script[type="application/ld+json"]')]
                        .map(s => s.textContent);
                    const ticket = art.querySelector('a.dice_book-now');
                    out.push({lines, ld, ticket: ticket ? ticket.href : null});
                }
                return out;
            }"""
        )
    finally:
        await page.close()

    shows: list[dict] = []
    for card in cards:
        ld = _first_jsonld(card.get("ld") or [])
        if not ld:
            continue

        lines = card.get("lines") or []
        # Structure is: title, venue, city, date text, 'Buy now'.
        venue = lines[1] if len(lines) >= 3 and lines[1].lower() not in ("san diego",) else ""

        # Only Soda Bar's own shows (see module docstring).
        if not INCLUDE_ALL_VENUES and (venue or "").strip().lower() != "soda bar":
            continue

        start = iso_to_pt(ld["startDate"])
        doors = iso_to_pt(ld["doorTime"]) if ld.get("doorTime") else None
        event_url = ld.get("url") or card.get("ticket")

        shows.append(
            {
                "id": f"sodabar:{ld.get('@id') or ld.get('url') or start.isoformat()}",
                "source": "sodabar",
                "title": (ld.get("name") or "").strip(),
                "venue": venue or "Soda Bar",
                "date": start.date().isoformat(),
                "show_time": start.strftime("%H:%M"),
                "doors_time": doors.strftime("%H:%M") if doors else None,
                "age_limit": "21+",
                "event_url": event_url,
                "ticket_url": card.get("ticket") or event_url,
                "ticket_kind": "direct",  # Dice event page is the purchase page
                "band_url": None,
                "venue_url": "https://sodabarmusic.com/",
                "timezone": "America/Los_Angeles",
            }
        )

    if not shows:
        raise RuntimeError("Soda Bar: widget rendered but no events parsed")
    return shows
