"""Collect upcoming San Diego concerts from ConcertsSD (The List: San Diego).

One source, two page requests per run, with the crawl delay their robots.txt
asks for. Only facts are kept: performer names, dates, and venues. No times,
prices, ticket links, commentary, artwork, or page design are copied.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent
INDEX_URL = "https://concertssd.com/index.html"
VENUES_URL = "https://concertssd.com/by-venue.html"
CRAWL_DELAY = 10  # seconds; concertssd.com robots.txt Crawl-delay: 10
USER_AGENT = "SanDiegoShows/1.0 (personal noncommercial concert listing; github.com/jndesign369)"
LA = ZoneInfo("America/Los_Angeles")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

VENUE_RE = re.compile(r'<li><a name="[^"]*"></a><b>([^<]+)</b></li>')
EVENT_RE = re.compile(
    r'<u><b><a href="week-(\d+)\.html">([A-Za-z]{3}) (\d{1,2})</a></b></u>(.*?)</li>',
    re.S)
PERFORMER_RE = re.compile(r'<u><a href="by-band\.html#[^"]*">([^<]+)</a></u>')
UPDATED_RE = re.compile(r"\(updated ([^)]+)\)")
WEEK_RE = re.compile(r'<a href="week-(\d+)\.html">([A-Za-z]{3}) (\d{1,2}) - [A-Za-z]{3} \d{1,2}</a>')


def today() -> date:
    return datetime_now().date()


def datetime_now():
    from datetime import datetime
    return datetime.now(LA)


def parse_weeks(index_html: str):
    """Map week page numbers to their start month/day from the homepage nav."""
    weeks = {}
    for match in WEEK_RE.finditer(index_html):
        weeks[int(match.group(1))] = (MONTHS.get(match.group(2)), int(match.group(3)))
    return weeks


def resolve_date(month_text: str, day_text: str, today: date, week_start=None):
    """ConcertsSD lists dates without a year.

    Prefer the week's own date range from the homepage nav: an event in the
    week "Jul 21 - Jul 27" gets that week's year, which may be next year.
    Without a week, fall back to the nearest upcoming year.
    """
    month = MONTHS.get(month_text)
    if not month:
        return None
    day = int(day_text)
    if week_start:
        week_month, week_day = week_start
        week_year = today.year
        try:
            start = date(week_year, week_month, week_day)
        except ValueError:
            start = None
        if start is None or start < today - timedelta(days=14):
            week_year += 1
        year = week_year
        # A week spanning New Year's: "Dec 28 - Jan 3" events in January.
        if month < (week_month or month):
            year += 1
        try:
            return date(year, month, day)
        except ValueError:
            return None
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        # Allow a few days of lag in the source; anything older is history.
        if candidate >= today - timedelta(days=3):
            return candidate
    return None


def split_venue(raw: str):
    """'Belly Up Tavern, Solana Beach' -> ('Belly Up Tavern', 'Solana Beach')."""
    name, _, city = html.unescape(raw).rpartition(",")
    city = city.strip()
    if city == "SD":
        city = "San Diego"
    return name.strip(), city


def parse_venues(page_html: str, today: date, weeks=None):
    venues = []
    weeks = weeks or {}
    matches = list(VENUE_RE.finditer(page_html))
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(page_html)
        block = page_html[match.end():block_end]
        venue, city = split_venue(match.group(1))
        events = []
        for event in EVENT_RE.finditer(block):
            performers = [html.unescape(p).strip() for p in PERFORMER_RE.findall(event.group(4))]
            performers = [p for p in performers if p]
            day = resolve_date(event.group(2), event.group(3), today,
                               weeks.get(int(event.group(1))))
            if day and performers and day >= today:
                events.append({"date": day.isoformat(), "performers": performers})
        if events:
            venues.append({"venue": venue, "city": city, "events": events})
    return venues


def dedupe(venues):
    seen = set()
    shows = []
    for entry in venues:
        for event in entry["events"]:
            key = (event["date"], entry["venue"], tuple(event["performers"]))
            if key in seen:
                continue
            seen.add(key)
            shows.append({
                "id": f"{slug(entry['venue'])}:{event['date']}"
                      f":{slug(event['performers'][0])}",
                "date": event["date"],
                "venue": entry["venue"],
                "city": entry["city"],
                "performers": event["performers"],
                "artists": [],
            })
    shows.sort(key=lambda s: (s["date"], s["venue"]))
    return shows


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def load_json(path: Path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def fetch(session: requests.Session, url: str):
    response = session.get(url, timeout=60)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def collect(*, online=True, html_pair=None, sleep=time.sleep):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    if online:
        index_html = fetch(session, INDEX_URL)
        sleep(CRAWL_DELAY)
        venues_html = fetch(session, VENUES_URL)
    else:
        index_html, venues_html = html_pair
    updated = UPDATED_RE.search(html.unescape(index_html))
    weeks = parse_weeks(html.unescape(index_html))
    shows = dedupe(parse_venues(venues_html, today(), weeks))
    links = load_json(ROOT / "venue_links.json", {})
    for show in shows:
        keys = [f"{show['venue']}, {show['city']}"]
        if show["city"] == "San Diego":
            keys.append(f"{show['venue']}, SD")
        show["venue_url"] = next((links[k] for k in keys if k in links), None)
    return {
        "generated_at": datetime_now().isoformat(timespec="seconds"),
        "source": {
            "name": "The List: San Diego (ConcertsSD)",
            "url": "https://concertssd.com/",
            "updated": updated.group(1).strip() if updated else None,
        },
        "shows": shows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="parse the saved _inspect pages; no network")
    parser.add_argument("--output", default=str(ROOT / "shows.json"))
    args = parser.parse_args()

    if args.offline:
        base = ROOT / "fixtures"
        index_html = (base / "index.html").read_text(encoding="utf-8")
        venues_html = (base / "by-venue.html").read_text(encoding="utf-8")
        data = collect(online=False, html_pair=(index_html, venues_html), sleep=lambda _s: None)
    else:
        data = collect()

    shows = data["shows"]
    print(f"{len(shows)} upcoming shows from "
          f"{len({s['venue'] for s in shows})} venues; "
          f"source updated: {data['source']['updated']}")
    if not shows:
        print("No shows parsed - not overwriting shows.json", file=sys.stderr)
        return 1
    Path(args.output).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
