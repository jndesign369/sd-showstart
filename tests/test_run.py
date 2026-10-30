"""Unit tests for merge/dedupe/override logic in run.py (no network).

Run with: python -m unittest discover tests
"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

import run

LA = ZoneInfo("America/Los_Angeles")


def show(title, venue, date, time="20:00", ticket=None, source="x", **kw):
    return {
        "id": f"{source}:{title[:8]}",
        "source": source,
        "title": title,
        "venue": venue,
        "date": date,
        "show_time": time,
        "doors_time": None,
        "age_limit": None,
        "event_url": None,
        "ticket_url": ticket,
        "band_url": None,
        "venue_url": None,
        "timezone": "America/Los_Angeles",
        **kw,
    }


def payloads(shows, source="x"):
    return {source: {"status": "ok", "shows": shows}}


class MergeTest(unittest.TestCase):
    def test_same_show_from_two_sources_dedupes_and_keeps_ticket(self):
        p = payloads([show("High Vis", "Soda Bar", "2026-11-05", ticket=None)], "a")
        p["b"] = {"status": "ok", "shows": [show("High Vis", "Soda Bar", "2026-11-05", ticket="https://t.example")]}
        merged = run.merged_and_sorted(p, keep_past=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["ticket_url"], "https://t.example")

    def test_same_band_same_day_different_times_stay_two_rows(self):
        p = payloads(
            [
                show("Band", "Venue", "2026-11-05", time="18:00"),
                show("Band", "Venue", "2026-11-05", time="21:00"),
            ]
        )
        merged = run.merged_and_sorted(p, keep_past=True)
        self.assertEqual(len(merged), 2)

    def test_past_shows_dropped(self):
        today = datetime.now(LA).date().isoformat()
        p = payloads(
            [
                show("Old", "Venue", "2020-01-01"),
                show("New", "Venue", "2099-01-01"),
            ]
        )
        merged = run.merged_and_sorted(p, keep_past=False)
        self.assertEqual([s["title"] for s in merged], ["New"])

    def test_ids_not_reassigned(self):
        p = payloads([show("Band", "Venue", "2099-01-01")], "bellyup")
        merged = run.merged_and_sorted(p, keep_past=True)
        self.assertFalse(merged[0]["id"].startswith("sd-"))
        self.assertEqual(merged[0]["id"], "x:Band")


class OverridesTest(unittest.TestCase):
    def test_headline_match(self):
        s = show("High Vis w/ Chubby and the Gang", "Venue", "2099-01-01")
        run.apply_band_overrides([s], {"high vis": "https://www.highvis.co.uk/"})
        self.assertEqual(s["band_url"], "https://www.highvis.co.uk/")

    def test_no_match_leaves_null(self):
        s = show("Unknown Act", "Venue", "2099-01-01")
        run.apply_band_overrides([s], {"someone else": "https://x.com/"})
        self.assertIsNone(s["band_url"])

    def test_never_guessed(self):
        # A band named like a domain must not get an invented URL.
        s = show("The Websites", "Venue", "2099-01-01")
        run.apply_band_overrides([s], {})
        self.assertIsNone(s["band_url"])


class HeadlineTest(unittest.TestCase):
    def test_variants(self):
        for title, expected in [
            ("A, B, C", "A"),
            ("A w/ B", "A"),
            ("A with B", "A"),
            ("A + B", "A"),
            ("Just A", "Just A"),
        ]:
            self.assertEqual(run.headline(title), expected)


if __name__ == "__main__":
    unittest.main()
