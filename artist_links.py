"""Conservative artist identity and official-website policy.

No title splitting, fuzzy matching, web-domain guessing, or legacy URL promotion.
Official websites can be curated or automatically accepted from MusicBrainz's
official-homepage relationship, never inferred from ticket/event links.
"""
from datetime import date
from urllib.parse import urlsplit

NON_ARTIST_HOSTS = {
    "ticketmaster.com", "ticketweb.com", "axs.com", "dice.fm", "eventbrite.com",
    "seetickets.us", "seetickets.com", "showclix.com", "etix.com", "tixr.com",
    "facebook.com", "instagram.com", "x.com", "twitter.com", "tiktok.com",
    "youtube.com", "youtu.be", "spotify.com", "linktr.ee", "bit.ly",
    "musicbrainz.org", "setlist.fm", "bandsintown.com", "songkick.com",
}


def artist_key(name):
    """Case and whitespace only; punctuation and word order preserve identity."""
    return " ".join(name.split()).casefold()


def http_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password):
            return None
        return value
    except ValueError:
        return None


def official_website(value):
    url = http_url(value)
    if not url:
        return None
    host = urlsplit(url).hostname.lower().rstrip(".")
    if any(host == h or host.endswith("." + h) for h in NON_ARTIST_HOSTS):
        return None
    return url


def verified_record(record, show):
    """Check manual evidence or automatically accepted MusicBrainz metadata."""
    if not isinstance(record, dict) or record.get("verified") is not True:
        return None
    url = (http_url if record.get("verification_method") == "musicbrainz_official_homepage"
           else official_website)(record.get("official_url"))
    evidence = http_url(record.get("evidence_url"))
    try:
        checked = date.fromisoformat(record.get("verified_at", ""))
    except (ValueError, TypeError):
        return None
    if checked > date.today() or not url or not evidence:
        return None
    # An official artist destination cannot be an event/ticket destination.
    if url.rstrip("/") in {
        (show.get(k) or "").rstrip("/") for k in ("ticket_url", "event_url", "venue_url")
    }:
        return None
    result = {
        "official_url": url,
        "website_verified": True,
        "evidence_url": evidence,
        "verified_at": checked.isoformat(),
    }
    for key in ("verification_method", "mbid", "artist_name", "official_urls",
                "search_term", "match_method"):
        if record.get(key):
            result[key] = record[key]
    return result


def apply_artist_links(shows, registry, lineups=None):
    """Attach artists only from explicit lineups or exact verified-name matches.

    Without a curated lineup, the original listing stays plain text unless its
    entire title exactly matches a registry artist. Unknown titles are not
    misrepresented as extracted artist names.
    """
    if not isinstance(registry, dict) or not isinstance(lineups or {}, dict):
        raise ValueError("Artist registry and event lineups must be JSON objects")
    lineups = lineups or {}
    records = {}
    for name, record in registry.items():
        key = artist_key(name)
        # Ambiguous duplicate keys are disabled instead of picking a winner.
        records[key] = None if key in records else record
    for show in shows:
        show["band_url"] = None  # legacy cached values must never reappear
        show["artists"] = []
        names = lineups.get(show["id"])
        if names is None and artist_key(show["title"]) in records:
            names = [show["title"]]
        if names is None:
            continue
        if not isinstance(names, list) or not names or not all(
            isinstance(n, str) and n.strip() for n in names
        ):
            raise ValueError(f"Invalid explicit lineup for {show['id']}")
        for name in names:
            artist = {
                "name": name.strip(), "official_url": None,
                "website_verified": False,
            }
            checked = verified_record(records.get(artist_key(name)), show)
            if checked:
                artist.update(checked)
                if checked.get("artist_name"):
                    # Link the returned artist name, never an entire tour title
                    # or multi-performer source listing to one homepage.
                    artist["name"] = checked["artist_name"]
            show["artists"].append(artist)
        if len(show["artists"]) == 1:
            # Backward-compatible field, only after this artist's verification.
            show["band_url"] = show["artists"][0]["official_url"]
