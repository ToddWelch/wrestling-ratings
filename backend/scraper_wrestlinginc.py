import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.json"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

# Show search queries and their IDs
NIELSEN_SHOWS = {
    "smackdown": "wwe smackdown viewership ratings report",
    "nxt": "wwe nxt viewership ratings report",
    "dynamite": "aew dynamite viewership ratings report",
    "collision": "aew collision viewership ratings report",
    "tna": "tna impact viewership ratings report",
}

STREAMING_SHOWS = {
    "raw": "wwe raw viewership ratings report",
}

# URL patterns to identify ratings articles
RATINGS_URL_RE = re.compile(
    r"wrestlinginc\.com/\d+/"
    r"(?:wwe-(?:smackdown|nxt|raw)|aew-(?:dynamite|collision)|tna-impact)"
    r"[-\w]*(?:viewership|ratings)[-\w]*(?:report|20\d{2})",
    re.IGNORECASE,
)

# Extract date from URL slug like "march-13-2026" or "3-13-2026"
URL_DATE_RE = re.compile(
    r"(?:(\w+)-(\d{1,2})-(\d{4}))"
)

# Patterns for extracting data from article text
VIEWERS_RE = re.compile(r"(\d{1,3}(?:,\d{3})+)\s*viewers", re.IGNORECASE)
DEMO_RE = re.compile(
    r"(?:posted\s+a\s+|earned\s+a\s+|drew\s+a\s+|grew\s+(?:from\s+[\d.]+\s+)?to\s+)?"
    r"(0\.\d{2})\s*(?:rating\s+)?(?:in\s+the\s+)?(?:key\s+)?(?:18-49|ages?\s+18)",
    re.IGNORECASE,
)
# Fallback: first 0.XX number near "18-49" or "demo"
DEMO_FALLBACK_RE = re.compile(r"(0\.\d{2}).*?(?:18-49|demo)", re.IGNORECASE)

# For Raw Netflix global views
GLOBAL_VIEWS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*million\s*(?:global\s*)?views", re.IGNORECASE)


def search_wrestlinginc_articles(show_query, max_results=20):
    """Search Google for recent WrestlingInc ratings articles for a show."""
    search_url = "https://www.google.com/search"
    params = {
        "q": f"site:wrestlinginc.com {show_query} 2026",
        "num": max_results,
    }

    try:
        resp = requests.get(search_url, params=params, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        urls = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Extract URL from Google redirect
            match = re.search(r"url\?q=(https://www\.wrestlinginc\.com/[^&]+)", href)
            if match:
                url = match.group(1)
                if RATINGS_URL_RE.search(url) and url not in urls:
                    urls.append(url)
            elif "wrestlinginc.com" in href and RATINGS_URL_RE.search(href):
                if href not in urls:
                    urls.append(href)

        return urls
    except Exception as e:
        logger.warning("Google search failed for '%s': %s", show_query, e)
        return []


def parse_date_from_url(url):
    """Extract air date from WrestlingInc URL."""
    matches = URL_DATE_RE.findall(url)
    for month_str, day_str, year_str in matches:
        month = MONTHS.get(month_str.lower())
        if month:
            return f"{year_str}-{month:02d}-{int(day_str):02d}"
        # Try numeric month
        try:
            m = int(month_str)
            if 1 <= m <= 12:
                return f"{year_str}-{m:02d}-{int(day_str):02d}"
        except ValueError:
            continue
    return None


def fetch_article_data(url):
    """Fetch and parse viewership/demo data from a WrestlingInc article."""
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "WrestlingRatingsTracker/1.0",
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get article text
        article = soup.find("article") or soup.find("div", class_="entry-content") or soup
        text = article.get_text()

        return text
    except Exception as e:
        logger.warning("Failed to fetch WrestlingInc article %s: %s", url, e)
        return None


def parse_nielsen_article(text, date):
    """Parse viewership and demo from article text."""
    if not text or not date:
        return None

    # Find viewership (first large number + "viewers")
    viewers_match = VIEWERS_RE.search(text)
    if not viewers_match:
        return None

    viewers_raw = viewers_match.group(1).replace(",", "")
    viewers = round(int(viewers_raw) / 1_000_000, 3)

    # Find demo rating
    demo = None
    demo_match = DEMO_RE.search(text)
    if demo_match:
        demo = float(demo_match.group(1))
    else:
        demo_match = DEMO_FALLBACK_RE.search(text)
        if demo_match:
            demo = float(demo_match.group(1))

    if demo is None:
        return None

    return {"date": date, "viewers": viewers, "demo": round(demo, 2)}


def parse_streaming_article(text, date):
    """Parse Raw Netflix global views from article text."""
    if not text or not date:
        return None

    views_match = GLOBAL_VIEWS_RE.search(text)
    if not views_match:
        return None

    viewers = round(float(views_match.group(1)), 1)
    return {"date": date, "viewers": viewers}


def scrape_wrestlinginc():
    """Scrape ratings data from WrestlingInc articles."""
    logger.info("Starting WrestlingInc scrape")

    nielsen = {sid: [] for sid in NIELSEN_SHOWS}
    streaming = {sid: [] for sid in STREAMING_SHOWS}

    # Scrape Nielsen shows
    for show_id, query in NIELSEN_SHOWS.items():
        urls = search_wrestlinginc_articles(query)
        logger.info("Found %d WrestlingInc URLs for %s", len(urls), show_id)

        for url in urls:
            date = parse_date_from_url(url)
            if not date:
                continue

            text = fetch_article_data(url)
            entry = parse_nielsen_article(text, date)
            if entry:
                nielsen[show_id].append(entry)

        nielsen[show_id].sort(key=lambda e: e["date"])
        logger.info("WrestlingInc: %d entries for %s", len(nielsen[show_id]), show_id)

    # Scrape streaming shows (Raw)
    for show_id, query in STREAMING_SHOWS.items():
        urls = search_wrestlinginc_articles(query)
        logger.info("Found %d WrestlingInc URLs for %s", len(urls), show_id)

        for url in urls:
            date = parse_date_from_url(url)
            if not date:
                continue

            text = fetch_article_data(url)
            entry = parse_streaming_article(text, date)
            if entry:
                streaming[show_id].append(entry)

        streaming[show_id].sort(key=lambda e: e["date"])
        logger.info("WrestlingInc: %d streaming entries for %s", len(streaming[show_id]), show_id)

    return {"nielsen": nielsen, "streaming": streaming}
