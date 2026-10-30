"""The Rady Shell at Jacobs Park calendar scraper.

theshell.org/performances/list/ is an Angular page: each date is an
<article> whose header gives the date (no year), containing one or more
.occurrence-teaser blocks with title, start time and a buy button
(Ticketmaster / Eventbrite / venue reservation). Rendered in a headless
browser.

Non-music community events (yoga, fitness classes) are filtered out.
"""
from __future__ import annotations

import re

from .common import Browser, infer_year, parse_clock

PAGE_URL = "https://www.theshell.org/performances/list/"

VENUE_URLS = {
    "the rady shell at jacobs park": "https://theshell.org/",
    "jacobs music center": "https://www.sandiegosymphony.org/",
}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Community fitness/wellness classes on the venue calendar, not music.
EXCLUDE_TITLE = re.compile(r"\byoga\b|\bfitness\b|\bworkout\b|\bclass\b", re.I)


async def scrape(browser: Browser) -> list[dict]:
    page = await browser.page()
    try:
        # networkidle never settles on this Angular app; wait for the list.
        await page.goto(PAGE_URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_selector(".occurrence-teaser", timeout=30000)
        await page.wait_for_timeout(2000)

        cards = await page.evaluate(
            """() => {
                const out = [];
                for (const art of document.querySelectorAll('.occurrence-list article')) {
                    const head = (art.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
                    for (const t of art.querySelectorAll('.occurrence-teaser')) {
                        const title = t.querySelector('h2 a');
                        const time = t.querySelector('.content p');
                        const buy = [...t.querySelectorAll('a')]
                            .find(a => /buy|reserve/i.test(a.innerText || ''));
                        const details = t.querySelector('h2 a');
                        out.push({
                            head,
                            title: title ? title.textContent.trim() : null,
                            timeText: time ? time.textContent.trim() : null,
                            buy: buy ? buy.href : null,
                            details: details ? details.href : null,
                        });
                    }
                }
                return out;
            }"""
        )
    finally:
        await page.close()

    shows = cards_to_shows(cards)
    if not shows:
        raise RuntimeError(
            "Rady Shell: no performances parsed (off-season or layout changed?)"
        )
    return shows


def cards_to_shows(cards: list[dict]) -> list[dict]:
    shows: list[dict] = []
    for card in cards:
        title = card.get("title")
        if not title or EXCLUDE_TITLE.search(title):
            continue

        # Date comes from the article header lines: ["TUESDAY", "Oct 27", ...]
        head = card.get("head") or []
        dm = None
        for i, line in enumerate(head):
            m = re.match(r"^([A-Z][a-z]{2})[a-z]*\s+(\d{1,2})$", line)
            if m:
                dm = m
                break
        if not dm:
            continue
        month, day = MONTHS.get(dm.group(1)[:3].lower()), int(dm.group(2))
        if not month:
            continue
        year = infer_year(month, day)

        show_time = None
        venue = None
        if card.get("timeText"):
            # Line looks like "8:00 pm The Rady Shell at Jacobs Park".
            # The venue is only ever taken from this source text; a card
            # without it is skipped rather than assumed to be the Shell.
            tm = re.search(
                r"(\d{1,2}:\d{2})\s*([ap]\.?m\.?)\s*(\S.*)$",
                card["timeText"],
                re.I | re.S,
            )
            if tm:
                show_time = parse_clock(
                    tm.group(1) + tm.group(2).replace(".", "")
                )
                venue = " ".join(tm.group(3).split())
        if not venue:
            continue

        buy = card.get("buy")
        # Keep any buy/reserve button (Ticketmaster, Eventbrite, the
        # symphony's own ticketing, ...); "More details" is never a buy.
        ticket_url = buy or None
        ticket_kind = "direct" if buy else None

        details = card.get("details")
        event_url = f"https://www.theshell.org{details}" if details and details.startswith("/") else details

        shows.append(
            {
                "id": f"radyshell:{year}{month:02d}{day:02d}:{title[:30]}",
                "source": "radyshell",
                "title": title,
                "venue": venue,
                "date": f"{year}-{month:02d}-{day:02d}",
                "show_time": show_time,
                "doors_time": None,
                "age_limit": None,
                "event_url": event_url,
                "ticket_url": ticket_url,
                "ticket_kind": ticket_kind,
                "sold_out": False,
                "band_url": None,
                "venue_url": VENUE_URLS.get(venue.lower(), "https://theshell.org/"),
                "timezone": "America/Los_Angeles",
            }
        )

    return shows