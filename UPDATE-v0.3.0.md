# Update an existing GitHub repository to v0.3.0

Download and extract `San Diego Shows starter kit-v0.3.0.zip`.
The `VERSION` file should say `0.3.0`. This release removes the mandatory
artist approval gate and accepts MusicBrainz official-homepage results
automatically. It does not require an API key.

## If v0.2.0 code was already uploaded

Replace these files at the repository root:

```text
VERSION
CHANGELOG.md
README.md
MUSICBRAINZ.md
ARTIST-LINKS.md
GITHUB-PAGES-SETUP.md
UPDATE-ARTIST-LINKS.md
UPDATE-v0.3.0.md
artist_enrichment.py
artist_enrichment.json
artist_links.py
index.html
artist_review.md
artist_review.json
```

Also replace these within the existing folders:

```text
data/artist_cache.json
tests/test_artist_enrichment.py
```

Preserve any additional entries in your existing artist cache if it is newer
than the included backfill. Keep your own manual overrides, explicit lineups,
and optional MBID corrections. The v0.2.0 workflow already performs the
required offline rebuild; it does not need another change for this upgrade.

## If only the v0.1.0 version documents were uploaded

You also need the actual enrichment code and workflow. Follow the complete
file/folder checklist in `UPDATE-v0.2.0.md`, but take every file from this
v0.3.0 package, use this release's configuration, and commit as v0.3.0.
The older guide's references to mandatory identity approval are superseded
by `MUSICBRAINZ.md`.

## Preserve current show data

Do not replace a fresher `shows.json` or the seven `data/<venue>.json` source
files with this kit's older venue data. The workflow will rebuild your own
shows from your source caches and the new artist cache.

This package includes a MusicBrainz backfill of the kit's saved list, not a
fresh collection of venue calendars. Your current linked-name count may
differ as your own shows change.

## Commit and deploy

Upload extracted files to the existing repository, preserving folder paths.
Do not upload the ZIP itself. Use `Release starter kit v0.3.0` as the commit
message and commit directly to main if that is your existing workflow.

Check Actions for a successful run. The workflow uses the included cache
without browser-side API calls. Scheduled/manual refreshes discover more
artists automatically; no approval step is required.

For a local artist-only refresh:

```bash
python run.py --from-cache --enrich-artists
```

For an explicit full backfill:

```bash
python artist_enrichment.py --online --max-requests 1200
python run.py --from-cache
```

`artist_review.md` now means unresolved or missing API results, not a
mandatory manual verification queue. Source acceptance can produce a wrong
same-name match; use an optional MBID correction if you spot one.

The assistant has not changed your GitHub repository remotely.
