# San Diego Shows (simple edition)

A text-only list of upcoming San Diego concerts: artists, dates, and venues.

- **One source:** listing facts (performers, dates, venues) are collected from
  [The List: San Diego (ConcertsSD)](https://concertssd.com/), which already
  aggregates venue calendars. Nothing else is copied from their site.
- **Our own links:** artist names link to MusicBrainz "official homepage"
  results; venue names link to official venue websites listed in
  `venue_links.json`. No ticket or event links are republished.
- **No graphics, no frameworks:** one static HTML page and one JSON file.

## Update the listings

```bash
python collect.py     # fetch ConcertsSD (two requests, 10s apart) -> shows.json
python enrich.py      # link artists via MusicBrainz (cached; few requests)
python listen.py      # choose Bandcamp song links; Spotify artist fallback
```

Run the tests first if you changed anything:

```bash
python -m unittest discover -s tests
```

## Twice-daily automatic updates (GitHub Pages)

1. Push this folder to a GitHub repository.
2. In the repository: Settings → Pages → Source → GitHub Actions.
3. The included `.github/workflows/update.yml` runs twice daily at 7:30am
   and 7:30pm Pacific Standard Time (8:30am and 8:30pm during daylight
   saving time). GitHub may delay scheduled runs.
4. Each scheduled run tests, collects, links artists, saves the data, and
   deploys the site. Pushes deploy the saved snapshot without scraping.
5. For an immediate refresh: Actions → Update shows → Run workflow,
   leaving “Collect fresh ConcertsSD listings before deploying” checked.

Only the HTML, theme files, optional `images/` folder, `shows.json`, and
`VERSION` are deployed. Lookup caches, Python scripts, and tests are not public.

The workflow makes two requests to ConcertsSD per run (their robots.txt asks
for a 10-second crawl delay, which the collector observes) and only queries
MusicBrainz for new names or responses older than its 30-day cache lifetime.

## Change the look of the site

Edit `sdmusic-theme.xml`. Empty values keep the default styling and hide the
top image. Here is a filled-in example:

```xml
<sdmusic-theme>
  <background color="#f4f4f4" image="images/pattern.webp" repeat="repeat" />
  <links color="#0059a6" size="16px" />
  <top-image src="images/header.webp" alt="San Diego Shows" />
</sdmusic-theme>
```

Put your image files in `images/` or supply direct HTTPS URLs. The background
can repeat in both directions (`repeat`), only horizontally (`repeat-x`), only
vertically (`repeat-y`), or not at all (`no-repeat`). `space` and `round` are
also supported. Choose link colors that are readable against your background.
The top image is centered above the title in a 300 × 300 px square with 10 px
padding on each side; it scales down on narrow screens without cropping.

Preview changes using a local HTTP server or a hosted preview. Opening
`index.html` directly from disk won't load the XML or listings.

## Keeping it accurate

- Missing venue link? Add the venue and city to `venue_links.json`. Matching
  ignores capitalization and extra whitespace; San Diego also accepts `SD`.
  Different cities remain distinct. Verified mappings and special venue labels
  are documented in `docs/venue-link-audit.md`.
- Wrong or missing artist homepage? MusicBrainz results are accepted
  automatically; fix the source of truth at musicbrainz.org and the next
  cache refresh (30 days) picks it up.
- No homepage returned means the artist name stays plain text.

## Listen links

Each artist can have a separate `LISTEN UP!` link, in a new tab. Use the artist's
active MusicBrainz Bandcamp relationship first. Read the first four releases
in Bandcamp's artist-controlled catalog order (usually newest first), choose
the first track with a public streaming file, and link to its actual `/track/`
page. Skip unreleased, private, capped, and non-streamable songs. Track URLs
come from Bandcamp metadata, never guessed titles.

If no usable Bandcamp song is found, use the MusicBrainz Spotify **artist**
URL. With neither, omit the listen link. Spotify Free may play ads or require
sign-in. Bandcamp may impose repeat-stream limits; availability can change
between refreshes. A streaming file indicates availability, not a guarantee
for every listener, region, or account.

Selection happens only in the background, with one-second request spacing,
a bounded request budget, and a pause on Bandcamp 429/503 responses. Other
failed pages are not bypassed. Successful selections cache for seven days;
misses retry after one day. `python listen.py --offline` only uses fresh
cached selections and never makes network requests. There are no embeds,
music SDKs, or third-party requests unless you configure remotely hosted theme
images.

## Files

| File | Purpose |
| --- | --- |
| `collect.py` | Fetch and parse ConcertsSD's by-venue page |
| `enrich.py` | MusicBrainz artist-homepage lookups with cache |
| `venue_links.json` | Venue names to official websites |
| `index.html` | Page markup and listings behavior |
| `sdmusic.css` | Site styles and defaults |
| `sdmusic-theme.xml` | Editable colors, image paths, repeat, and link size |
| `sdmusic-theme.js` | Applies the XML settings to the page |
| `shows.json` | Generated listings |
| `data/artist_cache.json` | Generated MusicBrainz response cache |
| `listen.py` | Background Bandcamp track selection and Spotify fallback |
| `data/listen_cache.json` | Generated track-selection cache, not deployed |
