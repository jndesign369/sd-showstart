"""Offline tests for the simplified ConcertsSD pipeline."""
import json
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
sys.path.insert(0, str(ROOT))

import collect
import enrich

FIXTURES = ROOT / "fixtures"
TODAY = date(2026, 11, 2)


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.index = (FIXTURES / "index.html").read_text(encoding="utf-8")
        self.venues = (FIXTURES / "by-venue.html").read_text(encoding="utf-8")

    def test_weeks_parsed_from_homepage(self):
        weeks = collect.parse_weeks(self.index)
        self.assertEqual(weeks[16], (11, 9))
        self.assertEqual(weeks[54], (7, 21))

    def test_year_follows_week(self):
        # A July event listed in November belongs to next year.
        self.assertEqual(
            collect.resolve_date("Jul", "21", TODAY, week_start=(7, 21)),
            date(2027, 7, 21))

    def test_new_year_wrap(self):
        # "Dec 28 - Jan 3" week: January events land in the following year.
        self.assertEqual(
            collect.resolve_date("Jan", "2", TODAY, week_start=(12, 28)),
            date(2027, 1, 2))

    def test_fallback_without_week(self):
        self.assertEqual(collect.resolve_date("Dec", "5", TODAY), date(2026, 12, 5))

    def test_venue_split(self):
        self.assertEqual(collect.split_venue("Belly Up Tavern, Solana Beach"),
                         ("Belly Up Tavern", "Solana Beach"))
        self.assertEqual(collect.split_venue("Dia De Los Deftones, Petco Park, SD"),
                         ("Dia De Los Deftones, Petco Park", "San Diego"))

    def test_parse_venues(self):
        with mock.patch.object(collect, "today", return_value=TODAY):
            venues = collect.parse_venues(self.venues, TODAY, collect.parse_weeks(self.index))
        by_name = {v["venue"]: v for v in venues}
        belly = by_name["Belly Up Tavern"]
        self.assertEqual(belly["city"], "Solana Beach")
        self.assertEqual(belly["events"][0]["date"], "2026-11-09")
        self.assertEqual(belly["events"][0]["performers"], ["King Buffalo", "LA Witch"])
        # The past Oct 26 event is dropped, not resurrected as 2027.
        self.assertNotIn("2026-10-26", [e["date"] for e in by_name["Quartyard"]["events"]])
        # The July event resolves to next year.
        self.assertEqual(by_name["House of Blues"]["events"][0]["date"], "2027-07-21")

    def test_venue_links_attached(self):
        with mock.patch.object(collect, "today", return_value=TODAY):
            data = collect.collect(online=False,
                                  html_pair=(self.index, self.venues),
                                  sleep=lambda _s: None)
        belly = next(s for s in data["shows"] if s["venue"] == "Belly Up Tavern")
        self.assertEqual(belly["venue_url"], "https://bellyup.com/")
        hobb = next(s for s in data["shows"] if s["venue"] == "House of Blues")
        self.assertEqual(hobb["venue_url"], "https://www.houseofblues.com/sandiego")
        self.assertEqual(data["source"]["updated"], "October 30, 2026")

    def test_dedupe(self):
        venues = [{"venue": "V", "city": "San Diego",
                   "events": [{"date": "2026-11-09", "performers": ["A"]}]}] * 2
        self.assertEqual(len(collect.dedupe(venues)), 1)


class EnrichTests(unittest.TestCase):
    def cache_with(self, key, payload):
        return {"responses": {key: {"fetched_at": "2026-11-01T00:00:00+00:00", "data": payload}}}

    def search_key(self, name):
        return '/artist/?{"limit": 10, "query": "artist:\\"' + name + '\\""}'

    def test_search_returns_cached_mbid(self):
        cache = self.cache_with(self.search_key("King Buffalo"),
                                {"artists": [{"id": "kb-1", "name": "King Buffalo"}]})
        client = enrich.MusicBrainz(cache, online=False,
                                    now=datetime(2026, 11, 2, tzinfo=timezone.utc))
        record = enrich.lookup("King Buffalo", client)
        self.assertEqual(record["mbid"], "kb-1")
        self.assertEqual(record["reason"], "not_cached_or_expired")

    def test_homepage_from_relations(self):
        client = enrich.MusicBrainz({"responses": {}}, online=False)
        artist = {"relations": [
            {"type": "official homepage", "ended": False,
             "url": {"resource": "https://kingbuffalo.com/"}},
            {"type": "official homepage", "ended": True,
             "url": {"resource": "https://old.example.com/"}},
        ]}
        self.assertEqual(client.homepage(artist), "https://kingbuffalo.com/")

    def test_retry_after_transient_503(self):
        calls = []

        class FakeResponse:
            def __init__(self, status):
                self.status_code = status

            def json(self):
                return {"artists": []}

        class FakeSession:
            def get(self, *a, **k):
                calls.append(1)
                return FakeResponse(503 if len(calls) <= 3 else 200)

        client = enrich.MusicBrainz({"responses": {}}, online=True,
                                    session=FakeSession(), sleep=lambda _s: None)
        data, error = client.search("Anyone")
        self.assertEqual(len(calls), 4)
        self.assertIsNone(error)
        self.assertEqual(data, {"artists": []})

    def test_unsafe_urls_rejected(self):
        self.assertIsNone(enrich.public_homepage("javascript:alert(1)"))
        self.assertIsNone(enrich.public_homepage("http://localhost/x"))
        self.assertIsNone(enrich.public_homepage("not a url"))
        self.assertEqual(enrich.public_homepage("https://example.com/"),
                         "https://example.com/")

    def test_enrich_show_records(self):
        client = enrich.MusicBrainz({"responses": {}}, online=False)
        shows = [{"performers": ["A", "B"]}]
        results = enrich.enrich(shows, client)
        self.assertEqual(shows[0]["artists"][0]["name"], "A")
        self.assertNotIn("official_url", shows[0]["artists"][0])
        self.assertEqual(results["A"]["reason"], "not_cached_or_expired")

    def test_real_cache_key_matches(self):
        # The reused cache from the previous version must keep hitting.
        cache = json.loads((ROOT / "data" / "artist_cache.json").read_text())
        self.assertIn(self.search_key("Mom Jeans"), cache["responses"])


if __name__ == "__main__":
    unittest.main()
