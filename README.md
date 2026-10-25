# cognosx.ca

The CognosX website, built with [Quarto](https://quarto.org) and published free on GitHub Pages.
It rebuilds itself every day and every time you save a change.

## Put it online (once)

1. **Create the repository.** On github.com/cognosx, click **New repository**, name it `cognosx.ca`, make it **Public**, and create it.
2. **Upload the files.** Click **uploading an existing file**, drag in everything from this folder (including the hidden `.github` folder), and click **Commit changes**.
   If the `.github` folder does not upload, create the file `.github/workflows/publish.yml` by hand with **Add file → Create new file** and paste its content.
3. **Turn on Pages.** In the repository: **Settings → Pages → Source: GitHub Actions**.
4. **Allow the daily update to save feeds.** **Settings → Actions → General → Workflow permissions → Read and write permissions → Save**.
5. **First build.** Open the **Actions** tab and wait for the green tick (2–4 minutes).
6. **Connect cognosx.ca.** In Hostinger: **Domaines → cognosx.ca → DNS / Serveurs de noms**:
   - Delete any existing `A`, `AAAA` or `CNAME` records for `@` and `www` that Hostinger added by default.
   - Add four `A` records for `@`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - Add a `CNAME` record: name `www`, target `cognosx.github.io`
   - Keep the `MX` records (they are for email).
7. Back in GitHub **Settings → Pages**: under **Custom domain** type `cognosx.ca`, save, and when it allows, tick **Enforce HTTPS**. DNS can take a few hours.

## Everyday changes

You can edit any file directly on github.com: open it, click the pencil, change, **Commit changes**. The site updates in a few minutes.

| I want to… | Edit this |
| --- | --- |
| Change the booking link, collaboration form, workshop date, waitlist or newsletter link | `_variables.yml` |
| Change text on a page | the page's `.qmd` file (e.g. `services.qmd`, `about.qmd`) |
| Add a project | copy `projects/_template.qmd`, follow the notes inside |
| Update a project's stage, plan or team | its file in `projects/` (change `stage`, `stage_note` and `updated` at the top) |
| Add a workshop | copy `ateliers/_template.qmd`, follow the notes inside (also add it as a choice in the Google registration form) |
| Mark a workshop as past, full or coming soon | its file in `ateliers/` (change `status`) |
| Add a dashboard | copy `dashboards/_template.qmd`, follow the notes inside |
| Change the Substack or YouTube source, or video types | `scripts/feeds.yml` |
| Hide a publication | add its DOI to `hide_dois` in `scripts/feeds.yml` |
| Add a proposal, framework, report or dataset by hand | `data/outputs.yml` (example inside) |
| Change which types appear, or the review/bibliometric rule | `scripts/feeds.yml` |
| Store a PDF on the site | put it in `files/`, then link it from `data/outputs.yml` |
| Show a LinkedIn post | add it to `data/linkedin.yml` (LinkedIn has no open feed; add `projects: ["file-name"]` to link it to a project) |
| Change colours or fonts | `styles/brand.scss` (brand colours are at the top) |
| Change the menu | `_quarto.yml` |

## How the site is organised

- **Projects**: one page per project in `projects/`. Each page gathers its outputs automatically: any paper, Substack post or video whose words match the project's `match > keywords` appears under "Outputs so far".
- **Work**: formal outputs from OpenAlex (by ORCID), sorted by type, plus hand-added items from `data/outputs.yml` and dashboards.
- **Insights**: every Substack post and YouTube video (automatic), plus LinkedIn posts you add by hand.

Tip: deposit datasets, protocols and reports on Zenodo with your ORCID; they get a DOI and reach Work automatically.

## All YouTube videos (optional)

The free YouTube feed shows the latest 15 videos; older ones stay once the site has seen them.
To import every video at once: create a free API key in Google Cloud (YouTube Data API v3),
then in GitHub go to **Settings → Secrets and variables → Actions → New repository secret**,
name it `YOUTUBE_API_KEY` and paste the key.

## Booking calls

Create a free page on [Cal.com](https://cal.com) or Calendly, connect your Google Calendar,
then paste its link as `booking_url` in `_variables.yml`. Every "Book a call" button updates.
To show the calendar on the Contact page, follow the note at the top of `contact.qmd`.

## Preview on your computer (optional)

Install Quarto, then in this folder run `quarto preview`.

## Folder map

```
_quarto.yml          site settings and menu
_variables.yml       links and dates used across pages
index.qmd …          one file per page
dashboards/          one file per dashboard (+ files/ for Plotly HTML)
posts/               articles written on the site
data/                feeds for the Insights page (updated daily)
scripts/             the daily feed updater and its settings
styles/              brand colours, fonts, small scripts
images/              logo, favicon, dot pattern
.github/workflows/   the daily build and publish job
```
