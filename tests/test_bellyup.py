"""Unit tests for the Belly Up calendar parser (no network needed).

Run with: python -m unittest discover tests
"""
import unittest

from scrapers.bellyup import parse_calendar

# Minimal stand-in for the real calendar page: the embedded JS array with
# tricky cases — an escaped apostrophe in the title, an event with no
# event-page link in the list markup, and two performances the same day.
FIXTURE = """
<html><body>
<div class='tw-cal-event'>
  <a href="https://bellyup.com/calendar/11111111/jimmys-buffet-bash"></a>
</div>
<script>
  events: [
    {
      id: '11111111',
      start: '2026-12-26 20:00:00',
      title: 'Jimmy\\'s Buffet - 3rd Annual Buffett Birthday Bash',
      venue: '<div class="tw-cal-full-venue">Belly Up</div>',
      allDay: false,
      doors: '',
      url: '#tw-event-dialog-11111111',
      displayTime: 'Show: 8:00PM'
    },
    {
      id: '22222222',
      start: '2026-12-26 23:00:00',
      title: 'Jimmy\\'s Buffet - 3rd Annual Buffett Birthday Bash',
      venue: '<div class="tw-cal-full-venue">Belly Up</div>',
      allDay: false,
      doors: '',
      url: '#tw-event-dialog-22222222',
      displayTime: 'Show: 11:00PM'
    },
    {
      id: '33333333',
      start: '2027-01-02 20:00:00',
      title: 'Desperado (The Nation\\'s Premier Eagles Tribute), Fleetwood Max',
      venue: '<div class="tw-cal-full-venue">Music Box</div>',
      allDay: false,
      doors: '',
      url: '#tw-event-dialog-33333333',
      displayTime: 'Show: 8:00PM'
    }
  ],
</script>
</body></html>
"""


class BellyUpParseTest(unittest.TestCase):
    def test_all_events_found_including_escaped_apostrophes(self):
        shows = parse_calendar(FIXTURE)
        self.assertEqual(len(shows), 3)

    def test_title_unescaped(self):
        shows = parse_calendar(FIXTURE)
        self.assertEqual(
            shows[0]["title"], "Jimmy's Buffet - 3rd Annual Buffett Birthday Bash"
        )

    def test_same_day_two_performances_both_kept(self):
        shows = parse_calendar(FIXTURE)
        late = [s for s in shows if s["show_time"] == "23:00"]
        self.assertEqual(len(late), 1)

    def test_fields(self):
        shows = parse_calendar(FIXTURE)
        by_id = {s["id"]: s for s in shows}
        self.assertEqual(by_id["bellyup:11111111"]["date"], "2026-12-26")
        self.assertEqual(by_id["bellyup:11111111"]["show_time"], "20:00")
        self.assertEqual(
            by_id["bellyup:11111111"]["event_url"],
            "https://bellyup.com/calendar/11111111/jimmys-buffet-bash",
        )
        self.assertEqual(
            by_id["bellyup:11111111"]["venue_url"], "https://bellyup.com/"
        )
        self.assertEqual(
            by_id["bellyup:33333333"]["venue_url"], "https://www.musicboxsd.com/"
        )

    def test_no_event_page_link_falls_back_to_construction(self):
        shows = parse_calendar(FIXTURE)
        by_id = {s["id"]: s for s in shows}
        self.assertEqual(
            by_id["bellyup:22222222"]["ticket_url"],
            "https://bellyup.com/calendar/22222222/",
        )


if __name__ == "__main__":
    unittest.main()
