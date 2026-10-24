"""Refresh the site's automatic content.

Writes:
  data/publications.yml  research outputs from OpenAlex (by ORCID)   -> Work page
  data/substack.yml      every Substack post (articles, podcasts...)  -> Insights page
  data/youtube.yml       every YouTube video                          -> Insights page

Every item is also linked to the projects it belongs to, using the
"match" rules written at the top of each file in projects/.

Runs every day on GitHub (see .github/workflows/publish.yml).
Run it yourself with:  python scripts/update_feeds.py

If a source cannot be reached, its file is kept unchanged, so the site
never loses content because of a temporary error.
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

import feedparser
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "scripts" / "feeds.yml").read_text(encoding="utf-8"))
HEADERS = {"User-Agent": "cognosx-site/1.0 (mailto:contact@cognosx.ca)"}

HEADER = (
    "# This file is written automatically by scripts/update_feeds.py.\n"
    "# Edits here are replaced at the next update; change scripts/feeds.yml instead.\n"
)


# ---------------------------------------------------------------- helpers

def clean(text: str, limit: int = 220) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def read(name: str) -> list[dict]:
    path = ROOT / "data" / name
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def write(name: str, items: list[dict]) -> None:
    path = ROOT / "data" / name
    body = yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=1000) if items else "[]\n"
    path.write_text(HEADER + body, encoding="utf-8")
    print(f"  wrote {len(items)} items to data/{name}")


def merge(new: list[dict], old: list[dict]) -> list[dict]:
    """Keep older items that a feed no longer lists (feeds only show the latest ones)."""
    seen = {i.get("path") for i in new}
    kept = [link_projects(i) for i in old if i.get("path") and i.get("path") not in seen]
    items = new + kept
    items.sort(key=lambda i: str(i.get("date") or ""), reverse=True)
    return items


# ---------------------------------------------------------------- projects

def load_projects() -> list[dict]:
    """Read the match rules from the front matter of each projects/*.qmd file."""
    projects = []
    folder = ROOT / "projects"
    for qmd in sorted(folder.glob("*.qmd")) if folder.exists() else []:
        if qmd.name.startswith("_"):
            continue
        text = qmd.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        match = meta.get("match") or {}
        projects.append({
            "slug": qmd.stem,
            "title": meta.get("title", qmd.stem),
            "keywords": [str(k).lower() for k in match.get("keywords") or []],
            "links": [str(l).lower() for l in match.get("links") or []],
        })
    return projects


PROJECTS = load_projects()


def link_projects(item: dict, extra_text: str = "") -> dict:
    """Add 'projects' (project page names) and 'project_names' to an item."""
    # Peer review reports are about other people's work, so they never belong to a project.
    if "Peer review report" in (item.get("categories") or []):
        item.pop("projects", None)
        item.pop("project_names", None)
        return item
    text = " ".join([item.get("title") or "", item.get("description") or "", extra_text]).lower()
    path = (item.get("path") or "").lower()
    found = []
    for p in PROJECTS:
        if any(l and l in path for l in p["links"]) or any(
            re.search(r"\b" + re.escape(k) + r"\b", text) for k in p["keywords"]
        ):
            found.append(p["slug"])
    if found:
        names = {p["slug"]: p["title"] for p in PROJECTS}
        item["projects"] = found
        item["project_names"] = [names.get(s, s) for s in found]
    else:
        item.pop("projects", None)
        item.pop("project_names", None)
    return item


# ---------------------------------------------------------------- Substack

SUBSTACK_TYPES = {"newsletter": "Article", "podcast": "Podcast", "thread": "Discussion", "video": "Video"}


def update_substack() -> None:
    url = (CONFIG.get("substack_url") or "").strip().rstrip("/")
    if not url:
        print("Substack: no address set in scripts/feeds.yml, skipping.")
        return
    print(f"Substack: reading the full archive of {url}")
    items: list[dict] = []
    try:
        offset = 0
        while True:
            r = requests.get(f"{url}/api/v1/archive", params={"sort": "new", "offset": offset, "limit": 50},
                             headers=HEADERS, timeout=30)
            r.raise_for_status()
            posts = r.json()
            if not posts:
                break
            for p in posts:
                tags = [t.get("name", "") for t in (p.get("postTags") or [])]
                item = {
                    "title": clean(p.get("title", ""), 200),
                    "path": p.get("canonical_url") or f"{url}/p/{p.get('slug', '')}",
                    "date": (p.get("post_date") or "")[:10] or None,
                    "description": clean(p.get("subtitle") or p.get("description") or ""),
                    "categories": ["Substack", SUBSTACK_TYPES.get(p.get("type"), "Article")],
                    "tags": tags,
                }
                items.append(link_projects(item, " ".join(tags)))
            offset += len(posts)
            if len(posts) < 50 or offset > 2000:
                break
    except Exception as exc:
        print(f"  archive not available ({exc}); trying the RSS feed instead.")
        items = []
        feed = feedparser.parse(f"{url}/feed", request_headers=HEADERS)
        if feed.bozo and not feed.entries:
            print("  could not read the feed; keeping the old file.")
            return
        for e in feed.entries:
            d = e.get("published_parsed")
            kind = "Podcast" if any("audio" in (l.get("type") or "") for l in e.get("links", [])) else "Article"
            tags = [t.get("term", "") for t in e.get("tags", [])]
            item = {
                "title": clean(e.get("title", ""), 200),
                "path": e.get("link", url),
                "date": f"{d.tm_year:04d}-{d.tm_mon:02d}-{d.tm_mday:02d}" if d else None,
                "description": clean(e.get("summary", "")),
                "categories": ["Substack", kind],
                "tags": tags,
            }
            items.append(link_projects(item, " ".join(tags)))
    if not items:
        print("  no posts found; keeping the old file.")
        return
    write("substack.yml", merge(items, read("substack.yml")))


# ---------------------------------------------------------------- YouTube

def youtube_type(title: str, link: str, playlist_type: str | None) -> str:
    if playlist_type:
        return playlist_type
    if "/shorts/" in link:
        return "Short"
    if any(k in title.lower() for k in CONFIG.get("youtube_tutorial_words") or []):
        return "Tutorial"
    return "Video"


def update_youtube() -> None:
    channel = (CONFIG.get("youtube_channel_id") or "").strip()
    if not channel:
        print("YouTube: no channel id set, skipping.")
        return
    print(f"YouTube: reading channel {channel}")

    # Videos placed in a playlist take that playlist's type (e.g. Tutorial).
    playlist_types: dict[str, str] = {}
    for pid, label in (CONFIG.get("youtube_playlists") or {}).items():
        f = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}", request_headers=HEADERS)
        for e in f.entries:
            playlist_types[e.get("yt_videoid", "")] = label

    raw: list[dict] = []
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if key:  # optional: the API lists every video; the free feed only the latest 15
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                             params={"part": "contentDetails", "id": channel, "key": key}, timeout=30)
            uploads = r.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            token = None
            while True:
                r = requests.get("https://www.googleapis.com/youtube/v3/playlistItems",
                                 params={"part": "snippet", "playlistId": uploads, "maxResults": 50,
                                         "pageToken": token, "key": key}, timeout=30)
                data = r.json()
                for it in data.get("items", []):
                    s = it["snippet"]
                    vid = s["resourceId"]["videoId"]
                    raw.append({"id": vid, "title": s.get("title", ""), "date": s.get("publishedAt", "")[:10],
                                "link": f"https://www.youtube.com/watch?v={vid}", "summary": s.get("description", "")})
                token = data.get("nextPageToken")
                if not token:
                    break
        except Exception as exc:
            print(f"  API failed ({exc}); using the free feed.")
            raw = []
    if not raw:
        feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}",
                                request_headers=HEADERS)
        if feed.bozo and not feed.entries:
            print("  could not read the channel feed; keeping the old file.")
            return
        for e in feed.entries:
            d = e.get("published_parsed")
            raw.append({"id": e.get("yt_videoid", ""), "title": e.get("title", ""),
                        "date": f"{d.tm_year:04d}-{d.tm_mon:02d}-{d.tm_mday:02d}" if d else None,
                        "link": e.get("link", ""), "summary": e.get("summary", "")})

    items = []
    for v in raw:
        item = {
            "title": clean(v["title"], 200),
            "path": v["link"],
            "date": v["date"],
            "description": clean(v["summary"], 180),
            "categories": ["YouTube", youtube_type(v["title"], v["link"], playlist_types.get(v["id"]))],
        }
        items.append(link_projects(item))
    if not items:
        print("  no videos found; keeping the old file.")
        return
    write("youtube.yml", merge(items, read("youtube.yml")))


# ---------------------------------------------------------------- OpenAlex

def abstract_text(w: dict) -> str:
    inv = w.get("abstract_inverted_index") or {}
    pos = {}
    for word, places in inv.items():
        for i in places:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def output_type(w: dict) -> str | None:
    title = (w.get("display_name") or "").lower()
    source = (((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "").lower()
    doi = (w.get("doi") or "").lower()
    where = f"{title} {source} {doi}"
    if any(m.lower() in where for m in CONFIG.get("technical_markers") or []):
        return CONFIG["type_labels"]["technical"]
    if w.get("type") == "other" and any(m.lower() in title for m in CONFIG.get("dataset_markers") or []):
        return CONFIG["type_labels"]["dataset"]
    key = (CONFIG.get("openalex_types") or {}).get(w.get("type"))
    return CONFIG["type_labels"].get(key) if key else None


def theme(w: dict, abstract: str) -> str | None:
    if w.get("type") == "review":
        return "Review"
    text = " ".join([
        w.get("display_name") or "", abstract,
        " ".join((t.get("display_name") or "") + " " + ((t.get("subfield") or {}).get("display_name") or "")
                 for t in (w.get("topics") or [])),
    ]).lower()
    if any(k.lower() in text for k in CONFIG.get("review_keywords") or []):
        return "Review"
    if any(k.lower() in text for k in CONFIG.get("bibliometric_keywords") or []):
        return "Bibliometrics"
    return None


def update_publications() -> None:
    orcid = (CONFIG.get("orcid") or "").strip()
    if not orcid:
        print("Publications: no ORCID set, skipping.")
        return
    since = int(CONFIG.get("publications_since", 2000))
    hidden = {d.lower() for d in (CONFIG.get("hide_dois") or [])}
    always = {d.lower() for d in (CONFIG.get("include_dois") or [])}
    filtered_types = set(CONFIG.get("theme_filter_applies_to") or [])
    print(f"Publications: reading OpenAlex for ORCID {orcid} (from {since})")
    try:
        r = requests.get(
            "https://api.openalex.org/works",
            params={"filter": f"author.orcid:{orcid},from_publication_date:{since}-01-01",
                    "sort": "publication_date:desc", "per-page": 100, "mailto": "contact@cognosx.ca"},
            headers=HEADERS, timeout=30,
        )
        r.raise_for_status()
        works = r.json().get("results", [])
    except Exception as exc:
        print(f"  could not reach OpenAlex ({exc}); keeping the old file.")
        return

    items, seen = [], set()
    for w in works:
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        title = clean(w.get("display_name") or w.get("title") or "", 220)
        if not title or doi in hidden:
            continue
        forced = doi in always
        kind = output_type(w) or (CONFIG["type_labels"]["article"] if forced else None)
        if not kind:
            continue
        abstract = abstract_text(w)
        topic = theme(w, abstract)
        if kind in filtered_types and not topic and not forced:
            continue
        key = (re.sub(r"[^a-z0-9]", "", title.lower()), kind)
        if key in seen:
            continue
        seen.add(key)
        source = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        item = {
            "title": title,
            "path": f"https://doi.org/{doi}" if doi else (w.get("id") or ""),
            "date": w.get("publication_date"),
            "description": source,
            "categories": [c for c in [kind, topic] if c],
        }
        items.append(link_projects(item, abstract))
        if len(items) >= CONFIG.get("max_items", 60):
            break

    if not items:
        print("  no publications match the rules; keeping the old file.")
        return
    write("publications.yml", items)


if __name__ == "__main__":
    print(f"Projects found: {', '.join(p['slug'] for p in PROJECTS) or 'none'}")
    update_substack()
    update_youtube()
    update_publications()
    sys.exit(0)
