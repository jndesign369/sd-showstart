# Update your existing GitHub repository

This package updates the kit; it does not change your GitHub repository remotely.
Use the existing repository. You do not need a new Pages setup or a new branch.

1. Download and extract **San Diego Shows starter kit-v0.1.0.zip**. Check that `VERSION` contains `0.1.0`; see `CHANGELOG.md` for the release contents.
2. In your repository's Code tab choose **Add file > Upload files**.
3. Upload these changed or new files, preserving the folder paths:

```text
VERSION
CHANGELOG.md
index.html
run.py
artist_links.py
event_lineups.json
shows.json
scripts/prepare_site.py
tests/test_run.py
tests/test_artist_links.py
README.md
GITHUB-PAGES-SETUP.md
ARTIST-LINKS.md
UPDATE-ARTIST-LINKS.md
```

To also save the target coverage list and audit in your repository, upload
`VENUES.md`, `venues.json`, and `VENUE-COVERAGE.md`. These files are planning
records, not additional enabled scrapers.

The existing `.github/workflows/update.yml` does not need to change. Keep your
other scrapers and cached data files in place. If you have already curated
registry or lineup entries, back them up and migrate using `ARTIST-LINKS.md`
instead of replacing your work with the supplied empty files.

4. Commit directly to `main`. The existing push workflow deploys the snapshot.
5. Check Actions for a successful run, then reload your Pages website.

Confirm: listing titles are not event links; unverified names are plain text;
purchase/event-page links are separate; venue names link to venue websites.

The package's `shows.json` was rebuilt from the included cache, not recollected
live. If your repository has fresher data, keep it and run **Update shows** with
refresh enabled after uploading the code. The new page already refuses old
`band_url` links while fresh data is being prepared.
