# Artist and ticket links

The page never substitutes a show's event/purchase link or a guessed domain
for a missing artist website. Manual records must identify official artist sites.
Unknown artist websites stay unlinked. No browser-side artist lookup or API call
is needed. v0.3.0 automatically accepts MusicBrainz “official homepage”
answers without manual artist approval; see [MUSICBRAINZ.md](MUSICBRAINZ.md).
The manual registry instructions below remain available as optional overrides,
not requirements for automatic linking. Automatic records trust MusicBrainz's
relationship label rather than independently classifying the destination.

## Record an official artist website

`band_overrides.json` is now a curated registry, not a name-to-URL shortcut.
Each record needs `official_url`, `verified: true`, `evidence_url`, and the
`verified_at` date in YYYY-MM-DD format. These fields record a human check;
setting the flag does not automatically verify a website.

Illustrative syntax only (reserved example domains, not real artists):

```json
{
  "Example Artist": {
    "official_url": "https://artist.example/",
    "verified": true,
    "evidence_url": "https://artist.example/about",
    "verified_at": "2026-10-30"
  }
}
```

Check the identity against the specific performer on the venue listing. Open the
candidate artist site and confirm its identity, music, or tour dates. Record a
page supporting that identity in `evidence_url`; don't mark search-result guesses
verified. If an artist has no official website, leave their record absent or
unverified. Social and ticketing URLs are not substitutes.

Old string entries such as `"Example Artist": "https://artist.example/"` are
not considered verified. Previously cached links are cleared unless they pass
the policy. The manual registry remains empty. v0.3.0 automatically discovers
and accepts MusicBrainz official-homepage relationships; `artist_identities.json`
is now an optional MBID correction file, not a whitelist. Manual entries take priority
over automatic records, including when a manual entry is explicitly unverified.

## Multiple performers and marketing titles

Automatic lookups can try a clearly separated performer prefix before a tour
or “with” suffix when the complete title returns no artist. They do not split
commas, ampersands, slashes, or `+`. The returned canonical artist name is
linked and the original marketing title stays plain text beneath it.
Explicit lineups remain the way to represent multiple performers independently.

To curate a multi-artist show, copy its stable `id` from `shows.json` and list the
performers separately in `event_lineups.json`:

```json
{
  "source:real-event-id": ["Example Artist", "Support Artist"]
}
```

Use the actual event ID, not this placeholder. Each performer gets their own
independent manual or automatically accepted MusicBrainz record. A performer
without a homepage stays plain text.
The original venue listing text remains visible below a curated lineup and is
never hyperlinked. Review curated lineups if a show changes.

## Separate ticket and venue destinations

- Artist name: a manual official website or MusicBrainz official-homepage answer.
- Buy tickets: the source's purchase URL, in a separate column.
- Event page: an explicitly labeled fallback when the source only provides its
  event page. It is never used as an artist link.
- Venue name: its own official venue URL, when supplied by the collector.

The build checks artist-link metadata again. The browser independently checks
URL schemes, source metadata, and collisions with event/ticket/venue URLs before
rendering a link. Manual records retain destination-category checks; automatic
MusicBrainz records trust its official-homepage classification.

## Rebuild without collecting again

```bash
python run.py --from-cache
python -m unittest discover -s tests -v
python scripts/prepare_site.py
```

This is a new presentation and verification policy, not a fresh collection of
event listings. Source collection timestamps remain in `shows.json`.
