# GitHub Pages setup

This kit is prepared for a public repository named `san-diego-shows` with `main` as its default branch. It needs no API keys, personal access tokens, paid scraping services, or repository secrets. Nothing has been uploaded to GitHub or published on your behalf.

## Create and upload the repository

1. Download and extract `San Diego Shows starter kit-v0.1.0.zip` (attachment title: “San Diego Shows starter kit”). Its files are at the archive root, not inside a second `sdshows` folder. The `VERSION` file should contain `0.1.0`; release notes are in `CHANGELOG.md`.
2. Create a new **public** repository on GitHub named `san-diego-shows`. Use `main` as the default branch. Do not add a README, license, or `.gitignore` on GitHub when creating it; the kit already has its own files.
3. Upload the extracted contents to the repository root. Make sure hidden items are included, especially `.github/workflows/update.yml`. Do not upload the ZIP itself or nest the files under `sdshows/`.

For a reliable upload including hidden files, use Git from the extracted directory:

```bash
git init -b main
git add .
git commit -m "Add San Diego Shows starter kit"
git remote add origin https://github.com/YOUR-USERNAME/san-diego-shows.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your actual GitHub username. Authenticate to GitHub using your normal Git setup; do not put credentials into these files.

If using GitHub's browser uploader, check the committed file tree afterward. If `.github` was omitted, choose **Add file > Create new file**, enter `.github/workflows/update.yml`, and paste the exact contents of that file from the kit.

Your repository root must look like this:

```text
.github/workflows/update.yml
.gitignore
VERSION
CHANGELOG.md
index.html
shows.json
run.py
requirements.txt
band_overrides.json
data/
scrapers/
scripts/prepare_site.py
tests/
README.md
GITHUB-PAGES-SETUP.md
```

## Enable Pages and run the first deployment

1. Open **Settings > Pages > Build and deployment** and select **GitHub Actions** as the source.
2. Open **Actions > Update shows > Run workflow**.
3. Select `main` and leave **Scrape venues before deploying** unchecked. This deploys the included snapshot without waiting for scraping.
4. Wait for the `prepare` and `deploy` jobs to finish. The deployment URL appears in the `github-pages` environment and in **Settings > Pages**.
5. Open `https://YOUR-USERNAME.github.io/san-diego-shows/` and test search and a venue filter.

The first push may run before you enable Pages and fail at configuration. Enable Pages, then run the workflow manually again; no code change is required. GitHub documents the deployment environment, permissions, artifact, and deployment requirements in its [custom Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Refresh the snapshot and enable daily operation

Run **Update shows** again with **Scrape venues before deploying** checked. This visits the seven venue sources, saves successful data, commits the updated JSON files, and deploys the updated site.

The schedule is already included: **14:30 UTC daily**, equivalent to **7:30am PDT or 6:30am PST**. Manual and scheduled workflows require the workflow file to exist on the default branch; scheduled runs use that branch and may be delayed by GitHub. Public-repository schedules can be disabled after 60 days without repository activity; the workflow's successful daily data commits normally provide activity, but check Actions if updates stop ([GitHub workflow event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)).

No separate scheduling service is necessary. A push to `main` deploys the current snapshot; it does not launch another full scrape. Documentation-only pushes do not redeploy.

## What is public

The public repository exposes the source code and event data. Only `index.html`, `shows.json`, and `.nojekyll` are uploaded to the Pages deployment artifact; Python scripts, source caches, tests, and workflow files are not part of that artifact.

Do not put personal information or credentials into this public repository. Venue scraping happens on GitHub's runners, not in visitors' browsers; no third-party event API is called by this kit.

## Troubleshooting

- **No Run workflow button:** Confirm `.github/workflows/update.yml` is present on the default branch and GitHub Actions is enabled for the repository.
- **Pages configuration or deployment error:** Select **GitHub Actions** in Settings > Pages. If repository or organization policy blocks Pages, workflow permissions, or actions, an owner must allow them.
- **Data commit denied:** The workflow requests `contents: write`. Branch rules or organization policy may still block bot commits. Do not disable protections blindly; use a separate, unprotected deployment repository or ask the repository owner to allow this workflow's intended data updates.
- **Git push rejected during collection:** Someone pushed while the scraper ran. The workflow refuses to overwrite their work; rerun it from the latest `main`.
- **Pages environment rejects deployment:** Check Settings > Environments > `github-pages`; allow `main` to deploy or obtain required approvals.
- **Site is 404:** Use the exact repository name in the URL, verify `deploy` succeeded, and confirm `index.html` is at the repository root.
- **Old dates or no shows:** The included snapshot is not a fresh scrape. Run the workflow with refresh enabled. The page hides past shows using Pacific dates.
- **One venue fails:** The scraper retains that source's last successful data. Check the footer and Actions logs; source sites can block hosted runners even when local collection works.
- **All venues fail:** The previous snapshot remains intact. The workflow deploys it if build validation passes, then marks the run failed so the collection problem is visible.
- **Artist names are not linked:** Names link only to verified official websites recorded in `band_overrides.json`. Unknown websites remain plain text. See `ARTIST-LINKS.md` for the verification format; old string-only entries no longer enable links.

## Local check before uploading

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/prepare_site.py
```

These commands do not scrape venues. A complete local collection additionally needs `python -m playwright install --with-deps chromium`, followed by `python run.py`.
