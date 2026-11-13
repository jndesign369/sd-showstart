"""No-network regression tests for listening-link selection and persistence."""
import copy
import html
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import listen

BASE = "https://exampleband.bandcamp.com"
SPOTIFY = "https://open.spotify.com/artist/6zvul52xwTWzilBZl6BUbT"
NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def player(tracks):
    data = {"trackinfo": tracks}
    return '<script data-tralbum="' + html.escape(json.dumps(data), quote=True) + '"></script>'


def track(title="First", path="/track/first", **kwargs):
    return {"title": title, "title_link": path,
            "streaming": 1, "file": {"mp3-128": "https://t4.bcbits.com/stream/file"},
            **kwargs}


def catalog(*paths):
    return '<ul>' + ''.join(
        f'<li data-item-id="album-{i}"><a href="{path}">Release</a></li>'
        for i, path in enumerate(paths)) + '</ul>'


class Response:
    def __init__(self, text="", status=200, location=None):
        self.text, self.status_code = text, status
        self.headers = {"Location": location} if location else {}


class Session:
    def __init__(self, responses):
        self.responses, self.calls, self.headers = responses, [], {}

    def get(self, url, **kwargs):
        self.calls.append(url)
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        return value


class ListeningTests(unittest.TestCase):
    def resolver(self, pages=None, cache=None, **kwargs):
        return listen.Bandcamp(
            cache if cache is not None else {}, online=True,
            session=Session(pages or {}), now=NOW,
            sleep=lambda _seconds: None, **kwargs)

    def test_bandcamp_url_safety(self):
        for value in ("javascript:alert(1)", "https://bandcamp.com.evil.com/x",
                      "https://evil.com/track/no", "https://127.0.0.1/x",
                      "https://a.bandcamp.com@localhost/x", "https://a.bandcamp.com:999/x",
                      "https://a.bandcamp.com\\@evil.com/x", None):
            with self.subTest(value=value):
                self.assertIsNone(listen.bandcamp_url(value))
        self.assertEqual(listen.bandcamp_url("/track/name?q=yes#x", BASE),
                         BASE + "/track/name")

    def test_spotify_requires_artist_not_album_or_track(self):
        self.assertEqual(listen.spotify_url(SPOTIFY + "?si=hello"), SPOTIFY)
        self.assertEqual(listen.spotify_url(SPOTIFY.replace("/artist/", "/intl-us/artist/")), SPOTIFY)
        for value in (SPOTIFY.replace("/artist/", "/track/"),
                      SPOTIFY.replace("/artist/", "/album/"),
                      SPOTIFY.replace("open.spotify.com", "open.spotify.com.evil.com"),
                      "spotify:artist:123", None):
            self.assertIsNone(listen.spotify_url(value))

    def test_active_musicbrainz_relationships_only(self):
        detail = {"relations": [
            {"ended": True, "url": {"resource": BASE + "/old"}},
            {"end": "2026-01-01", "url": {"resource": SPOTIFY.replace("6zv", "5zv")}},
            {"url": {"resource": BASE}},
            {"url": {"resource": SPOTIFY}}]}
        self.assertEqual(listen.music_links(detail), (BASE, SPOTIFY))

    def test_html_entities_and_first_streamable_track(self):
        page = listen.BandcampPage(player([
            track(file=None), track(title="Rock & Roll", path="/track/rock-roll"),
            track(title="Later", path="/track/later")]), BASE + "/album/new")
        self.assertEqual(page.song()["listen_title"], "Rock & Roll")
        self.assertEqual(page.song()["listen_url"], BASE + "/track/rock-roll")

    def test_skip_unreleased_private_disabled_capped_and_unsafe_tracks(self):
        tracks = [
            track(file=None, unreleased_track=True), track(private=True),
            track(file={"mp3-128": None}), track(file="not-player-metadata"),
            track(streaming=0), track(is_draft=True), track(is_capped=True),
            track(path="/album/not-song"), track(path="https://evil.com/track/a"),
            track(path="//other.bandcamp.com/track/not-same-band"),
            track(title="Playable", path="/track/playable")]
        self.assertEqual(listen.BandcampPage(player(tracks), BASE).song()["listen_title"],
                         "Playable")

    def test_malformed_metadata_ignored(self):
        page = listen.BandcampPage('<script data-tralbum="{broken"></script>', BASE)
        self.assertIsNone(page.song())

    def test_catalog_order_and_no_recommendation_links(self):
        body = '<a href="/album/recommended">No</a>' + catalog(
            "/album/new", "/album/old", "https://foreign.bandcamp.com/album/other")
        self.assertEqual(listen.BandcampPage(body, BASE).releases,
                         [BASE + "/album/new", BASE + "/album/old"])

    def test_catalog_to_song_not_album(self):
        resolver = self.resolver({
            BASE + "/music": Response(catalog("/album/new", "/album/old")),
            BASE + "/album/new": Response(player([track()]))})
        result = resolver.resolve(BASE + "/")
        self.assertEqual(result["listen_url"], BASE + "/track/first")
        self.assertEqual(resolver.requests_made, 2)

    def test_skip_unplayable_release_then_next_release(self):
        resolver = self.resolver({
            BASE + "/music": Response(catalog("/album/new", "/album/old")),
            BASE + "/album/new": Response(player([track(file=None)])),
            BASE + "/album/old": Response(player([track(title="Older")]))})
        self.assertEqual(resolver.resolve(BASE)["listen_title"], "Older")

    def test_skip_removed_release(self):
        resolver = self.resolver({
            BASE + "/music": Response(catalog("/album/gone", "/album/old")),
            BASE + "/album/gone": Response(status=404),
            BASE + "/album/old": Response(player([track()]))})
        self.assertTrue(resolver.resolve(BASE))

    def test_forbidden_page_not_bypassed(self):
        resolver = self.resolver({
            BASE + "/music": Response(catalog("/album/blocked", "/album/old")),
            BASE + "/album/blocked": Response(status=403)})
        self.assertIsNone(resolver.resolve(BASE))
        self.assertEqual(resolver.requests_made, 2)

    def test_redirects_cannot_leave_bandcamp(self):
        resolver = self.resolver({
            BASE + "/music": Response(status=302, location="http://127.0.0.1/private")})
        self.assertIsNone(resolver.resolve(BASE))
        self.assertEqual(resolver.requests_made, 1)

    def test_real_bandcamp_redirect_followed(self):
        resolver = self.resolver({
            BASE + "/music": Response(status=302, location="/album/new"),
            BASE + "/album/new": Response(player([track()]))})
        self.assertTrue(resolver.resolve(BASE))

    def test_rate_limit_pauses_remaining_artists(self):
        for status in (429, 503):
            resolver = self.resolver({BASE + "/music": Response(status=status)})
            self.assertIsNone(resolver.resolve(BASE))
            self.assertTrue(resolver.paused)
            self.assertIsNone(resolver.resolve("https://nextband.bandcamp.com"))
            self.assertEqual(resolver.requests_made, 1)
            self.assertNotIn(BASE, resolver.cache)

    def test_network_failure_is_nonfatal(self):
        resolver = self.resolver({BASE + "/music": requests.Timeout()})
        self.assertIsNone(resolver.resolve(BASE))
        self.assertEqual(resolver.cache[BASE]["reason"], "network_error")

    def test_budget_never_exceeded_or_cached_as_miss(self):
        resolver = self.resolver({
            BASE + "/music": Response(catalog("/album/new"))}, max_requests=1)
        self.assertIsNone(resolver.resolve(BASE))
        self.assertEqual(resolver.requests_made, 1)
        self.assertNotIn(BASE, resolver.cache)

    def test_pacing_and_bounded_traversal(self):
        pages = {BASE + "/music": Response(catalog(
            *("/album/" + str(i) for i in range(6))))}
        pages.update({BASE + "/album/" + str(i): Response(player([])) for i in range(4)})
        resolver = self.resolver(pages)
        resolver.sleep = mock.Mock()
        with mock.patch.object(listen.time, "monotonic", return_value=10):
            self.assertIsNone(resolver.resolve(BASE))
        self.assertEqual(resolver.requests_made, 5)
        self.assertEqual(resolver.sleep.call_count, 4)
        resolver.sleep.assert_called_with(1.0)

    def test_success_cached_for_seven_days_and_offline_no_requests(self):
        cache = {}
        resolver = self.resolver({BASE + "/track/first": Response(player([track()]))},
                                 cache=cache)
        result = resolver.resolve(BASE + "/track/first")
        offline = listen.Bandcamp(cache, now=NOW + timedelta(days=6))
        self.assertEqual(offline.resolve(BASE + "/track/first"), result)
        self.assertEqual(offline.requests_made, 0)
        expired = listen.Bandcamp(cache, now=NOW + timedelta(days=8))
        self.assertIsNone(expired.resolve(BASE + "/track/first"))
        self.assertEqual(expired.requests_made, 0)

    def test_negative_cache_expires_after_one_day(self):
        cache = {}
        resolver = self.resolver({BASE + "/music": Response(catalog())}, cache=cache)
        resolver.resolve(BASE)
        again = listen.Bandcamp(cache, online=True, now=NOW + timedelta(hours=12),
                               session=Session({}))
        self.assertIsNone(again.resolve(BASE))
        self.assertEqual(again.requests_made, 0)
        retry = self.resolver({BASE + "/music": Response(player([track()]))}, cache=cache)
        retry.now = NOW + timedelta(days=2)
        self.assertTrue(retry.resolve(BASE))

    def test_bandcamp_preferred_spotify_fallback_dedup_and_homepage_preserved(self):
        key = '/artist/id?{"inc": "url-rels"}'
        mb = {"responses": {key: {"data": {"relations": [
            {"url": {"resource": BASE}}, {"url": {"resource": SPOTIFY}}]}}}}
        original = [{"artists": [
            {"name": "Band", "mbid": "id", "official_url": "https://example.com"}]},
            {"artists": [{"name": "Band", "mbid": "id"}]}]
        resolver = mock.Mock()
        resolver.resolve.return_value = {
            "listen_url": BASE + "/track/song", "listen_service": "Bandcamp",
            "listen_title": "A Song"}
        shows = copy.deepcopy(original)
        listen.add_listen(shows, mb, resolver)
        self.assertEqual(shows[0]["artists"][0]["listen_service"], "Bandcamp")
        self.assertEqual(shows[0]["artists"][0]["official_url"], "https://example.com")
        self.assertEqual(shows[1]["artists"][0]["listen_title"], "A Song")
        resolver.resolve.assert_called_once_with(BASE)
        resolver.resolve.return_value = None
        listen.add_listen(shows, mb, resolver)
        self.assertEqual(shows[0]["artists"][0]["listen_url"], SPOTIFY)
        self.assertNotIn("listen_title", shows[0]["artists"][0])

    def test_no_links_no_guess_or_stale_link(self):
        shows = [{"artists": [{"name": "Unknown", "listen_url": SPOTIFY}]}]
        listen.add_listen(shows, {}, mock.Mock())
        self.assertEqual(shows, [{"artists": [{"name": "Unknown"}]}])

    def test_spotify_without_bandcamp_does_not_fetch(self):
        key = '/artist/id?{"inc": "url-rels"}'
        mb = {"responses": {key: {"data": {"relations": [
            {"url": {"resource": SPOTIFY}}]}}}}
        resolver = mock.Mock()
        shows = [{"artists": [{"name": "Spotify Only", "mbid": "id"}]}]
        listen.add_listen(shows, mb, resolver)
        self.assertEqual(shows[0]["artists"][0]["listen_url"], SPOTIFY)
        resolver.resolve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
