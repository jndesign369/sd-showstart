"""Quartyard (East Village, San Diego) calendar scraper.

quartyardsd.com/events/ is a WordPress/Elementor page whose event cards
are rendered server-side but need JS to finish, so it is loaded in a
headless browser. Cards are located via their /event/ links; each card's
text block has the pattern: Title / Date: <weekday>, <Mon> <day> /
Time: <start> - <end> / Age: <limit> / Buy Tickets / View Details.
"""
from __future__ import annotations

import re

from .common import Browser, infer_year, parse_clock

PAGE_URL = "https://quartyardsd.com/events/"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

TICKET_HREF = re.compile(
    r"eventbrite|eventim|dice\.fm|ticketmaster|\.axs\.|ticketweb|showclix|zeffy"
)

# Clearly non-music listings on the venue calendar (comedy nights,
# trivia, bingo parties, ...). The site is a music listings site; extend
# as needed.
EXCLUDE_TITLE = re.compile(r"\bcomedy\b|\btrivia\b|\bbingos?\b|\byoga\b|\bfitness\b", re.I)


async def scrape(browser: Browser) -> list[dict]:
    page = await browser.page()
    try:
        await page.goto(PAGE_URL, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_selector('a[href*="/event/"]', timeout=30000)
        await page.wait_for_timeout(1500)

        cards = await page.evaluate(
            """() => {
                const out = [];
                const seen = new Set();
                for (const a of document.querySelectorAll('a[href*="/event/"]')) {
                    const href = a.href.split('?')[0];
                    if (seen.has(href)) continue;
                    seen.add(href);
                    // Climb to the smallest ancestor that looks like a full card.
                    let el = a;
                    while (el && el !== document.body) {
                        if (el.textContent.includes('Date:') && el.textContent.includes('Time:')) break;
                        el = el.parentElement;
                    }
                    if (!el || el === document.body) continue;
                    const lines = el.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                    const links = [...el.querySelectorAll('a')]
                        .filter(x => x.href && !x.href.includes('quartyardsd.com'))
                        .map(x => ({href: x.href, text: (x.innerText || '').trim()}));
                    const internal = [...el.querySelectorAll('a[href*="/event/"]')].map(x => x.href.split('?')[0]);
                    out.push({lines, ticketLinks: links, eventLinks: internal});
                }
                return out;
            }"""
        )
    finally:
        await page.close()

    shows: list[dict] = []
    for card in cards:
        lines = card.get("lines") or []
        try:
            date_idx = next(i for i, l in enumerate(lines) if l.startswith("Date:"))
        except StopIteration:
            continue

        title = lines[date_idx - 1] if date_idx > 0 else None
        if EXCLUDE_TITLE.search(title or ""):
            continue
        date_raw = lines[date_idx][len("Date:"):].strip()  # e.g. "Sun, Oct 18"
        dm = re.search(r"([A-Za-z]{3})[a-z]*\s+(\d{1,2})", date_raw)
        if not (title and dm):
            continue
        month, day = MONTHS.get(dm.group(1)[:3].lower()), int(dm.group(2))
        if not month:
            continue
        year = infer_year(month, day)

        show_time = doors_time = None
        for l in lines:
            if l.startswith("Time:"):
                tm = re.search(r"(\d{1,2}(?::\d{2})?\s*[ap]m)", l[len("Time:"):], re.I)
                if tm:
                    show_time = parse_clock(tm.group(1))
                break

        age = next(
            (l[len("Age:"):].strip() for l in lines if l.startswith("Age:")), None
        )

        ticket_links = card.get("ticketLinks") or []
        ticket_url = None
        # Prefer the card's "Buy Tickets" button (some events link straight
        # to a promoter or tour site rather than a ticketing platform).
        for link in ticket_links:
            if re.search(r"\bbuy\b", link.get("text") or "", re.I):
                ticket_url = link["href"]
                break
        if not ticket_url:
            ticket_url = next(
                (u["href"] for u in ticket_links if TICKET_HREF.search(u["href"])), None
            )
        event_links = card.get("eventLinks") or []

        shows.append(
            {
                "id": f"quartyard:{year}{month:02d}{day:02d}:{title[:40]}",
                "source": "quartyard",
                "title": title,
                "venue": "Quartyard",
                "date": f"{year}-{month:02d}-{day:02d}",
                "show_time": show_time,
                "doors_time": doors_time,
                "age_limit": age,
                "event_url": event_links[0] if event_links else None,
                "ticket_url": ticket_url,
                "ticket_kind": "direct" if ticket_url else None,
                "band_url": None,
                "venue_url": "https://quartyardsd.com/",
                "timezone": "America/Los_Angeles",
            }
        )

    if not shows:
        raise RuntimeError("Quartyard: no event cards parsed (layout changed?)")
    return shows
