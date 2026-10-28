import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from errors import ScrapeError

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.json"

URLS = {
    2025: "https://www.wrestlingattitude.com/p/2025-wwe-aew-viewership-and-key-demo-ratings.html",
    2026: "https://www.wrestlingattitude.com/p/2026-wwe-aew-viewership-and-key-demo-ratings.html",
}

# Shows each year page must yield at least one valid entry for. A show that
# comes back empty fails the scrape, so a layout change cannot freeze one
# show's data quietly behind the fewer-entries guard. Every URLS year needs
# an entry here (TNA joined AMC in 2026, so 2025 has no TNA section).
EXPECTED_SHOWS = {
    2025: {"smackdown", "nxt", "dynamite", "collision", "raw"},
    2026: {"smackdown", "nxt", "dynamite", "collision", "tna", "raw"},
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

# Table layout cells: "Jan 5" and "1.175 M" / "0.899" (period is the decimal here)
HEADING_TAGS = ["h2", "h3", "h4"]
TABLE_DATE_RE = re.compile(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2})$")
TABLE_NUMBER_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*M?$", re.IGNORECASE)

# Table columns are found by header text, never by position, so a reordered
# table (e.g. Hours Viewed before Global Views) cannot swap values.
NIELSEN_COLUMNS = {"date": "date", "viewers": "viewership", "demo": "demo"}
RAW_COLUMNS = {"date": "date", "viewers": "global views"}

# Expected viewership ranges per show (in millions) for sanity checks.
# Raw is Netflix global views, a different metric on a different scale.
VIEWERSHIP_RANGES = {
    "smackdown": (0.5, 2.5),
    "nxt": (0.3, 1.2),
    "dynamite": (0.3, 1.2),
    "collision": (0.1, 0.8),
    "tna": (0.05, 0.4),
    "raw": (1.0, 8.0),
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


def extract_table_sections(soup):
    """Extract per-show table rows from the table layout.

    The 2026 page moved to this layout during 2026:
      <h3>WWE SmackDown (Million Viewers)</h3>
      <figure><table>... Date | Viewership | Key Demo (18-49) | Notes ...</table></figure>

    Returns {header_text: {"columns": [...], "rows": [[cell, ...], ...]}}.
    "columns" holds the lowercased header-row cells; "rows" holds the body
    rows with <td> and <th> cells in order. Only the first table before the
    next heading belongs to a show.
    """
    sections = {}
    for node in soup.find_all(string=lambda t: t and "Million Viewers" in t):
        header = node.find_parent(HEADING_TAGS)
        if not header:
            continue  # paragraph layout; extract_sections_from_dom handles it

        columns, rows = [], []
        for sib in header.find_next_siblings():
            if sib.name in HEADING_TAGS:
                break
            table = sib if sib.name == "table" else sib.find("table")
            if table:
                for tr in table.find_all("tr"):
                    cell_tags = tr.find_all(["td", "th"])
                    cells = [c.get_text(" ", strip=True) for c in cell_tags]
                    if not cells:
                        continue
                    if not columns and all(c.name == "th" for c in cell_tags):
                        columns = [c.lower() for c in cells]
                    else:
                        rows.append(cells)
                break

        sections[header.get_text(" ", strip=True)] = {"columns": columns, "rows": rows}
    return sections


def _column_indexes(columns, wanted):
    """Map each wanted field to the first column whose header contains its text.

    Returns None when any wanted column is missing.
    """
    indexes = {}
    for field, text in wanted.items():
        matches = [i for i, col in enumerate(columns) if text in col]
        if not matches:
            return None
        indexes[field] = matches[0]
    return indexes


def parse_table_date(cell, year):
    """'Jan 5' -> '2026-01-05'. Returns None when the cell is not a date."""
    match = TABLE_DATE_RE.match(cell.strip())
    if not match:
        return None
    month = MONTHS.get(match.group(1)[:3].title())
    if not month:
        return None
    return f"{year}-{month:02d}-{int(match.group(2)):02d}"


def parse_table_number(cell):
    """'1.175 M' or '0.899' -> float. Returns None for 'NO DATA' or blank."""
    match = TABLE_NUMBER_RE.match(cell.strip())
    if not match:
        return None
    return parse_viewer_number(match.group(1))


def _table_entries(table, year, wanted, label):
    """Parse a table's body rows into entries holding the wanted fields.

    Returns [] (with an error logged) when the header row lacks a wanted
    column; the caller's expected-shows check turns that into a failure.
    """
    indexes = _column_indexes(table["columns"], wanted)
    if indexes is None:
        logger.error("%s table (%d) is missing expected columns %s; found %s",
                     label, year, list(wanted.values()), table["columns"])
        return []

    entries = []
    for cells in table["rows"]:
        values = {f: cells[i] if i < len(cells) else "" for f, i in indexes.items()}
        entry = {"date": parse_table_date(values.pop("date"), year)}
        for field, cell in values.items():
            entry[field] = parse_table_number(cell)
        if entry["date"] and all(v is not None for v in entry.values()):
            if "demo" in entry:
                entry["demo"] = round(entry["demo"], 2)
            entries.append(entry)
        elif not _is_no_data_row(values):
            logger.warning("Unparseable %s table row (%d): %s", label, year, cells)
    return entries


def extract_nielsen_rows(table, year):
    """Turn a Nielsen table (Date, Viewership, Key Demo, Notes) into entries."""
    return _table_entries(table, year, NIELSEN_COLUMNS, "Nielsen")


def extract_raw_rows(table, year):
    """Turn a Raw table (Date, Global Views, Hours Viewed, Notes) into entries."""
    return _table_entries(table, year, RAW_COLUMNS, "Raw")


def _is_no_data_row(value_cells):
    """Weeks without published numbers: 'NO DATA', a dash or blank, no digits."""
    return not any(ch.isdigit() for cell in value_cells.values() for ch in cell)


def _show_id_for(header_text):
    for header_prefix, sid in NIELSEN_HEADERS.items():
        if header_prefix.lower() in header_text.lower():
            return sid
    return None


def _raw_paragraph_content(soup, content):
    """The Raw header <p> in the paragraph layout carries data inline; include it."""
    for node in soup.find_all(string=lambda t: t and RAW_HEADER in t):
        p = node
        while p and getattr(p, 'name', None) != 'p':
            p = p.parent
        if p:
            return p.get_text() + " " + content
    return content


def parse_page(soup, year):
    """Parse one WrestlingAttitude year page in either layout.

    Returns (nielsen, raw). Each show's entries, Raw included, are
    range-checked and deduplicated by date.
    """
    nielsen = {show_id: [] for show_id in NIELSEN_HEADERS.values()}
    raw = []

    for header_text, content in extract_sections_from_dom(soup).items():
        if RAW_HEADER.lower() in header_text.lower():
            raw.extend(extract_raw_entries(_raw_paragraph_content(soup, content), year))
        elif (show_id := _show_id_for(header_text)):
            nielsen[show_id].extend(extract_nielsen_entries(content, year))

    for header_text, table in extract_table_sections(soup).items():
        if RAW_HEADER.lower() in header_text.lower():
            raw.extend(extract_raw_rows(table, year))
        elif (show_id := _show_id_for(header_text)):
            nielsen[show_id].extend(extract_nielsen_rows(table, year))

    for show_id in nielsen:
        nielsen[show_id] = validate_entries(nielsen[show_id], show_id)
        logger.info("Parsed %d valid entries for %s (%d)", len(nielsen[show_id]), show_id, year)
    raw = validate_entries(raw, "raw")
    logger.info("Parsed %d Raw entries (%d)", len(raw), year)

    return nielsen, raw


def missing_shows(year, nielsen, raw):
    """Shows EXPECTED_SHOWS requires for this year page that came back empty."""
    found = {show_id for show_id, entries in nielsen.items() if entries}
    if raw:
        found.add("raw")
    return sorted(EXPECTED_SHOWS[year] - found)


def scrape_wrestlingattitude():
    """Scrape Nielsen and Raw (Netflix) data from every WrestlingAttitude year page.

    Each page is fetched once. Raises ScrapeError when any page cannot be
    fetched or any show expected on it yields no valid entries, so a layout
    change shows up as a failed scrape instead of a quiet drop in data.

    Returns (nielsen, raw).
    """
    logger.info("Starting WrestlingAttitude scrape")
    nielsen = {show_id: [] for show_id in NIELSEN_HEADERS.values()}
    raw = []
    problems = []

    for year, url in URLS.items():
        try:
            soup = fetch_page(url)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            problems.append(f"{year} page fetch failed: {e}")
            continue

        page_nielsen, page_raw = parse_page(soup, year)
        missing = missing_shows(year, page_nielsen, page_raw)
        if missing:
            logger.error("No valid entries for %s on %s", missing, url)
            problems.append(f"{year} page has no valid entries for {', '.join(missing)}")
            continue

        for show_id, entries in page_nielsen.items():
            nielsen[show_id].extend(entries)
        raw.extend(page_raw)

    if problems:
        raise ScrapeError("; ".join(problems))
    return nielsen, raw
