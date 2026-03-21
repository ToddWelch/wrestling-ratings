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

# Map page header text to our show IDs
NIELSEN_HEADERS = {
    "WWE SmackDown": "smackdown",
    "WWE NXT": "nxt",
    "AEW Dynamite": "dynamite",
    "AEW Collision": "collision",
    "TNA iMPACT": "tna",
}

RAW_HEADER = "WWE RAW on Netflix"

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

# Raw Netflix pattern: "Jan 5: 3,2 Global (5,9 million hours viewed)"
# The number before "Global" is views in millions with comma as decimal
RAW_RE = re.compile(
    r"(\w{3})\s+(\d{1,2}):\s*([\d,\.]+)\s*Global",
    re.IGNORECASE,
)

# Regex to split page text by show headers
HEADER_RE = re.compile(
    r"((?:WWE (?:RAW on Netflix|SmackDown|NXT)|AEW (?:Dynamite|Collision)|TNA iMPACT)\s*\(Million Viewers\)\s*:?)",
    re.IGNORECASE,
)


def fetch_page(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "WrestlingRatingsTracker/1.0"})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_viewer_number(raw):
    """Parse viewer string where comma = decimal. '1,175' -> 1.175, '0,990' -> 0.990"""
    cleaned = raw.replace(",", ".").rstrip(".")
    return round(float(cleaned), 3)


def extract_nielsen_data(text, year):
    """Extract Nielsen entries (viewers + demo) from a section of text."""
    # Clean up "(on SyFy)" annotations
    text = re.sub(r"\(on SyFy\)", "", text)

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
    return entries


def extract_raw_data(text, year):
    """Extract Raw Netflix data (viewers only, no demo) from a section of text."""
    entries = []
    for match in RAW_RE.finditer(text):
        month_str, day_str, viewers_raw = match.groups()
        month = MONTHS.get(month_str)
        if not month:
            continue
        day = int(day_str)
        try:
            viewers = parse_viewer_number(viewers_raw)
            date = f"{year}-{month:02d}-{day:02d}"
            entries.append({"date": date, "viewers": viewers})
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse Raw entry: %s - %s", match.group(), e)
    return entries


def split_into_sections(page_text):
    """Split page text into {header: content} sections using show headers."""
    parts = HEADER_RE.split(page_text)
    sections = {}
    # parts alternates: [preamble, header1, content1, header2, content2, ...]
    for i in range(1, len(parts) - 1, 2):
        header = parts[i].strip()
        content = parts[i + 1] if i + 1 < len(parts) else ""
        sections[header] = content
    return sections


def scrape_nielsen():
    """Scrape all Nielsen data from WrestlingAttitude."""
    logger.info("Starting Nielsen scrape")
    all_data = {show_id: [] for show_id in NIELSEN_HEADERS.values()}

    for year, url in URLS.items():
        try:
            soup = fetch_page(url)
            page_text = soup.get_text()
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            continue

        sections = split_into_sections(page_text)
        logger.info("Found %d sections on %d page", len(sections), year)

        for header, content in sections.items():
            # Match header to show ID
            show_id = None
            for header_prefix, sid in NIELSEN_HEADERS.items():
                if header_prefix.lower() in header.lower():
                    show_id = sid
                    break

            if show_id:
                entries = extract_nielsen_data(content, year)
                all_data[show_id].extend(entries)
                logger.info("Parsed %d entries for %s (%d)", len(entries), show_id, year)

    return all_data


def scrape_raw():
    """Scrape WWE Raw Netflix data from WrestlingAttitude."""
    logger.info("Starting Raw (Netflix) scrape")
    raw_data = []

    for year, url in URLS.items():
        try:
            soup = fetch_page(url)
            page_text = soup.get_text()
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            continue

        sections = split_into_sections(page_text)

        for header, content in sections.items():
            if RAW_HEADER.lower() in header.lower():
                entries = extract_raw_data(content, year)
                raw_data.extend(entries)
                logger.info("Parsed %d Raw entries (%d)", len(entries), year)

    return raw_data
