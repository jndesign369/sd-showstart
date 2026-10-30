"""Regression tests: ticket links never borrow from neighboring rows,
and Rady Shell venues come only from source text.

Run with: python -m unittest discover tests
"""
import unittest

from scrapers.humphreys import cards_to_shows as humphreys_cards
from scrapers.radyshell import cards_to_shows as radyshell_cards


def humph_card(start, title, ticket, sold_out=False, description="A music tour."):
    return {
        "start": start,
        "end": None,
        "title": title,
        "description": description,
        "ticket": ticket,
        "soldOut": sold_out,
    }


class HumphreysAssociationTest(unittest.TestCase):
    def test_linkless_row_does_not_borrow_next_rows_link(self):
        cards = [
            humph_card("10/24/2026 07:30 PM", "Sold Out Band", None, sold_out=True),
            humph_card(
                "10/27/2026 07:30 PM",
                "On Sale Band",
                "https://www.ticketmaster.com/event/AAA",
            ),
        ]
        shows = humphreys_cards(cards)
        by_title = {s["title"]: s for s in shows}
        self.assertIsNone(by_title["Sold Out Band"]["ticket_url"])
        self.assertEqual(
            by_title["On Sale Band"]["ticket_url"],
            "https://www.ticketmaster.com/event/AAA",
        )
        # And links are never shared between rows.
        links = [s["ticket_url"] for s in shows if s["ticket_url"]]
        self.assertEqual(len(links), len(set(links)))

    def test_sold_out_flag_and_comedy_exclusion(self):
        cards = [
            humph_card("10/24/2026 07:30 PM", "Band A", None, sold_out=True),
            humph_card(
                "11/07/2026 07:30 PM",
                "A Comedian",
                "https://www.ticketmaster.com/event/BBB",
                description="brings his incredible comedy show to town",
            ),
        ]
        shows = humphreys_cards(cards)
        self.assertEqual(len(shows), 1)
        self.assertTrue(shows[0]["sold_out"])


def rady_card(title, time_text, head, buy=None, details="/performances/x/"):
    return {
        "head": head,
        "title": title,
        "timeText": time_text,
        "buy": buy,
        "details": details,
    }


class RadyShellVenueTest(unittest.TestCase):
    HEAD = ["FRIDAY", "Oct 30"]

    def test_shell_venue_from_source_text(self):
        shows = radyshell_cards(
            [rady_card("Band", "8:00 pm The Rady Shell at Jacobs Park", self.HEAD)]
        )
        self.assertEqual(shows[0]["venue"], "The Rady Shell at Jacobs Park")
        self.assertEqual(shows[0]["venue_url"], "https://theshell.org/")

    def test_jacobs_music_center_venue(self):
        shows = radyshell_cards(
            [rady_card("Choir", "7:30 pm Jacobs Music Center", self.HEAD)]
        )
        self.assertEqual(shows[0]["venue"], "Jacobs Music Center")
        self.assertEqual(shows[0]["venue_url"], "https://www.sandiegosymphony.org/")

    def test_missing_venue_text_is_skipped_not_assumed(self):
        shows = radyshell_cards(
            [rady_card("Mystery", "8:00 pm", self.HEAD)]
        )
        self.assertEqual(shows, [])

    def test_yoga_excluded_and_buy_link_kept(self):
        shows = radyshell_cards(
            [rady_card("Fit Yoga", "9:30 am The Rady Shell at Jacobs Park", self.HEAD)]
        )
        self.assertEqual(shows, [])
        shows2 = radyshell_cards(
            [
                rady_card(
                    "Band",
                    "8:00 pm The Rady Shell at Jacobs Park",
                    self.HEAD,
                    buy="https://www.sandiegosymphony.org/tickets/xyz",
                )
            ]
        )
        self.assertEqual(shows2[0]["ticket_url"], "https://www.sandiegosymphony.org/tickets/xyz")
        self.assertEqual(shows2[0]["ticket_kind"], "direct")


if __name__ == "__main__":
    unittest.main()
