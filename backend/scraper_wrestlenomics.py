import re
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from errors import ScrapeError

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.json"

CATEGORY_URLS = [
    "https://wrestlenomics.com/category/tv-ratings/",
    "https://wrestlenomics.com/category/tv-ratings/page/2/",
    "https://wrestlenomics.com/category/tv-ratings/page/3/",
]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Map URL show slugs to our show IDs
NIELSEN_SHOW_MAP = {
    "wwe-smackdown": "smackdown",
    "wwe-nxt": "nxt",
    "aew-dynamite": "dynamite",
    "aew-collision": "collision",
    "tna-impact": "tna",
}

STREAMING_SHOW_MAP = {
    "wwe-raw": "raw",
}

# Parse data directly from URL slugs like:
# wwe-smackdown-mar-13-on-usa-network-1419000-viewers-0-32-p18-49-rating-tv-ratings-analysis
NIELSEN_URL_RE = re.compile(
    r"/(wwe-smackdown|wwe-nxt|aew-dynamite|aew-collision|tna-impact)"
    r"-(\w{3})-(\d{1,2})-on-[\w-]+-(\d+)-viewers-(\d+-\d{2})-p18-49-rating",
)

# Raw on Netflix uses "global-views" instead of "viewers"
STREAMING_URL_RE = re.compile(
    r"/(wwe-raw)"
    r"-(\w{3})-(\d{1,2})-on-netflix-(\d+)-global-views",
)

# Article paths: /tv-ratings/2026/... (until mid-2026), now /articles/2026/...
ARTICLE_YEAR_RE = re.compile(r"/(?:tv-ratings|articles)/(\d{4})/")


def fetch_article_urls():
    """Fetch all TV ratings article URLs from Wrestlenomics category pages."""
    urls = []
    failed_pages = 0
    for cat_url in CATEGORY_URLS:
        try:
            resp = requests.get(cat_url, timeout=30, headers={
                "User-Agent": "WrestlingRatingsTracker/1.0",
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if ARTICLE_YEAR_RE.search(href) and "rating" in href:
                    if href not in urls:
                        urls.append(href)

        except Exception as e:
            failed_pages += 1
            logger.warning("Failed to fetch Wrestlenomics category page %s: %s", cat_url, e)

    if failed_pages == len(CATEGORY_URLS):
        raise ScrapeError("every Wrestlenomics category page failed to load")

    logger.info("Found %d Wrestlenomics article URLs", len(urls))
    return urls


def parse_year_from_url(url):
    """Extract year from URL like /articles/2026/... or /tv-ratings/2026/..."""
    match = ARTICLE_YEAR_RE.search(url)
    return int(match.group(1)) if match else None


def air_date(year, month, day, today=None):
    """ISO air date for a show named in an article published in `year`.

    The URL carries the year the article was published, not the year the
    show aired: a Dec 28 Raw written up in January sits under the new year.
    No show airs after its write-up, so a date more than a day past today
    belongs to the year before. Returns None for an impossible date.
    """
    today = today or datetime.now(timezone.utc).date()
    try:
        aired = date(year, month, day)
        if aired > today + timedelta(days=1):
            aired = date(year - 1, month, day)
    except ValueError:
        logger.warning("Impossible date in Wrestlenomics URL: %s-%s-%s", year, month, day)
        return None
    return aired.isoformat()


def parse_nielsen_from_url(url, today=None):
    """Parse Nielsen show data directly from a Wrestlenomics URL slug."""
    year = parse_year_from_url(url)
    if not year:
        return None

    match = NIELSEN_URL_RE.search(url)
    if not match:
        return None

    show_slug, month_str, day_str, viewers_str, demo_str = match.groups()
    show_id = NIELSEN_SHOW_MAP.get(show_slug)
    if not show_id:
        return None

    month = MONTHS.get(month_str.lower())
    if not month:
        return None

    day = int(day_str)
    # Viewers in URL are raw numbers like 1419000
    viewers = round(int(viewers_str) / 1_000_000, 3)
    # Demo in URL is like "0-32" meaning 0.32
    demo = round(float(demo_str.replace("-", ".")), 2)
    aired = air_date(year, month, day, today)
    if not aired:
        return None

    return {
        "type": "nielsen",
        "show_id": show_id,
        "entry": {"date": aired, "viewers": viewers, "demo": demo},
    }


def parse_streaming_from_url(url, today=None):
    """Parse streaming show data from a Wrestlenomics URL slug."""
    year = parse_year_from_url(url)
    if not year:
        return None

    match = STREAMING_URL_RE.search(url)
    if not match:
        return None

    show_slug, month_str, day_str, views_str = match.groups()
    show_id = STREAMING_SHOW_MAP.get(show_slug)
    if not show_id:
        return None

    month = MONTHS.get(month_str.lower())
    if not month:
        return None

    day = int(day_str)
    # Raw views are in millions in the URL (e.g., 2800000 = 2.8M)
    viewers = round(int(views_str) / 1_000_000, 1)
    aired = air_date(year, month, day, today)
    if not aired:
        return None

    return {
        "type": "streaming",
        "show_id": show_id,
        "entry": {"date": aired, "viewers": viewers},
    }


def scrape_wrestlenomics():
    """Scrape all available data from Wrestlenomics URL slugs."""
    logger.info("Starting Wrestlenomics scrape")
    urls = fetch_article_urls()

    nielsen = {sid: [] for sid in NIELSEN_SHOW_MAP.values()}
    streaming = {sid: [] for sid in STREAMING_SHOW_MAP.values()}

    for url in urls:
        result = parse_nielsen_from_url(url)
        if result:
            nielsen[result["show_id"]].append(result["entry"])
            continue

        result = parse_streaming_from_url(url)
        if result:
            streaming[result["show_id"]].append(result["entry"])

    for show_id, entries in nielsen.items():
        entries.sort(key=lambda e: e["date"])
        logger.info("Wrestlenomics: %d entries for %s", len(entries), show_id)

    for show_id, entries in streaming.items():
        entries.sort(key=lambda e: e["date"])
        logger.info("Wrestlenomics: %d streaming entries for %s", len(entries), show_id)

    total = sum(len(v) for v in nielsen.values()) + sum(len(v) for v in streaming.values())
    if total == 0:
        raise ScrapeError(
            f"Wrestlenomics returned {len(urls)} article links but none parsed "
            "into ratings (URL format changed?)"
        )

    return {"nielsen": nielsen, "streaming": streaming}
