"""Official-site verification and explicit lineup regression tests."""
import unittest
from artist_links import apply_artist_links
from scripts.prepare_site import validate


def record(url="https://artist.example/"):
    return {
        "official_url": url, "verified": True,
        "evidence_url": "https://artist.example/about",
        "verified_at": "2026-01-01",
    }


def show(title="Artist"):
    return {
        "id": "test:1", "title": title, "source": "test", "venue": "Venue",
        "date": "2099-01-01", "ticket_url": "https://tickets.example/show",
        "event_url": "https://venue.example/event", "band_url": "https://stale.example",
        "venue_url": "https://venue.example/",
    }


class ArtistLinksTest(unittest.TestCase):
    def test_verified_exact_name_only(self):
        s = show()
        apply_artist_links([s], {"Artist": record()})
        self.assertEqual(s["artists"][0]["official_url"], "https://artist.example/")

    def test_legacy_string_url_not_verified(self):
        s = show()
        apply_artist_links([s], {"Artist": "https://artist.example/"})
        self.assertIsNone(s["band_url"])
        self.assertFalse(s["artists"][0]["website_verified"])

    def test_missing_website_remains_plain(self):
        s = show()
        apply_artist_links([s], {})
        self.assertIsNone(s["band_url"])
        self.assertEqual(s["artists"], [])

    def test_support_act_not_linked_to_headliner(self):
        s = show("Tour night")
        apply_artist_links([s], {"Headliner": record()}, {"test:1": ["Headliner", "Support"]})
        self.assertTrue(s["artists"][0]["website_verified"])
        self.assertFalse(s["artists"][1]["website_verified"])
        self.assertIsNone(s["band_url"])

    def test_punctuation_does_not_guess_identity(self):
        for title in ("Artist, Support", "Artist with Support", "Artist + Support", "Artist & Support"):
            s = show(title)
            apply_artist_links([s], {"Artist": record()})
            self.assertEqual(s["artists"], [])

    def test_ticket_social_and_identical_event_url_blocked(self):
        for url in ("https://ticketmaster.com/event/1", "https://www.instagram.com/artist",
                    "javascript:alert(1)", "https://venue.example/event"):
            s = show()
            apply_artist_links([s], {"Artist": record(url)})
            self.assertIsNone(s["band_url"])

    def test_evidence_and_date_required(self):
        for field in ("evidence_url", "verified_at", "verified"):
            r = record()
            r.pop(field)
            s = show()
            apply_artist_links([s], {"Artist": r})
            self.assertIsNone(s["band_url"])

    def test_no_punctuation_normalization_collision(self):
        s = show("ACDC")
        apply_artist_links([s], {"AC/DC": record()})
        self.assertEqual(s["artists"], [])

    def test_cached_artist_data_cleared(self):
        s = show()
        s["artists"] = [{"name": "Wrong Artist", "official_url": "https://wrong.example"}]
        apply_artist_links([s], {})
        self.assertEqual(s["artists"], [])
        self.assertIsNone(s["band_url"])

    def test_build_rejects_forged_link(self):
        s = show()
        s["band_url"] = None
        s["artists"] = [{"name": "Artist", "official_url": "https://ticketweb.com/1",
                         "website_verified": True, "evidence_url": "https://artist.example/",
                         "verified_at": "2026-01-01"}]
        with self.assertRaises(ValueError):
            validate({"generated_at": "2026-10-30T10:00:00-07:00",
                      "sources": {}, "shows": [s]})
