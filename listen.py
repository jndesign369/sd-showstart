"""Add cached Bandcamp song links, falling back to MusicBrainz Spotify artists.

Background-only: the browser never contacts either service until a link is
clicked. Use only URLs supplied by MusicBrainz or Bandcamp, never guessed slugs.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from enrich import ROOT, USER_AGENT, load_json, write_json

CACHE_PATH = ROOT / "data" / "listen_cache.json"
SELECTION = "catalog-order-first-streamable-v1"


def bandcamp_url(value, base=""):
    if not isinstance(value, str) or re.search(r"[\s\\]", value):
        return None
    try:
        parsed = urlsplit(urljoin(base, value))
        if (parsed.scheme not in ("http", "https") or parsed.username or parsed.password
                or parsed.port not in (None, 80, 443)
                or not re.fullmatch(r"[a-z0-9-]+\.bandcamp\.com", parsed.hostname or "")):
            return None
        return "https://" + parsed.hostname + parsed.path
    except ValueError:
        return None


def spotify_url(value):
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?artist/([A-Za-z0-9]{22})/?(?:\?[^#\s]*)?",
        value)
    return "https://open.spotify.com/artist/" + match[1] if match else None


def music_links(detail):
    bandcamp, spotify = None, None
    for relation in detail.get("relations", []):
        if relation.get("ended") or relation.get("end"):
            continue
        value = relation.get("url", {}).get("resource")
        bandcamp = bandcamp or bandcamp_url(value)
        spotify = spotify or spotify_url(value)
    return bandcamp, spotify


class BandcampPage(HTMLParser):
    """Read public player data and the artist's ordered music grid only."""
    def __init__(self, html, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.tralbum = {}
        self.releases = []
        self.in_item = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-tralbum"):
            try:
                value = json.loads(attrs["data-tralbum"])
                if isinstance(value, dict):
                    self.tralbum = value
            except (TypeError, ValueError):
                pass
        if tag == "li":
            self.in_item = bool(attrs.get("data-item-id"))
        if tag == "a" and self.in_item:
            url = bandcamp_url(attrs.get("href"), self.url)
            if (url and urlsplit(url).hostname == urlsplit(self.url).hostname
                    and re.fullmatch(r"/(?:album|track)/[^/]+", urlsplit(url).path)
                    and url not in self.releases):
                self.releases.append(url)

    def handle_endtag(self, tag):
        if tag == "li":
            self.in_item = False

    def song(self):
        for track in self.tralbum.get("trackinfo") or []:
            # A pre-order can list unreleased tracks with no playable file.
            if (not isinstance(track, dict) or not isinstance(track.get("file"), dict)
                    or not any(track["file"].values())
                    or track.get("streaming") == 0 or track.get("private")
                    or track.get("is_draft") or track.get("is_capped")):
                continue
            url = bandcamp_url(track.get("title_link"), self.url)
            if (url and urlsplit(url).hostname == urlsplit(self.url).hostname
                    and re.fullmatch(r"/track/[^/]+", urlsplit(url).path)):
                return {"listen_url": url, "listen_service": "Bandcamp",
                        "listen_title": track.get("title") or "",
                        "release_url": self.url}
        return None


class Bandcamp:
    def __init__(self, cache, *, online=False, session=None, now=None,
                 sleep=time.sleep, max_requests=900):
        self.cache = cache.setdefault("artists", {})
        self.online = online
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.now = now or datetime.now(timezone.utc)
        self.sleep = sleep
        self.remaining = max(0, int(max_requests))
        self.requests_made = 0
        self.last_request = None
        self.paused = False
        self.error = None

    def page(self, url):
        # Redirect manually, so a bad link cannot redirect the worker to a
        # private address or silently leave Bandcamp. No bypasses or proxies.
        for _ in range(4):
            url = bandcamp_url(url)
            if not url or not self.online or self.remaining <= 0 or self.paused:
                return None
            if self.last_request is not None:
                self.sleep(max(0, 1.0 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            self.remaining -= 1
            self.requests_made += 1
            try:
                response = self.session.get(url, timeout=20, allow_redirects=False)
            except requests.RequestException:
                self.error = "network_error"
                return None
            if response.status_code in (429, 503):
                self.paused = True
                self.error = "service_paused_" + str(response.status_code)
                return None
            if response.status_code in (301, 302, 303, 307, 308):
                url = bandcamp_url(response.headers.get("Location"), url)
                continue
            if response.status_code != 200:
                self.error = "http_" + str(response.status_code)
                return None
            return BandcampPage(response.text, url)
        self.error = "too_many_redirects"
        return None

    def resolve(self, source):
        source = bandcamp_url(source)
        if not source:
            return None
        cached = self.cache.get(source) or {}
        fresh = False
        try:
            age = self.now - datetime.fromisoformat(cached["checked_at"])
            ttl = 7 if cached.get("result") else 1
            fresh = timedelta(0) <= age < timedelta(days=ttl)
        except (KeyError, ValueError, TypeError):
            pass
        if cached.get("selection") == SELECTION and fresh:
            return cached.get("result")
        if not self.online or self.remaining <= 0 or self.paused:
            # Offline runs never invent/revalidate destinations.
            return None
        self.error = None
        path = urlsplit(source).path
        catalog = source if re.match(r"/(?:album|track)/", path) else urljoin(source, "/music")
        page = self.page(catalog)
        result = page.song() if page else None
        if page and not result:
            # Bandcamp's catalog ordering is artist-controlled, generally
            # newest first. Bound traversal; never crawl the whole discography.
            for release in page.releases[:4]:
                self.error = None
                release_page = self.page(release)
                result = release_page.song() if release_page else None
                if self.error in ("http_404", "http_410"):
                    continue
                if result or self.error or self.paused or self.remaining <= 0:
                    break
        # Do not cache an unattempted/budget-limited or globally paused miss.
        if result or (not self.paused and self.remaining > 0):
            self.cache[source] = {
                "checked_at": self.now.isoformat(), "selection": SELECTION,
                "result": result, "reason": self.error or (None if result else "no_streamable_track")}
        return result


def add_listen(shows, mb_cache, resolver):
    results = {}
    for show in shows:
        for artist in show.get("artists", []):
            mbid = artist.get("mbid")
            if mbid not in results:
                key = "/artist/" + str(mbid) + '?' + json.dumps({"inc": "url-rels"}, sort_keys=True)
                detail = mb_cache.get("responses", {}).get(key, {}).get("data", {})
                bandcamp, spotify = music_links(detail)
                result = resolver.resolve(bandcamp) if bandcamp else None
                if not result and spotify:
                    result = {"listen_url": spotify, "listen_service": "Spotify"}
                results[mbid] = result
            for key in ("listen_url", "listen_service", "listen_title"):
                artist.pop(key, None)
                if results[mbid] and results[mbid].get(key):
                    artist[key] = results[mbid][key]
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--max-requests", type=int, default=900)
    parser.add_argument("--shows", type=Path, default=ROOT / "shows.json")
    args = parser.parse_args()
    data = load_json(args.shows, {})
    if not data.get("shows"):
        parser.error("No shows found")
    cache = load_json(CACHE_PATH, {"artists": {}})
    resolver = Bandcamp(cache, online=not args.offline, max_requests=args.max_requests)
    try:
        results = add_listen(data["shows"], load_json(ROOT / "data" / "artist_cache.json", {}),
                             resolver)
    finally:
        # Preserve completed lookups even if interrupted; never deploy caches.
        if not args.offline:
            write_json(CACHE_PATH, cache)
    args.shows.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    counts = {s: sum(bool(r and r.get("listen_service") == s) for r in results.values())
              for s in ("Bandcamp", "Spotify")}
    print(f"Listen links: {counts}; {resolver.requests_made} Bandcamp requests", flush=True)
    if resolver.paused:
        print("Bandcamp paused; remaining artists use Spotify where available.", flush=True)


if __name__ == "__main__":
    main()
