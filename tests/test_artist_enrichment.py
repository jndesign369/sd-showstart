"""No-network regression tests for automatic MusicBrainz homepage enrichment."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from artist_enrichment import (
    MusicBrainz, approved_identities, collect_names, enrich, homepage_from_artist,
    merge_registries, public_homepage, run_enrichment, valid_mbid,
)
from artist_links import apply_artist_links

MBID = "11111111-1111-4111-8111-111111111111"
NOW = datetime(2026, 10, 31, 2, tzinfo=timezone.utc)
URL = "https://artist-band.com/"


def detail(url=URL):
    return {"id": MBID, "name": "Artist", "relations": [
        {"type": "official homepage", "ended": False, "url": {"resource": url}}
    ]}


def shows():
    return [{"id": "test:1", "title": "Artist", "ticket_url": "https://ticketweb.com/1",
             "event_url": "https://venue.com/event", "venue_url": "https://venue.com/"}]


def identity(**kwargs):
    return {"Artist": dict({"approved": True, "mbid": MBID, "homepage": URL}, **kwargs)}


def response(data=None, status=200):
    r = Mock(status_code=status)
    r.json.return_value = data or detail()
    if status >= 400:
        r.raise_for_status.side_effect = requests.HTTPError()
    return r


class HomepageTest(unittest.TestCase):
    def test_only_official_relation(self):
        d = detail()
        d["relations"][0]["type"] = "social network"
        self.assertIsNone(homepage_from_artist(d)[0])

    def test_ended_relation_rejected(self):
        for field, value in (("ended", True), ("end", "2025")):
            d = detail()
            d["relations"][0][field] = value
            self.assertIsNone(homepage_from_artist(d)[0])

    def test_multiple_homepages_accepted(self):
        d = detail()
        d["relations"].append(detail("https://another-band.com/")["relations"][0])
        self.assertEqual(homepage_from_artist(d), (URL, None))

    def test_unsafe_destinations_rejected(self):
        for url in ("javascript:alert(1)", "http://127.0.0.1/", "http://192.168.0.1/",
                    "http://localhost/", "http://host.internal/", "https://artist-band.com:bad/"):
            self.assertIsNone(public_homepage(url), url)

    def test_official_homepage_classification_is_trusted(self):
        d = detail("https://artist.bandcamp.com/")
        self.assertEqual(homepage_from_artist(d)[0], "https://artist.bandcamp.com/")
        # No destination-class guesses override MusicBrainz's official label.
        d = detail("https://instagram.com/artist")
        self.assertEqual(homepage_from_artist(d)[0], "https://instagram.com/artist")

    def test_official_url_accepted(self):
        self.assertEqual(homepage_from_artist(detail()), (URL, None))

    def test_all_official_homepages_retained_in_record(self):
        d = detail()
        d["relations"].append(detail("https://second-band.com/")["relations"][0])
        c = Mock()
        c.artist.return_value = (d, "2026-10-30", None)
        registry, _ = enrich(shows(), {}, identity(), c)
        self.assertEqual(registry["Artist"]["official_urls"],
                         [URL, "https://second-band.com/"])


class ClientTest(unittest.TestCase):
    def test_offline_makes_zero_requests(self):
        session = Mock()
        client = MusicBrainz({}, session=session, now=NOW)
        self.assertEqual(client.artist(MBID)[2], "not_cached_or_expired")
        session.get.assert_not_called()

    def test_cache_hit_and_pacific_verification_date(self):
        session = Mock()
        session.get.return_value = response()
        cache = {}
        online = MusicBrainz(cache, online=True, session=session, now=NOW)
        self.assertEqual(online.artist(MBID)[1], "2026-10-30")
        offline = MusicBrainz(cache, session=Mock(), now=NOW)
        self.assertEqual(offline.artist(MBID)[1], "2026-10-30")
        self.assertEqual(session.get.call_count, 1)

    def test_expired_cache_not_promoted(self):
        session = Mock()
        session.get.return_value = response()
        cache = {}
        MusicBrainz(cache, online=True, session=session, now=NOW).artist(MBID)
        later = datetime(2026, 12, 1, tzinfo=timezone.utc)
        self.assertEqual(MusicBrainz(cache, now=later).artist(MBID)[2], "not_cached_or_expired")

    def test_request_budget_enforced(self):
        session = Mock()
        session.get.return_value = response()
        c = MusicBrainz({}, online=True, max_requests=1, session=session, now=NOW)
        c.artist(MBID)
        self.assertEqual(c.search("Another")[2], "request_budget_exhausted")
        self.assertEqual(session.get.call_count, 1)

    def test_rate_limit_and_user_agent(self):
        session = Mock()
        session.get.return_value = response()
        sleep = Mock()
        c = MusicBrainz({}, online=True, session=session, now=NOW, sleep=sleep, clock=lambda: 10)
        c.artist(MBID)
        c.search("Another")
        sleep.assert_called_once_with(1.1)
        call = session.get.call_args.kwargs
        self.assertIn("SanDiegoShows", call["headers"]["User-Agent"])
        self.assertFalse(call["allow_redirects"])

    def test_service_error_pauses_requests(self):
        for status in (429, 403):
            session = Mock()
            session.get.return_value = response(status=status)
            c = MusicBrainz({}, online=True, session=session, now=NOW, max_retries=0)
            self.assertEqual(c.artist(MBID)[2], "musicbrainz_unavailable")
            self.assertEqual(c.search("Next")[2], "service_paused_after_error")
            self.assertEqual(session.get.call_count, 1)

    def test_malformed_and_invalid_mbid(self):
        self.assertFalse(valid_mbid("../../"))
        c = MusicBrainz({}, online=True, session=Mock(), now=NOW)
        self.assertEqual(c.artist("../../")[2], "invalid_mbid")

    def test_transient_service_error_retried_with_backoff(self):
        session = Mock()
        transient = response(status=503)
        transient.headers = {"Retry-After": "2"}
        session.get.side_effect = [transient, response()]
        sleep = Mock()
        client = MusicBrainz({}, online=True, session=session, now=NOW,
                            sleep=sleep, clock=lambda: 10)
        self.assertEqual(client.artist(MBID)[0]["id"], MBID)
        self.assertEqual(session.get.call_count, 2)
        self.assertIn(unittest.mock.call(2), sleep.call_args_list)

    def test_large_one_time_budget_not_clamped_to_forty(self):
        self.assertEqual(MusicBrainz({}, max_requests=1200).remaining, 1200)

    def test_isolated_server_error_does_not_cancel_next_artist(self):
        session = Mock()
        session.get.side_effect = [response(status=503), response()]
        client = MusicBrainz({}, online=True, session=session, now=NOW,
                            max_retries=0, sleep=Mock(), clock=lambda: 10)
        self.assertEqual(client.search("Unavailable")[2], "musicbrainz_unavailable")
        self.assertEqual(client.artist(MBID)[0]["id"], MBID)

    def test_repeated_server_errors_pause_backfill(self):
        session = Mock()
        session.get.return_value = response(status=503)
        client = MusicBrainz({}, online=True, session=session, now=NOW,
                            max_retries=0, sleep=Mock(), clock=lambda: 10)
        for name in ("First", "Second", "Third"):
            client.search(name)
        self.assertEqual(client.search("Fourth")[2], "service_paused_after_error")
        self.assertEqual(session.get.call_count, 3)


class IdentityTest(unittest.TestCase):
    def client(self, data):
        session = Mock()
        session.get.return_value = response(data)
        return MusicBrainz({}, online=True, session=session, now=NOW)

    def test_approved_identity_links(self):
        s = shows()
        registry, review = enrich(s, {}, identity(), self.client(detail()))
        apply_artist_links(s, registry)
        self.assertEqual(s[0]["artists"][0]["official_url"], URL)
        self.assertEqual(review, [])

    def auto_client(self, candidates, lookup=None):
        c = Mock()
        c.search.return_value = ({"count": len(candidates), "artists": candidates}, "2026-10-30", None)
        c.artist.return_value = (lookup or detail(), "2026-10-30", None)
        return c

    def test_search_automatically_accepts_homepage(self):
        c = self.auto_client([{"id": MBID, "name": "Artist", "score": 100}])
        registry, review = enrich(shows(), {}, {}, c)
        self.assertEqual(registry["Artist"]["official_url"], URL)
        self.assertEqual(review, [])

    def test_same_name_candidates_use_musicbrainz_ranking(self):
        c = self.auto_client([
            {"id": MBID, "name": "Artist", "score": 100, "disambiguation": "Band A"},
            {"id": "22222222-2222-4222-8222-222222222222", "name": "Artist",
             "score": 90, "disambiguation": "Band B"}])
        registry, review = enrich(shows(), {}, {}, c)
        self.assertEqual(registry["Artist"]["mbid"], MBID)
        self.assertEqual(review, [])
        c.artist.assert_called_once_with(MBID)

    def test_changed_homepage_accepted_without_manual_gate(self):
        registry, review = enrich(shows(), {}, identity(), self.client(detail("https://new-band.com/")))
        self.assertEqual(registry["Artist"]["official_url"], "https://new-band.com/")
        self.assertEqual(review, [])

    def test_returned_canonical_name_is_used(self):
        d = detail()
        d["name"] = "Artist New Name"
        registry, review = enrich(shows(), {}, identity(), self.client(d))
        s = shows()
        apply_artist_links(s, registry)
        self.assertEqual(s[0]["artists"][0]["name"], "Artist New Name")
        self.assertEqual(review, [])

    def test_missing_homepage_stays_unlinked_without_approval_request(self):
        d = detail()
        d["relations"] = []
        c = self.auto_client([{"id": MBID, "name": "Artist", "score": 100}], d)
        registry, unresolved = enrich(shows(), {}, {}, c)
        self.assertEqual(registry, {})
        self.assertEqual(unresolved[0]["reason"], "no_active_official_homepage")

    def test_explicit_disabled_override_stays_unlinked(self):
        registry, unresolved = enrich(shows(), {}, identity(disabled=True), Mock())
        self.assertEqual(registry, {})
        self.assertEqual(unresolved[0]["reason"], "explicitly_disabled")

    def test_tour_prefix_uses_returned_name_not_entire_title(self):
        s = shows()
        s[0]["title"] = "Artist - Fall Tour w/ Support"
        c = self.auto_client([{"id": MBID, "name": "Artist", "score": 100}])
        c.search.side_effect = [
            ({"count": 0, "artists": []}, "2026-10-30", None),
            ({"count": 1, "artists": [{"id": MBID, "name": "Artist", "score": 100}]},
             "2026-10-30", None)]
        registry, _ = enrich(s, {}, {}, c)
        apply_artist_links(s, registry)
        self.assertEqual(s[0]["artists"][0]["name"], "Artist")
        self.assertEqual(s[0]["title"], "Artist - Fall Tour w/ Support")

    def test_mismatched_mbid_reviewed(self):
        d = detail()
        d["id"] = "22222222-2222-4222-8222-222222222222"
        self.assertEqual(enrich(shows(), {}, identity(), self.client(d))[1][0]["reason"],
                         "mbid_mismatch")

    def test_explicit_alias_can_use_approved_canonical_name(self):
        d = detail()
        d["name"] = "Artist."
        registry, _ = enrich(shows(), {}, identity(canonical_name="Artist."), self.client(d))
        self.assertIn("Artist", registry)

    def test_no_lineup_splitting(self):
        s = [{"id": "t:1", "title": "Artist & Support with Friends"}]
        self.assertEqual(len(collect_names(s, {})), 1)
        self.assertEqual(len(collect_names(s, {"t:1": ["Artist", "Support"]})), 2)

    def test_manual_override_has_priority_even_when_disabled(self):
        self.assertEqual(merge_registries({"Artist": {"official_url": URL}}, {"ARTIST": None}),
                         {"ARTIST": None})

    def test_duplicate_approved_name_disabled(self):
        with self.assertRaises(ValueError):
            approved_identities({"Artist": {}, "artist": {}})

    def test_report_and_cache_written_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry, report = run_enrichment(shows(), {}, root=Path(tmp))
            self.assertEqual(registry, {})
            self.assertEqual(report["requests_made"], 0)
            self.assertTrue((Path(tmp) / "artist_review.md").exists())
            self.assertTrue((Path(tmp) / "data/artist_cache.json").exists())

    def test_disabled_enrichment(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "artist_enrichment.json").write_text('{"enabled":false}')
            registry, report = run_enrichment(shows(), {}, root=Path(tmp))
            self.assertEqual(report, {"enabled": False})
            self.assertEqual(registry, {})


if __name__ == "__main__":
    unittest.main()
