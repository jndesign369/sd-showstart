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
```

Run the tests first if you changed anything:

```bash
python -m unittest discover -s tests
```

## Twice-daily automatic updates (GitHub Pages)

1. Push this folder to a GitHub repository.
2. In the repository: Settings → Pages → Deploy from a branch → `main`, `/ (root)`.
3. The included `.github/workflows/update.yml` runs at 7:30am and 7:30pm
   Pacific, runs the tests, refreshes `shows.json`, and commits.

The workflow makes two requests to ConcertsSD per run (their robots.txt asks
for a 10-second crawl delay, which the collector observes) and only queries
MusicBrainz for artist names it has not seen before.

## Keeping it accurate

- Missing venue link? Add the venue (spelled exactly as ConcertsSD spells it,
  including the city) to `venue_links.json`.
- Wrong or missing artist homepage? MusicBrainz results are accepted
  automatically; fix the source of truth at musicbrainz.org and the next
  cache refresh (30 days) picks it up.
- No homepage returned means the artist name stays plain text.

## Files

| File | Purpose |
| --- | --- |
| `collect.py` | Fetch and parse ConcertsSD's by-venue page |
| `enrich.py` | MusicBrainz artist-homepage lookups with cache |
| `venue_links.json` | Venue names to official websites |
| `index.html` | The whole site |
| `shows.json` | Generated listings |
| `data/artist_cache.json` | Generated MusicBrainz response cache |
