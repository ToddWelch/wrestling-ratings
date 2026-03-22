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
RAW_RE = re.compile(
    r"(\w{3})\s+(\d{1,2}):\s*([\d,\.]+)\s*Global",
    re.IGNORECASE,
)

# Expected viewership ranges per show (in millions) for sanity checks
VIEWERSHIP_RANGES = {
    "smackdown": (0.5, 2.5),
    "nxt": (0.3, 1.2),
    "dynamite": (0.3, 1.2),
    "collision": (0.1, 0.8),
    "tna": (0.05, 0.4),
}


def fetch_page(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "WrestlingRatingsTracker/1.0"})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_viewer_number(raw):
    """Parse viewer string where comma = decimal. '1,175' -> 1.175, '0,990' -> 0.990"""
    cleaned = raw.replace(",", ".").rstrip(".")
    return round(float(cleaned), 3)


def extract_sections_from_dom(soup):
    """Walk the HTML DOM to extract per-show data sections.

    The page structure is:
      <p><strong><u>SHOW NAME (Million Viewers):</u></strong></p>
      <p>Jan 2: 1,175 ... key demo rating Jan 9: ...</p>
      <p><strong><u>NEXT SHOW (Million Viewers):</u></strong></p>
      ...

    We find each header element, then collect the text from the <p>
    siblings that follow it, stopping when we hit the next header
    or any non-<p> element (like <h2>, <ul>, <div>).
    """
    sections = {}

    # Find all text nodes containing "Million Viewers"
    header_nodes = soup.find_all(string=lambda t: t and "Million Viewers" in t)

    for header_text_node in header_nodes:
        # The header text is inside <u><strong><p>
        header_p = header_text_node
        while header_p and getattr(header_p, 'name', None) != 'p':
            header_p = header_p.parent

        if not header_p:
            continue

        header_text = header_text_node.strip()

        # Collect text from <p> siblings after the header <p>
        # Stop at the next show header or non-<p> element
        data_text_parts = []
        for sib in header_p.next_siblings:
            if not hasattr(sib, 'name') or not sib.name:
                continue  # skip NavigableString (whitespace)

            if sib.name != 'p':
                break  # hit <h2>, <ul>, <div>, etc. = footer content

            sib_text = sib.get_text()

            # If this <p> contains a show header, stop
            if "Million Viewers" in sib_text:
                break

            data_text_parts.append(sib_text)

        sections[header_text] = " ".join(data_text_parts)

    return sections


def extract_nielsen_entries(text, year):
    """Extract Nielsen entries (viewers + demo) from section text."""
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


def extract_raw_entries(text, year):
    """Extract Raw Netflix entries (viewers only) from section text."""
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


def validate_entries(entries, show_id):
    """Remove entries outside the expected viewership range for a show.
    Also removes duplicate dates, keeping the first occurrence."""
    vmin, vmax = VIEWERSHIP_RANGES.get(show_id, (0, 100))
    seen_dates = set()
    valid = []

    for entry in entries:
        date = entry["date"]
        viewers = entry["viewers"]

        if date in seen_dates:
            logger.warning("Duplicate date %s for %s, skipping", date, show_id)
            continue
        seen_dates.add(date)

        if viewers < vmin or viewers > vmax:
            logger.warning(
                "Viewership %.3f for %s on %s outside range (%.2f-%.2f), rejecting",
                viewers, show_id, date, vmin, vmax,
            )
            continue

        valid.append(entry)

    return valid


def scrape_nielsen():
    """Scrape all Nielsen data from WrestlingAttitude using DOM parsing."""
    logger.info("Starting Nielsen scrape")
    all_data = {show_id: [] for show_id in NIELSEN_HEADERS.values()}

    for year, url in URLS.items():
        try:
            soup = fetch_page(url)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            continue

        sections = extract_sections_from_dom(soup)
        logger.info("Found %d sections on %d page", len(sections), year)

        for header_text, content in sections.items():
            # Match header to show ID
            show_id = None
            for header_prefix, sid in NIELSEN_HEADERS.items():
                if header_prefix.lower() in header_text.lower():
                    show_id = sid
                    break

            if show_id:
                entries = extract_nielsen_entries(content, year)
                entries = validate_entries(entries, show_id)
                all_data[show_id].extend(entries)
                logger.info("Parsed %d valid entries for %s (%d)", len(entries), show_id, year)

    return all_data


def scrape_raw():
    """Scrape WWE Raw Netflix data from WrestlingAttitude using DOM parsing."""
    logger.info("Starting Raw (Netflix) scrape")
    raw_data = []

    for year, url in URLS.items():
        try:
            soup = fetch_page(url)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            continue

        sections = extract_sections_from_dom(soup)

        for header_text, content in sections.items():
            if RAW_HEADER.lower() in header_text.lower():
                # Raw header <p> also contains inline text; include it
                header_nodes = soup.find_all(string=lambda t: t and RAW_HEADER in t)
                for node in header_nodes:
                    p = node
                    while p and getattr(p, 'name', None) != 'p':
                        p = p.parent
                    if p:
                        content = p.get_text() + " " + content
                        break

                entries = extract_raw_entries(content, year)
                # Remove duplicates by date
                seen = set()
                unique = []
                for e in entries:
                    if e["date"] not in seen:
                        seen.add(e["date"])
                        unique.append(e)
                raw_data.extend(unique)
                logger.info("Parsed %d Raw entries (%d)", len(unique), year)

    return raw_data
