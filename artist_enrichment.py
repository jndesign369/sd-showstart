"""Bounded, cached MusicBrainz enrichment; no browser-side API requests.

Accept MusicBrainz's active official-homepage relationships automatically.
Manual MBID records are optional corrections, not an approval gate.
"""
from __future__ import annotations

import argparse
import ipaddress
import html
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo

import requests

from artist_links import artist_key, http_url

ROOT = Path(__file__).resolve().parent
API = "https://musicbrainz.org/ws/2"
USER_AGENT = "SanDiegoShows/0.3.0 (https://github.com/jndesign369)"
LA = ZoneInfo("America/Los_Angeles")
DEFAULTS = {"enabled": True, "max_requests": 600, "cache_days": 30}


def load_json(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def valid_mbid(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value.lower()
    except (ValueError, TypeError, AttributeError):
        return False


def public_homepage(value):
    """Basic URL safety only; trust MusicBrainz's relationship classification."""
    url = http_url(value)
    if not url:
        return None
    parsed = urlsplit(url)
    host = parsed.hostname.lower().rstrip(".")
    if (host == "localhost"
            or host.endswith((".localhost", ".local", ".internal", ".example", ".invalid", ".test"))
            or "." not in host):
        return None
    try:
        if not ipaddress.ip_address(host).is_global:
            return None
    except ValueError:
        pass
    try:
        parsed.port  # reject malformed port strings
    except ValueError:
        return None
    return url


def exact_key(name):
    return artist_key(unicodedata.normalize("NFC", name))


def homepage_from_artist(artist):
    """Choose the first active safe homepage; multiple sites are not a blocker."""
    urls = homepage_urls(artist)
    return (urls[0], None) if urls else (None, "no_active_official_homepage")


def homepage_urls(artist):
    urls = []
    for relation in artist.get("relations", []):
        if relation.get("type") != "official homepage" or relation.get("ended") is True:
            continue
        if relation.get("end"):
            continue
        value = public_homepage(relation.get("url", {}).get("resource"))
        if value and value not in urls:
            urls.append(value)
    return urls


class MusicBrainz:
    def __init__(self, cache, *, online=False, max_requests=600, cache_days=30,
                 session=None, now=None, sleep=time.sleep, clock=time.monotonic,
                 max_retries=2, cache_path=None):
        self.cache = cache.setdefault("responses", {})
        self.online = online
        self.remaining = max(0, min(2000, int(max_requests)))
        self.cache_days = max(1, min(90, int(cache_days)))
        self.session = session or requests.Session()
        self.now = now or datetime.now(timezone.utc)
        self.sleep, self.clock = sleep, clock
        self.last_request = None
        self.stopped = False
        self.consecutive_errors = 0
        self.last_error = None
        self.requests_made = 0
        self.max_retries = max(0, min(2, max_retries))
        self.cache_path = cache_path
        self.user_agent = os.environ.get("MUSICBRAINZ_USER_AGENT", USER_AGENT)

    def get(self, path, params):
        key = path + "?" + json.dumps(params, sort_keys=True)
        cached = self.cache.get(key)
        if isinstance(cached, dict):
            try:
                stamp = datetime.fromisoformat(cached["fetched_at"])
                age = self.now - stamp
                if timedelta(0) <= age < timedelta(days=self.cache_days):
                    return cached["data"], stamp.astimezone(LA).date().isoformat(), None
            except (KeyError, ValueError, TypeError):
                pass
        if not self.online:
            return None, None, "not_cached_or_expired"
        if self.remaining <= 0:
            return None, None, "request_budget_exhausted"
        if self.stopped:
            return None, None, "service_paused_after_error"
        for attempt in range(self.max_retries + 1):
            if self.remaining <= 0:
                return None, None, "request_budget_exhausted"
            if self.last_request is not None:
                delay = 1.1 - (self.clock() - self.last_request)
                if delay > 0:
                    self.sleep(delay)
            self.remaining -= 1
            self.requests_made += 1
            self.last_request = self.clock()
            try:
                response = self.session.get(
                    API + path, params=dict(params, fmt="json"),
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                    timeout=(5, 20), allow_redirects=False,
                )
                if response.status_code == 404:
                    return None, None, "artist_not_found"
                if response.status_code in (429, 502, 503, 504) and attempt < self.max_retries:
                    raw = response.headers.get("Retry-After", "")
                    delay = int(raw) if isinstance(raw, str) and raw.isdigit() else 3 * (attempt + 1)
                    if delay > 60:
                        self.stopped = True
                        return None, None, "musicbrainz_retry_later"
                    self.sleep(max(1.1, delay))
                    continue
                if response.status_code in (500, 502, 503, 504):
                    self.consecutive_errors += 1
                    self.stopped = self.consecutive_errors >= 3
                    self.last_error = f"HTTP {response.status_code}"
                    print(f"MusicBrainz {self.last_error}; lookup left pending"
                          + ("; pausing after repeated failures" if self.stopped else ""),
                          flush=True)
                    return None, None, "musicbrainz_unavailable"
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError("Unexpected MusicBrainz response")
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Unexpected JSON structure")
                break
            except (requests.Timeout, requests.ConnectionError):
                if attempt < self.max_retries:
                    self.sleep(3 * (attempt + 1))
                    continue
                self.stopped = True
                self.last_error = "connection_timeout"
                return None, None, "musicbrainz_unavailable"
            except (requests.RequestException, ValueError):
                # Permission failures are not retried or bypassed.
                self.stopped = True
                self.last_error = f"HTTP {response.status_code}" if "response" in locals() else "request_error"
                print(f"MusicBrainz requests paused: {self.last_error}", flush=True)
                return None, None, "musicbrainz_unavailable"
        stamp = self.now.isoformat(timespec="seconds")
        self.cache[key] = {"fetched_at": stamp, "data": data}
        self.consecutive_errors = 0
        if self.cache_path:
            write_json(self.cache_path, {"responses": self.cache})
        return data, self.now.astimezone(LA).date().isoformat(), None

    def artist(self, mbid):
        if not valid_mbid(mbid):
            return None, None, "invalid_mbid"
        return self.get("/artist/" + mbid, {"inc": "url-rels"})

    def search(self, name):
        # Escape Lucene syntax inside one quoted name, never split a lineup.
        escaped = re.sub(r'([\\"])', r"\\\1", name)
        return self.get("/artist/", {"query": 'artist:"' + escaped + '"', "limit": 10})


def collect_names(shows, lineups):
    """Only explicit lineup names or complete source titles; no splitting."""
    names = {}
    for show in shows:
        lineup = lineups.get(show["id"])
        candidates = lineup if isinstance(lineup, list) else [show["title"]]
        for name in candidates:
            if isinstance(name, str) and name.strip():
                entry = names.setdefault(exact_key(name), {"name": name.strip(), "shows": []})
                entry["shows"].append(show["id"])
    return names


def approved_identities(identities):
    if not isinstance(identities, dict):
        raise ValueError("artist_identities.json must be an object")
    mapped = {}
    for name, record in identities.items():
        key = exact_key(name)
        if key in mapped:
            raise ValueError("Duplicate normalized artist identity: " + name)
        mapped[key] = record
    return mapped


def lookup_terms(title):
    """Try the published title, then a clearly separated performer prefix."""
    title = html.unescape(title).strip()
    terms = [title]
    # Preserve names containing ampersands, commas, slashes, or plus signs.
    cleaned = re.sub(r"^.*?\b(?:presents?|present)\s*:\s*", "", title, flags=re.I)
    cleaned = re.sub(r"^LED presents\s+", "", cleaned, flags=re.I)
    cleaned = re.split(r"\s+(?:[-–—]|w/|with special guests|with|presents)\s+|:\s+", cleaned,
                       maxsplit=1, flags=re.I)[0].strip()
    if cleaned and cleaned not in terms:
        terms.append(cleaned)
    return terms


def enrich(shows, lineups, identities, client):
    names = collect_names(shows, lineups)
    identities = approved_identities(identities)
    registry, review = {}, []
    # Optional known MBIDs are useful corrections, not a whitelist.
    ordered = sorted(names.items(), key=lambda pair: (
        not bool(isinstance(identities.get(pair[0]), dict)
                 and identities[pair[0]].get("approved") is True), pair[0]))
    for number, (key, entry) in enumerate(ordered, 1):
        name = entry["name"]
        identity = identities.get(key)
        item = {"name": name, "show_ids": entry["shows"]}
        detail = None
        checked = None
        if isinstance(identity, dict) and identity.get("disabled") is True:
            item["reason"] = "explicitly_disabled"
        elif isinstance(identity, dict) and valid_mbid(identity.get("mbid")):
            mbid = identity.get("mbid")
            detail, checked, error = client.artist(mbid)
            if error:
                item["reason"] = error
            elif detail.get("id") != mbid:
                item["reason"] = "mbid_mismatch"
            else:
                item["match_method"] = "optional_mbid_override"
            item["mbid"] = mbid
        else:
            for term in lookup_terms(name):
                data, _, error = client.search(term)
                if error:
                    item["reason"] = error
                    break
                candidates = [{
                        "mbid": artist.get("id"), "name": artist.get("name"),
                        "profile_url": "https://musicbrainz.org/artist/" + artist.get("id", ""),
                        "disambiguation": artist.get("disambiguation"),
                        "area": artist.get("area", {}).get("name"),
                        "exact_name": exact_key(artist.get("name", "")) == key,
                        "score": artist.get("score", 0),
                    } for artist in data.get("artists", []) if valid_mbid(artist.get("id"))]
                item["candidates"] = candidates
                item["total_candidates"] = data.get("count")
                if not candidates:
                    item["reason"] = "no_artist_match"
                    continue
                # Trust MusicBrainz ranking as requested. Do not require human
                # approval, uniqueness, or a hand-curated name/website pin.
                chosen = max(candidates, key=lambda c: int(c["score"] or 0))
                mbid = chosen["mbid"]
                item.update(mbid=mbid, search_term=term,
                            match_method="musicbrainz_highest_ranked_result")
                detail, checked, error = client.artist(mbid)
                if error:
                    item["reason"] = error
                elif detail.get("id") != mbid:
                    detail = None
                    item["reason"] = "mbid_mismatch"
                break
        if detail and not item.get("reason") in {
                "mbid_mismatch", "artist_not_found", "musicbrainz_unavailable"}:
            homepage, problem = homepage_from_artist(detail)
            if homepage:
                registry[name] = {
                    "official_url": homepage, "official_urls": homepage_urls(detail),
                    "artist_name": detail.get("name") or name,
                    "verified": True, "verified_at": checked,
                    "evidence_url": "https://musicbrainz.org/artist/" + mbid,
                    "verification_method": "musicbrainz_official_homepage",
                    "mbid": mbid, "search_term": item.get("search_term", name),
                    "match_method": item.get("match_method"),
                }
                continue
            item["reason"] = problem
        review.append(item)
        if number % 10 == 0:
            print(f"Artists processed {number}/{len(ordered)}; "
                  f"{len(registry)} homepage matches; {client.requests_made} requests", flush=True)
    return registry, review


def merge_registries(automatic, manual):
    """Manual records (including explicit unverified/null entries) take priority."""
    merged = dict(automatic)
    for name, record in manual.items():
        for old in list(merged):
            if artist_key(old) == artist_key(name):
                del merged[old]
        merged[name] = record
    return merged


def run_enrichment(shows, lineups, *, online=False, root=ROOT, max_requests=None):
    config = dict(DEFAULTS, **load_json(root / "artist_enrichment.json", {}))
    if config.get("enabled") is not True:
        return {}, {"enabled": False}
    identities = load_json(root / "artist_identities.json", {})
    cache = load_json(root / "data/artist_cache.json", {"responses": {}})
    client = MusicBrainz(
        cache, online=online,
        max_requests=config["max_requests"] if max_requests is None else max_requests,
        cache_days=config["cache_days"],
        cache_path=root / "data/artist_cache.json",
    )
    registry, review = enrich(shows, lineups, identities, client)
    report = {
        "generated_at": client.now.isoformat(timespec="seconds"),
        "linked_artist_count": len(registry),
        "review_count": len(review), "requests_made": client.requests_made,
        "network_enabled": online, "items": review,
        "acceptance_policy": "automatic_musicbrainz_official_homepage",
        "matches": [{"source_name": name, **record} for name, record in registry.items()],
    }
    write_json(root / "data/artist_cache.json", cache)
    write_json(root / "artist_review.json", report)
    write_review(root / "artist_review.md", report)
    print(f"Artist enrichment: {len(registry)} linked identities, "
        f"{len(review)} unresolved entries, {client.requests_made} API requests")
    return registry, {k: report[k] for k in (
        "generated_at", "linked_artist_count", "review_count", "requests_made")}


def write_review(path, report):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "# Artist homepage lookup results",
        "",
        "Generated: " + report["generated_at"] + ". This is a working review "
        "list of missing/unprocessed homepage results; manual approval is not required.",
        "",
        f"Automatically accepted homepage matches: {report['linked_artist_count']}. "
        f"Unresolved entries: {report['review_count']}.",
        "",
        "Whole listing titles may be marketing text or multiple performers; "
        "the automatic lookup uses MusicBrainz's highest-ranked result. Candidate "
        "links below are MusicBrainz profiles, not official artist websites.",
        "",
        "## Automatically linked results",
        "",
        "| Returned artist | Official homepage | Source listing |",
        "|---|---|---|",
    ]
    for record in report.get("matches", []):
        homepage = record["official_url"].replace("(", "%28").replace(")", "%29")
        lines.append("| " + cell(record.get("artist_name", record["source_name"]))
                     + " | [Official homepage](" + homepage + ") | "
                     + cell(record["source_name"]) + " |")
    lines += [
        "",
        "## Unresolved lookups",
        "",
        "| Source name / listing | Review reason | MusicBrainz candidates |",
        "|---|---|---|",
    ]
    for item in report["items"]:
        candidates = [
            "[" + cell(c.get("name")) + "](" + c["profile_url"] + ")"
            + (" (" + cell(c["disambiguation"]) + ")" if c.get("disambiguation") else "")
            for c in item.get("candidates", []) if valid_mbid(c.get("mbid"))
        ]
        if not candidates and valid_mbid(item.get("mbid")):
            candidates = ["[Matched artist](https://musicbrainz.org/artist/" + item["mbid"] + ")"]
        lines.append("| " + cell(item["name"]) + " | " + cell(item["reason"])
                     + " | " + "; ".join(candidates) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="Allow bounded MusicBrainz requests")
    parser.add_argument("--max-requests", type=int)
    parser.add_argument("--names", nargs="+", help="Discover these complete names only")
    parser.add_argument("--inspect", help="Inspect one candidate MBID without approving it")
    args = parser.parse_args()
    if args.inspect:
        cache = load_json(ROOT / "data/artist_cache.json", {"responses": {}})
        client = MusicBrainz(cache, online=args.online, max_requests=1)
        detail, checked, error = client.artist(args.inspect)
        homepage, problem = homepage_from_artist(detail) if detail else (None, error)
        print(json.dumps({"mbid": args.inspect, "name": (detail or {}).get("name"),
                          "disambiguation": (detail or {}).get("disambiguation"),
                          "homepage": homepage, "problem": problem, "checked": checked,
                          "evidence_url": "https://musicbrainz.org/artist/" + args.inspect},
                         indent=2))
        write_json(ROOT / "data/artist_cache.json", cache)
        return
    data = load_json(ROOT / "shows.json", {"shows": []})
    shows = data["shows"]
    if args.names:
        shows = [{"id": "lookup:" + str(i), "title": n} for i, n in enumerate(args.names)]
    run_enrichment(shows, load_json(ROOT / "event_lineups.json", {}),
                   online=args.online, max_requests=args.max_requests)
    print("To update the page from this cache: python run.py --from-cache")


if __name__ == "__main__":
    main()
