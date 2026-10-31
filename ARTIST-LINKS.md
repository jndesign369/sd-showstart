# Artist and ticket links

Artist accuracy takes priority over having a hyperlink. The page never uses an
event link, purchase link, social account, or guessed domain as an artist website.
Unknown artist websites stay unlinked. No browser-side artist lookup or API call
is needed.

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
the new policy. No real artist sites have been verified as part of this update;
the supplied registry remains empty.

## Multiple performers and marketing titles

No splitting titles at commas, ampersands, `with`, or `+`: those may be part of an
artist's actual name. Without an explicit lineup, the original source listing is
shown as plain text, unless the entire title exactly matches a registry artist
(case and whitespace differences are allowed; punctuation remains significant).

To curate a multi-artist show, copy its stable `id` from `shows.json` and list the
performers separately in `event_lineups.json`:

```json
{
  "source:real-event-id": ["Example Artist", "Support Artist"]
}
```

Use the actual event ID, not this placeholder. Each performer gets their own
independently verified registry entry. A performer without one stays plain text.
The original venue listing text remains visible below a curated lineup and is
never hyperlinked. Review curated lineups if a show changes.

## Separate ticket and venue destinations

- Artist name: verified official artist website only.
- Buy tickets: the source's purchase URL, in a separate column.
- Event page: an explicitly labeled fallback when the source only provides its
  event page. It is never used as an artist link.
- Venue name: its own official venue URL, when supplied by the collector.

The build checks artist-link metadata again. The browser independently checks
URL schemes, verification metadata, known ticket/social domains, and collisions
with the event/ticket/venue URLs before rendering an artist link.

## Rebuild without collecting again

```bash
python run.py --from-cache
python -m unittest discover -s tests -v
python scripts/prepare_site.py
```

This is a new presentation and verification policy, not a fresh collection of
event listings. Source collection timestamps remain in `shows.json`.
