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
| Change the booking link, workshop date, waitlist or newsletter link | `_variables.yml` |
| Change text on a page | the page's `.qmd` file (e.g. `services.qmd`, `about.qmd`) |
| Add a dashboard | copy `dashboards/_template.qmd`, follow the notes inside |
| Write an article on the site | copy `posts/_template.qmd`, follow the notes inside |
| Show newsletter posts automatically | put your Substack address in `scripts/feeds.yml` |
| Hide a publication | add its DOI to `hide_dois` in `scripts/feeds.yml` |
| Show a LinkedIn post | add it to `data/linkedin.yml` (LinkedIn has no open feed) |
| Change colours or fonts | `styles/brand.scss` (brand colours are at the top) |
| Change the menu | `_quarto.yml` |

Publications come from OpenAlex using your ORCID, so a new paper appears by itself once OpenAlex lists it.

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
