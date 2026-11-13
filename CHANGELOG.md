# San Diego Shows starter kit changelog

This file tracks downloadable kit releases, not daily listing refreshes on a
running website. The first numbered release establishes a baseline for the
previously unnumbered kit; no historical version numbers have been invented.

## v0.4.2 (2026-11-13)

- Add separate new-tab listen links beside artists, including plain-text names.
- Prefer a streamable Bandcamp song from the first playable listed release;
  otherwise use the artist's MusicBrainz Spotify artist link.
- Resolve and cache songs in the background, with bounded traversal and
  request pacing. Keep the page text-only with no embedded music or SDKs.
- Persist the selection cache in scheduled updates, outside the public site.

## v0.4.1 (2026-11-04)

- Complete deployment of the simplified v0.4.0 edition uploaded by the user.
- Replace the old multi-venue workflow with ConcertsSD collection,
  MusicBrainz enrichment, and explicit GitHub Pages deployment.
- Run collection twice daily; keep the lookup cache out of the deployed site.
- Restore the simple edition's fixtures and regression tests.
- Remove superseded scrapers and configuration; earlier versions remain in git history.

## v0.4.0 (2026-11-02)

- Simplified edition: collect artist names, dates, and venues from ConcertsSD.
- Link artists using MusicBrainz official-homepage results and venues using
  an editable list of venue websites.

## v0.3.0 (2026-10-31)

### Changed at the user's request

- Automatically accept MusicBrainz's active `official homepage` answers.
  Removed mandatory identity approval, curated whitelist enforcement,
  homepage pins, and same-name/multiple-homepage review gates.
- Select the highest-ranked returned artist automatically; preserve match
  provenance and optional MBID corrections instead of withholding all links.
- Accept updated homepages and retain every qualifying homepage in
  `official_urls`, using the first as the name hyperlink.
- Trust MusicBrainz's relationship classification without an extra
  destination-category blacklist; retain basic URL safety and separation
  from the show's ticket/event/venue destinations.
- Display the returned artist name as the hyperlink and keep the original
  marketing title unlinked underneath.
- Try a clearly separated performer prefix when a full event-title search
  returns no artists; never split ampersands, commas, plus signs, or slashes.
- Raise the default background request budget to 600 and allow explicit
  full backfills up to 2,000 calls. Persist every successful API response
  immediately so interrupted runs can resume.
- Retry temporary API errors with bounded backoff; a single server error
  no longer stops the rest of the catalog.
- Repurpose the review reports as unresolved-lookup reports, not approval
  queues. Include a complete accepted-match list in the JSON report.
- Update the preview, source-policy explanation, and repository upgrade guide.
- 70 offline regression tests cover automatic acceptance, returned canonical
  names, multiple homepages, optional corrections, URL safety, cache behavior,
  request pacing, retries, and isolated-service-error handling.
- Backfill the saved catalog: 125 of 269 upcoming listings now carry homepage
  links, representing 116 distinct MusicBrainz artists. All 255 source-name
  inputs were processed; 100 had no artist match and 34 matched artists had
  no active official homepage. No temporary lookup failures remain pending.
  This is an artist-metadata update, not a fresh scrape of venue calendars.

### Important boundary

Automatic source acceptance does not independently verify the selected band's
identity or website ownership. A top-ranked same-name result can be wrong;
the policy intentionally trusts MusicBrainz as requested. No guessed domain
or fabricated homepage is generated when the API supplies none.

## v0.2.0 (2026-10-30)

### Added

- Background MusicBrainz official-homepage enrichment; no API key and no
  browser-side API calls. Searches produce suggestions only; approved MBIDs
  are required before an artist is linked.
- `artist_identities.json` for identity approvals and homepage pins;
  `artist_enrichment.json` for enable/disable, request budget, and cache TTL.
- `data/artist_cache.json` for persistent API responses and both
  `artist_review.md` and `artist_review.json` for unresolved entries.
- Three seeded identities with fetched homepage evidence:
  [Slow Pulp](https://www.slowpulp.com/),
  [Pigeons Playing Ping Pong](https://pigeonsplayingpingpong.com/), and
  [Theo Katzman](http://www.theokatzman.com/).
- Rate pacing, bounded calls, offline operation, safe destination checks,
  ended/multiple-homepage rejection, and pause-on-service-error behavior.
- A `--inspect` command for reviewing candidate MBIDs and a targeted discovery
  command for complete artist names.
- `MUSICBRAINZ.md` and `UPDATE-v0.2.0.md` for review and repository upgrades.
- 24 new offline regression tests, bringing the suite to 61 tests.

### Changed

- Normal venue refreshes also enrich artists; `--from-cache` remains offline,
  with explicit `--enrich-artists` opt-in for artist-only network refreshes.
- GitHub Actions now rebuilds cached artist links on ordinary pushes and
  persists the cache/review files after successful scheduled/manual refreshes.
- Manual artist overrides remain authoritative, including explicit disabling.
- Artist URLs cannot point to setlist.fm/MusicBrainz profiles or common
  discovery, social, or ticket services.
- Verification dates use Pacific dates so a UTC date rollover does not
  hide freshly checked links during a San Diego evening.

### Release boundaries

- Artist metadata was fetched live; venue calendars were not re-scraped.
  The bundled venue caches remain from October 24, 2026.
- Most names remain unlinked until their identities and official websites
  can be approved. Whole marketing titles are not split into guessed lineups.
- The live search returned distinct Mom Jeans candidates; neither was
  silently chosen. The request budget/service-pause safeguards also mean
  the bundled review list is not an exhaustive completed API search.
- MusicBrainz relationships are community-maintained metadata, not a
  guarantee that a website remains controlled by an artist. Pinned homepage
  changes require review.
- No setlist.fm page scraper or ConcertsSD discovery collector was added.
- This release does not automatically update the user's GitHub repository.

## v0.1.0 (2026-10-30)

### Release identification

- Added `VERSION` containing `0.1.0` and this changelog.
- Named the downloadable archive `San Diego Shows starter kit-v0.1.0.zip`.
- Kept the conversation attachment title “San Diego Shows starter kit.”
- Updated setup and update instructions to identify the numbered package.

### Included baseline

- Text-only static listings page with search, venue/source filters, sorting,
  responsive layout, and Pacific-date filtering.
- Seven venue collectors: Belly Up, Soda Bar, Quartyard, Observatory North
  Park, Humphreys Concerts by the Bay, The Rady Shell, and SOMA.
- Cached collection, merge handling, last-good-source fallback, and GitHub
  Actions / GitHub Pages setup.
- Separate ticket and venue destinations; artist names link only when an
  exact artist identity has a curated, evidence-backed official-site record.
  Unknown artist websites remain unlinked.
- The user's 36-entry target coverage list in `VENUES.md` and `venues.json`.
- Entry-by-entry implementation audit in `VENUE-COVERAGE.md`: six dedicated
  collectors, four partial cross-listed entries, one parser-only entry, and
  25 entries without implemented coverage.
- Existing-repository update instructions and 37 automated tests.

### Known limitations

- Source caches were collected October 24, 2026. The included merged snapshot
  was rebuilt October 30, 2026, without fresh network collection.
- The artist registry is empty; this release does not supply verified real
  artist websites.
- ConcertsSD is a discovery-source candidate, not an enabled collector.
- The 36 saved target entries are not all covered, and partial cross-listings
  do not establish complete venue calendars.
- This archive does not update the user's GitHub repository or deployed site
  automatically.

## Versioning policy

- **Patch releases (`0.1.1`):** Corrections, documentation changes, and other
  updates to a newly distributed kit, including a changed bundled snapshot.
- **Minor releases (`0.2.0`):** New capabilities or additional collectors.
- **Major releases (`1.0.0` and later):** A deliberate major release; after
  1.0, incompatible changes increment the major version.
- **Pre-1.0 changes:** The kit is still a starter release. Any incompatible
  change must be called out explicitly and increment the minor version.
- **Archive identity:** Do not replace an issued versioned ZIP with different
  contents under the same filename. Increment `VERSION`, add a changelog
  entry, and publish a correspondingly named ZIP.
- **Live data refreshes:** Routine scheduled refreshes of a running site do
  not increment the kit version unless a new kit archive is distributed.
