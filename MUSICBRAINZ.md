# Automatic official artist websites with MusicBrainz

As requested, v0.3.0 accepts MusicBrainz “official homepage” results without
manual identity approval, a curated whitelist, or a pinned website. Missing
homepages stay unlinked; tickets remain separate. This replaces v0.2.0's
approval-first policy.

## Automatic matching and homepage acceptance

The collector searches the complete source name/title. If that returns no
artists, it can try a clearly separated performer prefix before a tour-name,
“with,” or “w/” suffix, or remove a recognizable promoter prefix. It does not
split names at commas, ampersands, plus signs, or slashes. Explicit
`event_lineups.json` entries still provide independently looked-up performers.

When a search returns artists, the collector selects MusicBrainz's highest
ranked result; ties use the service's result order. Same-name alternatives
do not trigger an approval gate. It retrieves that artist's URL relationships
and automatically accepts active relationships labeled `official homepage`,
as defined in the [MusicBrainz relationship documentation](https://musicbrainz.org/relationships/artist-url).
It does not substitute a lower-ranked artist just because that artist has a
website.

If several official homepages are returned, all usable URLs are stored in
`official_urls`; the first is used for the artist-name hyperlink. Multiple
homepages and changes to an old homepage are not reasons to block a link.
The URL's hostname is not independently classified as “official” by this kit;
MusicBrainz's relationship classification is trusted.

The returned canonical artist name is the hyperlink text. If it differs from
the original event title, the unlinked source title remains beneath it.
A headliner's website never wraps a full multi-performer marketing title.
Support acts need their own source names/explicit lineup entries to receive
independent links.

## What this policy does and does not establish

This is source acceptance, not independent verification of every band or
domain. A highest-ranked same-name artist can be the wrong performer.
MusicBrainz's relationship data can be incomplete or outdated. The user has
chosen to accept these results automatically rather than require manual
verification. Match provenance is retained so individual mistakes can be
corrected.

Only active `official homepage` relationships become automatic links. Social,
discography, streaming, and profile relationships are not relabeled as
homepages. If MusicBrainz itself classifies a destination as an official
homepage, the kit does not impose an additional social/ticket/profile-domain
blacklist on that result.

Basic URL safety still applies: HTTP(S), no embedded credentials, no obvious
localhost/private-IP destinations, and a valid hostname/port. A destination
equal to that show's actual ticket, event, or venue URL cannot become the
artist link. No arbitrary candidate website is fetched during enrichment.

The legacy public field `website_verified` now means that the record passed
the source-acceptance/URL checks, not that a human approved it. Automatic
records explicitly carry `verification_method: musicbrainz_official_homepage`
and a MusicBrainz evidence URL.

## Cache, requests, and retries

- **Normal refresh:** `python run.py` scrapes venues and enriches artists.
- **Offline rebuild:** `python run.py --from-cache` uses only existing caches.
- **Artist-only refresh:** `python run.py --from-cache --enrich-artists`
  enriches without re-scraping venue calendars.
- **Full backfill:** `python artist_enrichment.py --online --max-requests 1200`,
  followed by `python run.py --from-cache`, works through the saved list.
- **Targeted lookup:** `python artist_enrichment.py --online --names "Artist Name"`
  limits discovery to named inputs; rebuild afterward to restore full reports.
- **Inspection:** `python artist_enrichment.py --online --inspect ACTUAL-MBID`
  prints one artist's returned homepage; inspection is optional, not approval.

Default request budget: 600 new API calls per run, configurable in
`artist_enrichment.json`; explicit runs are capped at 2,000 calls. Cached
responses are reusable for 30 days and are written after each successful
response so an interrupted backfill can resume. API calls are paced at least
1.1 seconds apart, following the
[MusicBrainz API rules](https://musicbrainz.org/doc/MusicBrainz_API).

Temporary service errors receive up to two delayed retries. An isolated
server error is recorded as pending rather than cancelling the rest of the
catalog. Repeated server failures, access denials, or exhausted rate limits
pause network requests rather than bypass restrictions. Venue publication
does not depend on every artist lookup succeeding. Missing/unprocessed
lookups can be retried on later runs.

Public read-only requests use no API key and identify this application in
User-Agent. Another maintainer can set `MUSICBRAINZ_USER_AGENT` with their own
contact URL. Check MusicBrainz's current commercial-use terms before
monetizing a deployment; this kit does not grant third-party usage rights.

## Results and optional corrections

`artist_review.md` and `artist_review.json` now list unresolved lookups, not
artists awaiting mandatory approval. Their reasons distinguish:

- **No artist match:** The searches returned no artist.
- **No active official homepage:** A matched artist lacks that relationship.
- **Not cached / request budget / API unavailable:** The lookup is pending,
  not evidence that a homepage does not exist.
- **Explicitly disabled:** A maintainer deliberately disabled this name.

The JSON report also includes every accepted source name, selected artist
name/MBID, matching method, searched term, and homepage(s). A fresh-cache
offline rebuild recreates the same automatic links without network calls.
The public `verified_at` date is the cached response's Pacific date, not the
date of an offline rebuild.

`artist_identities.json` is optional. Existing MBIDs remain useful corrections
but no longer form a whitelist; old `approved`, `homepage`, and
`canonical_name` fields do not gate automatic linking. To deliberately disable
an entry, set `"disabled": true`. Set or replace `mbid` to correct a wrong
automatic artist match.

Evidence-backed `band_overrides.json` records still take priority over
automatic results. A null/unverified manual record still suppresses that
name's automatic link. Removing an optional identity no longer disables
automatic discovery.

## Deployment boundaries

No APIs are called by visitors' browsers. Only `index.html`, `shows.json`,
and `.nojekyll` are staged for the public site. Raw API caches and lookup
reports stay in the kit/source repository, though they will be visible if
that repository is public.

The existing Actions workflow persists API caches and reports on successful
refreshes. Ordinary code pushes perform an offline rebuild using those
caches. No setlist.fm website scraper or event API was added, and artist
enrichment does not independently refresh or verify concert dates.
