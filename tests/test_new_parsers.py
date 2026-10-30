"""Unit tests for the Observatory and SOMA parsers (no network).

Run with: python -m unittest discover tests
"""
import unittest

from scrapers.observatory import parse_page as parse_observatory
from scrapers.soma import parse_page as parse_soma

OBSERVATORY_FIXTURE = """
<html><body>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "MusicEvent",
 "name": "Spooky Feels: A Halloween Indie Rock + Electronic Dance Party - 18+",
 "startDate": "2026-10-24T20:00:00",
 "url": "https://www.ticketmaster.com/spooky-feels/event/ABC123",
 "location": {"@type": "Place", "name": "The Observatory North Park",
   "address": {"@type": "PostalAddress", "addressLocality": "San Diego"}}}
</script>
<script type="application/ld+json">
{"@type": "MusicEvent", "name": "Santa Ana show",
 "startDate": "2026-11-01T19:00:00",
 "location": {"@type": "Place", "name": "The Observatory",
   "address": {"@type": "PostalAddress", "addressLocality": "Santa Ana"}}}
</script>
</body></html>
"""

SOMA_FIXTURE = """
<html><body><ol id="events-list">
<li class="event-onsale">
    <div class="event-info">
        <h3><a href="https://www.somasandiego.com/event/example-band/">Example Band</a></h3>
        <div class="event-time">Doors 6 pm - Mainstage</div>
    </div>
    <div class="event-links">
        <a href="https://bit.ly/example" target="_blank" class="button event-tickets">Tickets</a>
    </div>
    <div class="event-date">
        <span class="event-month">Nov</span>
        <span class="event-day">3</span>
        <span class="event-year">2026</span>
        <span class="event-weekday">Tue</span>
    </div>
</li>
<li class="event-soldout">
    <div class="event-info">
        <h3><a href="https://www.somasandiego.com/event/sold-out-band/">Sold Out Band</a></h3>
        <div class="event-time">Mainstage - 8pm</div>
    </div>
    <div class="event-date">
        <span class="event-month">Dec</span>
        <span class="event-day">5</span>
        <span class="event-year">2026</span>
        <span class="event-weekday">Sat</span>
    </div>
</li>
</ol></body></html>
"""


class ObservatoryTest(unittest.TestCase):
    def test_parses_san_diego_events_with_age(self):
        shows = parse_observatory(OBSERVATORY_FIXTURE)
        self.assertEqual(len(shows), 1)  # Santa Ana show filtered out
        s = shows[0]
        self.assertEqual(s["date"], "2026-10-24")
        self.assertEqual(s["show_time"], "20:00")
        self.assertEqual(s["age_limit"], "18+")
        self.assertNotIn("18+", s["title"])
        self.assertEqual(s["ticket_kind"], "direct")
        self.assertTrue(s["ticket_url"].startswith("https://www.ticketmaster.com/"))

    def test_non_san_diego_dropped(self):
        shows = parse_observatory(OBSERVATORY_FIXTURE)
        self.assertEqual([s["title"] for s in shows], ["Spooky Feels: A Halloween Indie Rock + Electronic Dance Party"])


class SomTest(unittest.TestCase):
    def test_fields(self):
        shows = parse_soma(SOMA_FIXTURE)
        self.assertEqual(len(shows), 2)
        first = shows[0]
        self.assertEqual(first["date"], "2026-11-03")
        self.assertEqual(first["doors_time"], "18:00")
        self.assertEqual(first["ticket_url"], "https://bit.ly/example")
        self.assertFalse(first["sold_out"])

    def test_sold_out_flag(self):
        shows = parse_soma(SOMA_FIXTURE)
        second = shows[1]
        self.assertTrue(second["sold_out"])
        self.assertIsNone(second["ticket_url"])
        self.assertEqual(second["show_time"], "20:00")


if __name__ == "__main__":
    unittest.main()
