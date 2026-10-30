"""Offline checks for the public GitHub Pages build."""
import copy
import unittest

from scripts.prepare_site import validate


class PagesBuildTest(unittest.TestCase):
    def setUp(self):
        self.data = {
            "generated_at": "2026-10-24T12:00:00-07:00",
            "sources": {},
            "shows": [{
                "id": "test:1", "source": "test", "title": "Band",
                "venue": "Venue", "date": "2027-01-02",
                "show_time": "20:00", "doors_time": None,
                "ticket_url": "https://example.com/ticket",
                "band_url": None, "venue_url": None, "event_url": None,
            }],
        }

    def test_valid_snapshot(self):
        validate(self.data)

    def test_empty_calendar_is_valid(self):
        self.data["shows"] = []
        validate(self.data)

    def test_unsafe_url_is_rejected(self):
        self.data["shows"][0]["ticket_url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            validate(self.data)

    def test_missing_title_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["shows"][0].pop("title")
        with self.assertRaises(ValueError):
            validate(data)

    def test_invalid_time_is_rejected(self):
        self.data["shows"][0]["show_time"] = "29:00"
        with self.assertRaises(ValueError):
            validate(self.data)
