"""Link performers to MusicBrainz "official homepage" results.

Automatic acceptance, no approval gate: the first active official-homepage
relationship on MusicBrainz's highest-ranked search result becomes the link.
No homepage returned means the artist name stays plain text. Results are
cached so routine updates make few or no API requests.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parent
API = "https://musicbrainz.org/ws/2"
CACHE_PATH = ROOT / "data" / "artist_cache.json"
USER_AGENT = "SanDiegoShows/1.0 (personal noncommercial concert listing; github.com/jndesign369)"
DEFAULTS = {"max_requests": 400, "cache_days": 30}


def public_homepage(value):
    """Accept only well-formed public http(s) URLs."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not re.match(r"https?://", url, re.I) or " " in url:
        return None
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (not host or "." not in host or host == "localhost"
            or host.endswith((".localhost", ".local", ".internal", ".example", ".invalid", ".test"))):
        return None
    return url


def load_json(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


class MusicBrainz:
    def __init__(self, cache, *, online=False, max_requests=DEFAULTS["max_requests"],
                 cache_days=DEFAULTS["cache_days"], session=None, now=None,
                 sleep=time.sleep):
        self.cache = cache.setdefault("responses", {})
        self.online = online
        self.remaining = max(0, min(1000, int(max_requests)))
        self.cache_days = max(1, min(90, int(cache_days)))
        self.session = session or requests.Session()
        if getattr(self.session, "headers", None) is not None:
            self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.now = now or datetime.now(timezone.utc)
        self.sleep = sleep
        self.last_request = None
        self.requests_made = 0
        self.paused = False
        self.last_error = None

    def get(self, path, params):
        key = path + "?" + json.dumps(params, sort_keys=True)
        cached = self.cache.get(key)
        if isinstance(cached, dict):
            try:
                stamp = datetime.fromisoformat(cached["fetched_at"])
                age = self.now - stamp
                if timedelta(0) <= age < timedelta(days=self.cache_days):
                    return cached["data"], None
            except (KeyError, ValueError, TypeError):
                pass
        if not self.online:
            return None, "not_cached_or_expired"
        if self.remaining <= 0 or self.paused:
            return None, self.last_error or "request_budget_exhausted"
        if self.last_request is not None:
            elapsed = time.monotonic() - self.last_request
            if elapsed < 1.1:
                self.sleep(1.1 - elapsed)
        self.last_request = time.monotonic()
        try:
            response = self.session.get(API + path, params=params, timeout=60)
        except requests.RequestException as error:
            return None, str(error)
        finally:
            self.remaining -= 1
            self.requests_made += 1
        if response.status_code in (503, 429):
            # Brief outages are common; back off and retry a few times
            # before pausing the run.
            for attempt in range(3):
                self.sleep(5 * (attempt + 1))
                try:
                    response = self.session.get(API + path, params=params, timeout=60)
                except requests.RequestException:
                    continue
                self.remaining -= 1
                self.requests_made += 1
                if response.status_code not in (503, 429):
                    break
            else:
                self.paused = True
                self.last_error = ("rate_limited" if response.status_code == 429
                                   else "service_unavailable")
                return None, self.last_error
        if response.status_code >= 500:
            return None, f"http_{response.status_code}"
        if response.status_code >= 400:
            return None, f"http_{response.status_code}"
        data = response.json()
        self.cache[key] = {"fetched_at": self.now.isoformat(), "data": data}
        return data, None

    def search(self, name):
        escaped = re.sub(r'([\\"])', r"\\\1", name)
        return self.get("/artist/", {"query": 'artist:"' + escaped + '"', "limit": 10})

    def artist(self, mbid):
        return self.get("/artist/" + mbid, {"inc": "url-rels"})

    def homepage(self, artist):
        for relation in artist.get("relations", []):
            if relation.get("type") != "official homepage" or relation.get("ended") is True:
                continue
            if relation.get("end"):
                continue
            url = public_homepage(relation.get("url", {}).get("resource"))
            if url:
                return url
        return None


def enrich(shows, client):
    results = {}
    for show in shows:
        artists = []
        for name in show.get("performers", []):
            key = name
            if key not in results:
                results[key] = lookup(name, client)
            record = results[key]
            artist = {"name": name}
            if record.get("mbid"):
                artist["mbid"] = record["mbid"]
            if record.get("official_url"):
                artist["official_url"] = record["official_url"]
            artists.append(artist)
        show["artists"] = artists
    return results


def lookup(name, client):
    data, error = client.search(name)
    if error:
        return {"reason": error}
    matches = (data or {}).get("artists") or []
    if not matches:
        return {"reason": "no_artist_match"}
    best = matches[0]
    detail, error = client.artist(best["id"])
    if error:
        return {"mbid": best["id"], "reason": error}
    url = client.homepage(detail or {})
    record = {"mbid": best["id"], "artist_name": best.get("name")}
    if url:
        record["official_url"] = url
    else:
        record["reason"] = "no_active_official_homepage"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="use cached responses only; no API requests")
    parser.add_argument("--max-requests", type=int, default=DEFAULTS["max_requests"])
    parser.add_argument("--shows", default=str(ROOT / "shows.json"))
    args = parser.parse_args()

    data = load_json(Path(args.shows), {})
    shows = data.get("shows") or []
    if not shows:
        print("No shows found in shows.json", file=sys.stderr)
        return 1

    cache = load_json(CACHE_PATH, {"responses": {}})
    client = MusicBrainz(cache, online=not args.offline, max_requests=args.max_requests)
    results = enrich(shows, client)

    linked = sum(1 for r in results.values() if r.get("official_url"))
    print(f"Artists: {len(results)} unique names, {linked} with homepages, "
          f"{client.requests_made} API requests")
    if not args.offline and client.requests_made:
        write_json(CACHE_PATH, cache)

    reasons = {}
    for record in results.values():
        if record.get("reason"):
            reasons[record["reason"]] = reasons.get(record["reason"], 0) + 1
    if reasons:
        print("Unlinked:", json.dumps(reasons, sort_keys=True))

    Path(args.shows).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"updated {args.shows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
