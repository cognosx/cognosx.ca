"""Refresh the Insights feeds.

Writes:
  data/substack.yml      newest newsletter posts (from the Substack RSS feed)
  data/publications.yml  publications (from OpenAlex, by ORCID)

Runs every day on GitHub (see .github/workflows/publish.yml).
Run it yourself with:  python scripts/update_feeds.py

If a source cannot be reached, the existing file is kept unchanged,
so the site never loses content because of a temporary error.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import feedparser
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "scripts" / "feeds.yml").read_text(encoding="utf-8"))
HEADERS = {"User-Agent": "cognosx-site/1.0 (mailto:cognosxx@gmail.com)"}

HEADER = (
    "# This file is written automatically by scripts/update_feeds.py.\n"
    "# Edits here are replaced at the next update; change scripts/feeds.yml instead.\n"
)


def clean(text: str, limit: int = 220) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def write(name: str, items: list[dict]) -> None:
    path = ROOT / "data" / name
    body = yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=1000) if items else "[]\n"
    path.write_text(HEADER + body, encoding="utf-8")
    print(f"  wrote {len(items)} items to data/{name}")


def update_substack() -> None:
    url = (CONFIG.get("substack_url") or "").strip().rstrip("/")
    if not url:
        print("Substack: no address set in scripts/feeds.yml, skipping.")
        return
    print(f"Substack: reading {url}/feed")
    feed = feedparser.parse(f"{url}/feed", request_headers=HEADERS)
    if feed.bozo and not feed.entries:
        print(f"  could not read the feed ({feed.bozo_exception}); keeping the old file.")
        return
    items = []
    for e in feed.entries[: CONFIG.get("max_items", 40)]:
        published = e.get("published_parsed") or e.get("updated_parsed")
        items.append({
            "title": clean(e.get("title", ""), 200),
            "path": e.get("link", url),
            "date": f"{published.tm_year:04d}-{published.tm_mon:02d}-{published.tm_mday:02d}" if published else None,
            "description": clean(e.get("summary", "")),
            "categories": ["Newsletter"],
        })
    write("substack.yml", items)


def update_publications() -> None:
    orcid = (CONFIG.get("orcid") or "").strip()
    if not orcid:
        print("Publications: no ORCID set, skipping.")
        return
    since = int(CONFIG.get("publications_since", 2000))
    types = set(CONFIG.get("publication_types") or [])
    hidden = {d.lower() for d in (CONFIG.get("hide_dois") or [])}
    print(f"Publications: reading OpenAlex for ORCID {orcid}")
    try:
        r = requests.get(
            "https://api.openalex.org/works",
            params={
                "filter": f"author.orcid:{orcid},from_publication_date:{since}-01-01",
                "sort": "publication_date:desc",
                "per-page": 100,
                "mailto": "cognosxx@gmail.com",
            },
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        works = r.json().get("results", [])
    except Exception as exc:  # keep the old file on any network problem
        print(f"  could not reach OpenAlex ({exc}); keeping the old file.")
        return

    items, seen = [], set()
    for w in works:
        if types and w.get("type") not in types:
            continue
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        title = clean(w.get("display_name") or w.get("title") or "", 220)
        key = doi or title.lower()
        if not title or key in seen or doi in hidden:
            continue
        seen.add(key)
        source = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        topic = ((w.get("primary_topic") or {}).get("field") or {}).get("display_name")
        kind = "Preprint" if w.get("type") == "preprint" else "Publication"
        items.append({
            "title": title,
            "path": f"https://doi.org/{doi}" if doi else (w.get("id") or ""),
            "date": w.get("publication_date"),
            "description": source,
            "categories": [c for c in [kind, topic] if c],
        })
        if len(items) >= CONFIG.get("max_items", 40):
            break

    if not items:
        print("  OpenAlex returned no matching works; keeping the old file.")
        return
    write("publications.yml", items)


if __name__ == "__main__":
    update_substack()
    update_publications()
    sys.exit(0)
