"""Shared helpers for all venue scrapers."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LA = ZoneInfo("America/Los_Angeles")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def http_get(url: str, retries: int = 3, timeout: int = 30) -> str:
    """Fetch a page as text, retrying transient failures."""
    last = None
    for _ in range(retries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
                timeout=timeout,
            )
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:  # network hiccup, 5xx, timeout
            last = e
    raise RuntimeError(f"GET failed after {retries} tries: {url} ({last})")


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def parse_clock(s: str) -> str | None:
    """'7:30PM' / '7pm' / '19:30' -> '19:30' (24h) or None."""
    if not s:
        return None
    s = s.strip().lower().replace(".", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), m.group(2) or "00", m.group(3)
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h <= 23):
        return None
    return f"{h:02d}:{mi}"


def iso_to_pt(iso: str) -> datetime:
    """Parse an ISO datetime (possibly Z-suffixed) and convert to Pacific."""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LA)


def infer_year(month: int, day: int, today: datetime | None = None) -> int:
    """Best-guess year for a 'Oct 18' style date: current year unless that
    date is well in the past, then next year. Calendars rarely list >1yr out."""
    today = today or datetime.now(LA)
    try:
        candidate = today.replace(year=today.year, month=month, day=day)
    except ValueError:  # Feb 29 in a non-leap year, etc.
        return today.year
    if candidate.date() < today.date() - __import__("datetime").timedelta(days=45):
        return today.year + 1
    return today.year


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def dedupe_key(show: dict) -> tuple:
    """Two rows are the same show when band, venue, date AND time match;
    the same act playing twice in one night stays as two rows."""
    return (
        show["venue"].lower(),
        show["date"],
        show.get("show_time") or "",
        slugify(show["title"]),
    )


# ---------------------------------------------------------------- persistence
# Per-source files in data/ keep the last successful scrape. If a venue's
# page fails (site redesign, network, bot wall), we keep showing the last
# good data instead of erasing the site's content.


def source_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load_source(name: str) -> dict | None:
    p = source_path(name)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def save_source(name: str, shows: list[dict], ok: bool) -> dict:
    """Write data/<name>.json. On failure, keep previous shows untouched."""
    prev = load_source(name) or {}
    now = datetime.now(LA).isoformat(timespec="seconds")
    if ok:
        payload = {
            "status": "ok",
            "last_run": now,
            "last_success": now,
            "shows": shows,
        }
    else:
        payload = {
            "status": "failed",
            "last_run": now,
            "last_success": prev.get("last_success"),
            "shows": prev.get("shows", []),
        }
    source_path(name).write_text(json.dumps(payload, indent=1))
    return payload


# ---------------------------------------------------------------- playwright


class Browser:
    """A single shared headless Chromium for the JS-rendered sources."""

    def __init__(self):
        self._pw = None
        self._browser = None

    async def start(self):
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)

    async def page(self):
        ctx = await self._browser.new_context(
            user_agent=UA,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        return await ctx.new_page()

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
