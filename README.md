# San Diego Shows

Kit release: **v0.1.0**. Download filename:
`San Diego Shows starter kit-v0.1.0.zip`. The attachment title remains
“San Diego Shows starter kit”; check `VERSION` inside the archive to confirm
the release. See [CHANGELOG.md](CHANGELOG.md) for included changes and limitations.

A zero-cost listings site for upcoming live music in San Diego. One plain HTML
page reads `shows.json`, which is rebuilt daily by seven venue scrapers running
on GitHub Actions. No database, no CMS, no server to run.

For the prepared upload package, start with [GitHub Pages setup](GITHUB-PAGES-SETUP.md).
The workflow supports a fast snapshot deployment first, followed by optional
manual refreshes and daily scheduled collection.

The user's desired expansion coverage is saved in [VENUES.md](VENUES.md) and
`venues.json`: 36 supplied entries with their original ConcertsSD reference
links. This is a target list, not a list of enabled scrapers or verified official
venue websites.

See [VENUE-COVERAGE.md](VENUE-COVERAGE.md) for the entry-by-entry implementation
audit: dedicated collectors, partial cross-listings, parser-only support, and
coverage gaps.

**Venues covered by the starter kit:**

| Venue | Location | How it's read |
|---|---|---|
| Belly Up (calendar also lists The Sound, Music Box and other promoted venues) | Solana Beach | Static HTML + embedded event data, plus per-event pages for TicketWeb links and doors |
| Soda Bar | City Heights / Normal Heights | Dice widget, rendered in a headless browser |
| Quartyard | East Village | WordPress/Elementor event cards, rendered in a headless browser |
| The Observatory North Park | North Park | MusicEvent JSON-LD in static HTML (Ticketmaster links) |
| Humphreys Concerts by the Bay | Shelter Island | Season schedule rows with embedded calendar data + Ticketmaster links |
| The Rady Shell at Jacobs Park | Embarcadero | Performance list, rendered in a headless browser |
| SOMA San Diego | Midtown | Static Modern Events Calendar list |

Sold-out shows are kept and marked (Humphreys, SOMA publish it). House of
Blues (Live Nation) and the Casbah (Cloudflare) would not render their
event lists to our server-based methods and are documented below instead
of shipped broken.

## Files

```
VERSION                     downloadable kit version (currently 0.1.0)
CHANGELOG.md                release history and versioning policy
index.html                  the website (text-only table)
shows.json                  merged output the page reads
run.py                      runs all scrapers, merges, dedupes, writes shows.json
artist_links.py             exact artist identity and official-website policy
band_overrides.json         curated official-site records with verification evidence
event_lineups.json          optional explicit artist names per stable event ID
VENUES.md                   saved target coverage list and integration notes
venues.json                 machine-readable target entries and reference links
scrapers/
  common.py                 fetching, time parsing, per-source data cache
  bellyup.py                bellyup.com/calendar
  sodabar.py                sodabarmusic.com (Dice widget)
  quartyard.py              quartyardsd.com/events
data/                       last-good scrape per source (survives failures)
tests/                     unit tests for the parser and merge logic
.github/workflows/update.yml  daily scrape + commit + GitHub Pages deploy
```

## How it works

1. Each scraper reads one venue calendar and returns a list of shows with:
   date, show time, doors time (when published), age limit, event URL,
   ticket URL and venue URL. Artist identity and verified official websites
   are applied separately; they are never guessed from ticket destinations.
   - **Belly Up** also visits each upcoming event page (the calendar
     itself has no purchase links) to pick up the real TicketWeb link and
     doors time. That makes the daily run a few minutes longer; the
     calendar-only fallback is the event page itself.
   - **Soda Bar's** widget also lists shows it promotes at other venues;
     those are dropped so its 21+ policy and website only apply to its
     own shows. Flip `INCLUDE_ALL_VENUES` in the scraper to keep them.
   - **Quartyard** cards labeled comedy/trivia/bingo are skipped (extend
     `EXCLUDE_TITLE` in the scraper if you want them).
2. `run.py` runs all of them, drops past shows, dedupes (same band + venue +
   date + time from two sources becomes one row; two performances the
   same night stay separate), and writes `shows.json`.
3. If one venue's page fails (redesign, network, bot wall), the last good
   data from `data/<venue>.json` is kept and the site footer flags that
   source as stale. `shows.json` is never blanked: if every source fails,
   the previous file stays in place and the run exits with an error.
4. `index.html` fetches `shows.json` and renders a table with sorting,
   venue/source filters, and search. Ticket links are labeled honestly:
   "buy tickets" is a direct purchase link; "event page" means the venue
   sells via its own event page (e.g. sold-out Belly Up shows). It also
   hides past shows client-side using the Pacific date, so the page stays
   correct even if the data is a day old.

`python run.py --from-cache` rebuilds `shows.json` from the cached data
in `data/` without touching any website — useful after code changes.

## Quick start (local)

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
python run.py
python -m http.server 8000
# open http://localhost:8000

# unit tests (no network needed)
python -m unittest discover tests
```

Serving over HTTP matters: opening `index.html` straight from disk will block
the `shows.json` fetch in most browsers.

## Deploying to GitHub Pages

1. Follow [GITHUB-PAGES-SETUP.md](GITHUB-PAGES-SETUP.md) to create a public
   repository with the kit files at its root, including the hidden `.github` folder.
2. In the repo: Settings -> Pages -> Build and deployment -> Source:
   **GitHub Actions**.
3. Actions tab -> "Update shows" -> Run workflow. Leave refresh unchecked for
   the first snapshot deployment, then run again with refresh checked.
4. Your site is at `https://<yourname>.github.io/<repo>/`. The included
   daily workflow is scheduled for 14:30 UTC.

GitHub Actions minutes are free for public repositories, and GitHub Pages
static hosting is free, so the recurring cost is $0. If you prefer
Cloudflare Pages, push the repo there and point it at `index.html` — just
keep the scheduled scraper on GitHub Actions.

## Artist names and official websites

Artist names link only to independently verified official websites. Listing
titles never link to event pages, and an unknown artist website means plain
text, not a search, social, ticketing, or guessed URL. Ticket links stay in
their own column; venue names link to their own official venue websites.

See [ARTIST-LINKS.md](ARTIST-LINKS.md) for the evidence-backed registry format
and explicit multi-artist lineups. Old string-only URL overrides are no longer
treated as verified. There is no fuzzy or inferred headliner matching.

The supplied registry is empty: no real artist websites were verified in this
update, and no names are linked merely to make the table look complete.
For an existing GitHub site, follow [UPDATE-ARTIST-LINKS.md](UPDATE-ARTIST-LINKS.md).

## Broader coverage reference

[ConcertsSD](https://concertssd.com/) is a candidate discovery source, not an
enabled collector in this release. Its
[weekly listings](https://concertssd.com/week-12.html) expose individual performer
names, but those names link to ConcertsSD's own band index rather than official
artist websites. The weekly page also does not supply direct ticket-purchase
links. Any future integration should discover current weekly pages from the
homepage, preserve attribution, filter the intended geography, reconcile
duplicates with venue collectors, and verify ticket and artist destinations
separately. Do not treat a numbered weekly URL as a permanent current-week URL.

## Adding a venue

1. Copy the closest scraper in `scrapers/` (use `bellyup.py` if the venue's
   calendar is plain HTML; `sodabar.py` or `quartyard.py` if events are
   rendered by JavaScript).
2. Find a stable pattern: embedded JSON, JSON-LD blocks, or event links.
3. Register it in `SOURCES` in `run.py`.

Practical tips learned building the included scrapers:

- Many venue sites embed complete event data (JS variables, JSON-LD) that
  is easier and more reliable to parse than the visible HTML.
- Sources with dates but no year (common) use a "current year unless that
  date is 45+ days in the past, then next year" heuristic — see
  `infer_year()` in `scrapers/common.py`.
- Always distinguish doors time from show time when the venue publishes
  both. Soda Bar's widget publishes both; Belly Up's calendar only shows
  show time.
- Run the scraper on a schedule, never per visitor. One polite visit per
  venue per day keeps you on good terms with the sites you read.

### A note on the Casbah and House of Blues

The Casbah's real calendar (casbahmusic.com) sits behind Cloudflare's bot
challenge, which blocked every server-based method we tested. House of
Blues / Live Nation venue pages did not render their event list to our
headless browser (the page returned a placeholder instead of the shows).
GitHub Actions runners use data-center IPs, so expect similar results
there. Shipping scrapers that silently fail every night would be worse
than not having them. If you want that coverage, the options are: run that
scraper from a machine with a residential IP (e.g. a home cron job pushing
to the same repo), or use a paid scraping proxy service.

## Keeping it legal and polite

- You are republishing factual event information (band, date, time, venue)
  with links back to the sources — not their descriptions or images.
- Don't bypass login walls or paywalls. One visit per venue per day is
  modest, but check each venue's terms if in doubt — and if a venue
  objects, remove its scraper.

## Costs

| Item | Cost |
|---|---|
| GitHub Actions (public repo) | $0 |
| GitHub Pages hosting | $0 |
| Domain (optional) | ~$10-15/yr |

The real cost is maintenance: venue sites redesign every couple of years,
and scrapers need small fixes when they do.
