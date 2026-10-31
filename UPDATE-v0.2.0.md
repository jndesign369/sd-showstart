# Update an existing GitHub repository to v0.2.0

Historical upgrade checklist: the current release is **v0.3.0**. Follow
[UPDATE-v0.3.0.md](UPDATE-v0.3.0.md) for current instructions and take files
from that release's ZIP. The v0.2.0 manual identity-approval requirement has
been removed; the file/path checklist below remains useful for repositories
that have not yet uploaded any enrichment code.

Use your existing repository. Download and extract
`San Diego Shows starter kit-v0.2.0.zip`, then check that `VERSION` says
`0.2.0`. Do not upload the ZIP itself or create a second repository.

## Files to add or replace

Upload these at the repository root, preserving their paths:

```text
VERSION
CHANGELOG.md
README.md
GITHUB-PAGES-SETUP.md
UPDATE-ARTIST-LINKS.md
UPDATE-v0.2.0.md
ARTIST-LINKS.md
MUSICBRAINZ.md
index.html
run.py
artist_links.py
artist_enrichment.py
artist_enrichment.json
artist_identities.json
artist_review.json
artist_review.md
```

Upload these inside the existing folders, not at the root:

```text
data/artist_cache.json
scripts/prepare_site.py
tests/test_artist_enrichment.py
tests/test_artist_links.py
tests/test_run.py
```

The v0.2.0 workflow must also replace the existing file at this exact path:

```text
.github/workflows/update.yml
```

Your file manager may hide `.github`. In GitHub, open the existing
`.github/workflows/update.yml`, click the pencil/edit button, and replace its
contents with the kit's workflow. Do not create a root-level `update.yml` or
a second unrelated workflow.

If the saved venue list/audit is not already in the repository, also add
`VENUES.md`, `venues.json`, and `VENUE-COVERAGE.md`. These do not enable
additional venue collectors.

## Preserve your data and approvals

Do not replace fresher `shows.json` or the seven existing `data/<venue>.json`
files with the kit's older venue snapshot. The updated workflow rebuilds
`shows.json` from your own source caches and the included artist cache.
If `band_overrides.json` or `event_lineups.json` is missing, add the kit's
copy; otherwise keep your existing contents. The validator and earlier
artist-link tests in the list above ensure that presentation-only fixes
are included even if you previously uploaded only the version documents.

Do not overwrite a customized `band_overrides.json`, `event_lineups.json`,
`artist_identities.json`, `artist_enrichment.json`, or `data/artist_cache.json`
without merging your edits. If upgrading directly from v0.1.0, the last three
files are new. Retain any of your existing tests and scraper files.

## Commit and check

Use the commit message `Release starter kit v0.2.0`. Committing directly to
main is appropriate for the existing single-maintainer workflow.

Open Actions and inspect the newest run. The updated workflow performs an
offline snapshot rebuild for an ordinary push. The three shipped approved
identities can link immediately while their API cache remains fresh.
Your actual linked names/count may differ if your show dates have advanced.

If further artist details are needed, open the Update shows workflow,
choose Run workflow, and check the refresh option. That refreshes venue
calendars as well as allowing bounded artist lookups. Unapproved identities
still require review in `artist_review.md`; no key or GitHub secret is needed.

For a local artist-only online refresh without re-scraping venue calendars:

```bash
python run.py --from-cache --enrich-artists
```

This package has not been pushed to your repository by the assistant.
