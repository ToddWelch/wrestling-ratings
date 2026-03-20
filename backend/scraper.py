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

URLS = {
    2025: "https://www.wrestlingattitude.com/p/2025-wwe-aew-viewership-and-key-demo-ratings.html",
    2026: "https://www.wrestlingattitude.com/p/2026-wwe-aew-viewership-and-key-demo-ratings.html",
}

SHOW_SECTIONS = {
    "smackdown": "WWE SmackDown",
    "nxt": "WWE NXT",
    "dynamite": "AEW Dynamite",
    "collision": "AEW Collision",
    "tna": "TNA iMPACT",
}

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# Pattern: "Jan 2: 1,175 - 0.28 key demo rating"
# The comma in viewer number is European-style decimal separator: 1,175 = 1.175M
ENTRY_RE = re.compile(
    r"(\w{3})\s+(\d{1,2}):\s*([\d,\.]+)\s*[-\u2013\u2014]+\s*([\d.]+)\s*key\s*demo\s*rating",
    re.IGNORECASE,
)


def fetch_page(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "WrestlingRatingsTracker/1.0"})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_viewer_number(raw):
    """Parse viewer string where comma = decimal. '1,175' -> 1.175, '0,990' -> 0.990"""
    cleaned = raw.replace(",", ".")
    return round(float(cleaned), 3)


def extract_show_data(text, year):
    entries = []
    for match in ENTRY_RE.finditer(text):
        month_str, day_str, viewers_raw, demo_raw = match.groups()
        month = MONTHS.get(month_str)
        if not month:
            continue
        day = int(day_str)
        try:
            viewers = parse_viewer_number(viewers_raw)
            demo = round(float(demo_raw), 2)
            date = f"{year}-{month:02d}-{day:02d}"
            entries.append({"date": date, "viewers": viewers, "demo": demo})
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse entry: %s - %s", match.group(), e)
            continue
    return entries


def find_show_section(soup, show_name):
    """Find text block for a show section by looking for the bold header."""
    text = soup.get_text()
    # Look for the show header pattern
    pattern = re.compile(
        rf"{re.escape(show_name)}\s*\(Million Viewers\)\s*:?\s*\n(.*?)(?=\n\s*\*\*|\n\s*$|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        return match.group(0)

    # Fallback: find all text after the show name header until next show header
    parts = re.split(r"\*\*[^*]+\(Million Viewers\)[^*]*\*\*", text)
    headers = re.findall(r"\*\*([^*]+)\(Million Viewers\)[^*]*\*\*", text)

    for i, header in enumerate(headers):
        if show_name.lower() in header.lower():
            if i + 1 < len(parts):
                return parts[i + 1]
    return None


def scrape_nielsen():
    """Scrape all Nielsen data from WrestlingAttitude."""
    logger.info("Starting Nielsen scrape")
    all_data = {show_id: [] for show_id in SHOW_SECTIONS}

    for year, url in URLS.items():
        try:
            soup = fetch_page(url)
            page_text = soup.get_text()
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            continue

        for show_id, show_name in SHOW_SECTIONS.items():
            # Find the section for this show
            section_text = find_show_section(soup, show_name)
            if not section_text:
                logger.info("No section found for %s on %d page", show_name, year)
                continue

            # Clean up "(on SyFy)" annotations
            section_text = re.sub(r"\(on SyFy\)", "", section_text)

            entries = extract_show_data(section_text, year)
            all_data[show_id].extend(entries)
            logger.info("Parsed %d entries for %s (%d)", len(entries), show_name, year)

    return all_data


def save_nielsen_data(new_data):
    """Merge new Nielsen data into ratings.json. Never overwrite with less data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    current = {}
    if RATINGS_FILE.exists():
        with open(RATINGS_FILE) as f:
            current = json.load(f)

    if not current:
        current = {
            "lastUpdated": None,
            "scrapeStatus": {"nielsen": "pending", "youtube": "pending"},
            "nielsen": {"smackdown": [], "nxt": [], "dynamite": [], "collision": [], "tna": []},
            "streaming": {"raw": [], "roh": [], "nwa": []},
        }

    nielsen = current.get("nielsen", {})
    for show_id, entries in new_data.items():
        existing = nielsen.get(show_id, [])
        if len(entries) >= len(existing):
            nielsen[show_id] = sorted(entries, key=lambda e: e["date"])
        else:
            logger.warning(
                "New data for %s has fewer entries (%d vs %d), keeping existing",
                show_id, len(entries), len(existing),
            )

    current["nielsen"] = nielsen
    current["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    current["scrapeStatus"]["nielsen"] = "ok"

    with open(RATINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)

    logger.info("Nielsen data saved")


def run_nielsen_scrape():
    """Entry point for scheduled Nielsen scrape."""
    try:
        data = scrape_nielsen()
        total = sum(len(v) for v in data.values())
        if total > 0:
            save_nielsen_data(data)
        else:
            logger.warning("Nielsen scrape returned no data, keeping existing")
    except Exception as e:
        logger.error("Nielsen scrape failed: %s", e)
        # Update status but don't touch data
        if RATINGS_FILE.exists():
            with open(RATINGS_FILE) as f:
                current = json.load(f)
            current["scrapeStatus"]["nielsen"] = "error"
            with open(RATINGS_FILE, "w") as f:
                json.dump(current, f, indent=2)
