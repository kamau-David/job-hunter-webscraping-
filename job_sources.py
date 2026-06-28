"""
job_sources.py

Pulls job listings from free, public, ToS-friendly sources:
  - RemoteOK        https://remoteok.com/api
  - Arbeitnow       https://arbeitnow.com/api/job-board-api
  - We Work Remotely (RSS feeds, parsed with feedparser)

Every fetcher returns a list of dicts normalized to this shape:
{
    "id": str,            # stable unique id (used for de-duplication)
    "title": str,
    "company": str,
    "location": str,
    "remote": bool,
    "tags": list[str],
    "description": str,   # plain text, HTML stripped
    "url": str,
    "source": str,
}

Each fetcher is defensive: network errors or unexpected response shapes
are caught and logged, returning an empty list rather than crashing the
whole pipeline.
"""

from __future__ import annotations

import html
import re
import logging
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "job-hunter-bot/1.0 (personal use; contact: you@example.com)"}
TIMEOUT = 15


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities — good enough for job descriptions."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_remoteok() -> list[dict[str, Any]]:
    """Fetch listings from RemoteOK's public JSON API."""
    url = "https://remoteok.com/api"
    jobs: list[dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("RemoteOK fetch failed: %s", exc)
        return jobs

    # The first element is a legal/metadata notice, not a job — skip it.
    for item in data:
        if not isinstance(item, dict) or "id" not in item or "position" not in item:
            continue
        jobs.append({
            "id": f"remoteok:{item.get('id')}",
            "title": item.get("position", "").strip(),
            "company": item.get("company", "").strip(),
            "location": item.get("location", "Remote") or "Remote",
            "remote": True,
            "tags": [t.strip() for t in item.get("tags", []) if isinstance(t, str)],
            "description": _strip_html(item.get("description", "")),
            "url": item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}",
            "source": "RemoteOK",
        })
    log.info("RemoteOK: %d jobs fetched", len(jobs))
    return jobs


def fetch_arbeitnow() -> list[dict[str, Any]]:
    """Fetch listings from Arbeitnow's public job board API (first page)."""
    url = "https://arbeitnow.com/api/job-board-api"
    jobs: list[dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", [])
    except Exception as exc:
        log.warning("Arbeitnow fetch failed: %s", exc)
        return jobs

    for item in data:
        jobs.append({
            "id": f"arbeitnow:{item.get('slug')}",
            "title": item.get("title", "").strip(),
            "company": item.get("company_name", "").strip(),
            "location": item.get("location", "") or ("Remote" if item.get("remote") else ""),
            "remote": bool(item.get("remote")),
            "tags": item.get("tags", []) or [],
            "description": _strip_html(item.get("description", "")),
            "url": item.get("url", ""),
            "source": "Arbeitnow",
        })
    log.info("Arbeitnow: %d jobs fetched", len(jobs))
    return jobs


# categories with slugs confirmed to work on We Work Remotely's public RSS
WWR_CATEGORIES = [
    "remote-programming-jobs",
    "remote-full-stack-programming-jobs",
    "remote-back-end-programming-jobs",
    "remote-data-jobs",
]


def fetch_weworkremotely() -> list[dict[str, Any]]:
    """Fetch listings from We Work Remotely's public per-category RSS feeds."""
    try:
        import feedparser  # local import: optional dependency, only needed here
    except ImportError:
        log.warning("feedparser not installed — skipping We Work Remotely. "
                    "Install with: pip install feedparser")
        return []

    jobs: list[dict[str, Any]] = []
    for category in WWR_CATEGORIES:
        feed_url = f"https://weworkremotely.com/categories/{category}.rss"
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                log.warning("WWR feed '%s' failed to parse", category)
                continue
        except Exception as exc:
            log.warning("WWR fetch failed for %s: %s", category, exc)
            continue

        for entry in feed.entries:
            title_full = entry.get("title", "")
            # WWR titles are usually "Company: Job Title"
            if ":" in title_full:
                company, title = title_full.split(":", 1)
            else:
                company, title = "", title_full
            jobs.append({
                "id": f"wwr:{entry.get('id', entry.get('link', title_full))}",
                "title": title.strip(),
                "company": company.strip(),
                "location": "Remote",
                "remote": True,
                "tags": [category.replace("remote-", "").replace("-jobs", "")],
                "description": _strip_html(entry.get("summary", "")),
                "url": entry.get("link", ""),
                "source": "We Work Remotely",
            })
    log.info("We Work Remotely: %d jobs fetched", len(jobs))
    return jobs


def fetch_all_jobs() -> list[dict[str, Any]]:
    """Fetch from every source and de-duplicate by id."""
    all_jobs = fetch_remoteok() + fetch_arbeitnow() + fetch_weworkremotely()
    seen: set[str] = set()
    deduped = []
    for job in all_jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            deduped.append(job)
    log.info("Total unique jobs fetched: %d", len(deduped))
    return deduped


if __name__ == "__main__":
    for j in fetch_all_jobs()[:5]:
        print(f"[{j['source']}] {j['title']} @ {j['company']} — {j['url']}")
