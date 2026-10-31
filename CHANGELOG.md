# San Diego Shows starter kit changelog

This file tracks downloadable kit releases, not daily listing refreshes on a
running website. The first numbered release establishes a baseline for the
previously unnumbered kit; no historical version numbers have been invented.

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
