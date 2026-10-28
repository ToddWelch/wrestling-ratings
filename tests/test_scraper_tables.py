"""Tests for the WrestlingAttitude table layout (2026 page, captured 2026-10-28)
and for the combined page parser that handles both layouts."""
import logging
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import scraper
from errors import ScrapeError
from scraper import (
    EXPECTED_SHOWS,
    URLS,
    VIEWERSHIP_RANGES,
    extract_nielsen_rows,
    extract_raw_rows,
    extract_table_sections,
    parse_page,
    parse_table_date,
    parse_table_number,
    scrape_wrestlingattitude,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def soup_tables():
    with open(FIXTURES_DIR / "wrestlingattitude_2026_tables.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def soup_2025():
    with open(FIXTURES_DIR / "wrestlingattitude_2025.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


def table_page(sections):
    """Build a minimal table-layout page: {heading: (header_cells, rows)}."""
    html = ""
    for heading, (header, rows) in sections.items():
        head = "".join(f"<th>{h}</th>" for h in header)
        body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
        html += (f"<h3>{heading} (Million Viewers)</h3>"
                 f"<figure><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></figure>")
    return BeautifulSoup(f"<html><body><article>{html}</article></body></html>", "html.parser")


NIELSEN_HEADER = ["Date", "Viewership", "Key Demo (18-49)", "Notes"]
RAW_HEADER_CELLS = ["Date", "Global Views", "Hours Viewed", "Notes"]


class TestTableCells:
    def test_number_with_suffix(self):
        assert parse_table_number("1.175 M") == 1.175

    def test_number_without_suffix(self):
        assert parse_table_number("0.899") == 0.899

    def test_raw_global_views(self):
        assert parse_table_number("3.2 M") == 3.2

    def test_no_data(self):
        assert parse_table_number("NO DATA") is None

    def test_dash(self):
        assert parse_table_number(chr(0x2013)) is None  # the source's en dash placeholder

    def test_date(self):
        assert parse_table_date("Jan 5", 2026) == "2026-01-05"

    def test_long_month_name(self):
        assert parse_table_date("July 2", 2026) == "2026-07-02"

    def test_header_cell_is_not_a_date(self):
        assert parse_table_date("Date", 2026) is None


class TestTableSections:
    def test_finds_all_six_shows_with_columns(self, soup_tables):
        sections = extract_table_sections(soup_tables)
        assert len(sections) == 6
        for table in sections.values():
            assert table["rows"]
            assert table["columns"][0] == "date"

    def test_paragraph_layout_has_no_table_sections(self, soup_2025):
        assert extract_table_sections(soup_2025) == {}

    def test_columns_found_by_header_not_position(self):
        soup = table_page({"WWE RAW on Netflix": (
            ["Date", "Hours Viewed", "Global Views", "Notes"],
            [["Jan 5", "5.9 M", "3.2 M", "-"]],
        )})
        table = next(iter(extract_table_sections(soup).values()))
        assert extract_raw_rows(table, 2026) == [{"date": "2026-01-05", "viewers": 3.2}]

    def test_row_header_date_cell_is_kept(self):
        soup = BeautifulSoup(
            "<h3>WWE NXT (Million Viewers)</h3><figure><table>"
            "<thead><tr><th>Date</th><th>Viewership</th><th>Key Demo</th><th>Notes</th></tr></thead>"
            "<tbody><tr><th scope='row'>Oct 6</th><td>0.532 M</td><td>0.10</td><td>-</td></tr></tbody>"
            "</table></figure>", "html.parser")
        table = next(iter(extract_table_sections(soup).values()))
        assert extract_nielsen_rows(table, 2026) == [{"date": "2026-10-06", "viewers": 0.532, "demo": 0.1}]

    def test_missing_column_yields_nothing_and_logs_error(self, caplog):
        soup = table_page({"WWE NXT": (["Date", "Audience", "Notes"], [["Oct 6", "0.532 M", "-"]])})
        table = next(iter(extract_table_sections(soup).values()))
        with caplog.at_level(logging.ERROR):
            assert extract_nielsen_rows(table, 2026) == []
        assert "missing expected columns" in caplog.text


class TestParsePageTables:
    def test_smackdown_first_entry(self, soup_tables):
        nielsen, _ = parse_page(soup_tables, 2026)
        assert nielsen["smackdown"][0] == {"date": "2026-01-02", "viewers": 1.175, "demo": 0.28}

    def test_data_runs_into_october(self, soup_tables):
        nielsen, raw = parse_page(soup_tables, 2026)
        for show_id in ("smackdown", "nxt", "dynamite", "collision", "tna"):
            assert nielsen[show_id][-1]["date"] >= "2026-10-01", show_id
        assert raw[-1]["date"] >= "2026-10-01"

    def test_unsuffixed_rows_parse(self, soup_tables):
        nielsen, _ = parse_page(soup_tables, 2026)
        dynamite = {e["date"]: e for e in nielsen["dynamite"]}
        assert dynamite["2026-09-30"] == {"date": "2026-09-30", "viewers": 0.899, "demo": 0.22}

    def test_no_data_weeks_skipped_without_warnings(self, soup_tables, caplog):
        with caplog.at_level(logging.WARNING):
            nielsen, raw = parse_page(soup_tables, 2026)
        assert "Unparseable" not in caplog.text
        # NO DATA rows (Raw Jan 12, Collision Jan 17, TNA July 2) and a dash-only row (TNA Aug 27)
        assert "2026-01-12" not in {e["date"] for e in raw}
        assert "2026-01-17" not in {e["date"] for e in nielsen["collision"]}
        tna_dates = {e["date"] for e in nielsen["tna"]}
        assert "2026-07-02" not in tna_dates and "2026-08-27" not in tna_dates

    def test_malformed_row_warns(self, caplog):
        soup = table_page({"WWE NXT": (NIELSEN_HEADER, [["Oct 6", "0.53x M", "0.10", "-"]])})
        with caplog.at_level(logging.WARNING):
            nielsen, _ = parse_page(soup, 2026)
        assert nielsen["nxt"] == []
        assert "Unparseable Nielsen table row" in caplog.text

    def test_raw_first_entry(self, soup_tables):
        _, raw = parse_page(soup_tables, 2026)
        assert raw[0] == {"date": "2026-01-05", "viewers": 3.2}

    def test_raw_out_of_range_rejected(self):
        soup = table_page({"WWE RAW on Netflix": (RAW_HEADER_CELLS, [
            ["Jan 5", "3.2 M", "5.9 M", "-"],
            ["Jan 12", "12.5 M", "20.0 M", "-"],
        ])})
        _, raw = parse_page(soup, 2026)
        assert raw == [{"date": "2026-01-05", "viewers": 3.2}]

    def test_no_contamination_or_duplicates(self, soup_tables):
        nielsen, raw = parse_page(soup_tables, 2026)
        for show_id, entries in list(nielsen.items()) + [("raw", raw)]:
            vmin, vmax = VIEWERSHIP_RANGES[show_id]
            dates = [e["date"] for e in entries]
            assert len(dates) == len(set(dates)), show_id
            for e in entries:
                assert vmin <= e["viewers"] <= vmax, (show_id, e)
                assert e["date"].startswith("2026")

    def test_paragraph_layout_still_parses(self, soup_2025):
        nielsen, raw = parse_page(soup_2025, 2025)
        assert nielsen["smackdown"][0]["date"] == "2025-01-03"
        assert len(nielsen["smackdown"]) >= 50
        assert nielsen["tna"] == []
        assert len(raw) >= 45


class TestScrapeFailsLoudly:
    def test_every_url_year_has_expected_shows(self):
        assert set(EXPECTED_SHOWS) == set(URLS)

    def test_layout_change_raises(self, monkeypatch):
        empty = BeautifulSoup("<html><body><p>Ratings coming soon</p></body></html>", "html.parser")
        monkeypatch.setattr(scraper, "fetch_page", lambda url: empty)
        with pytest.raises(ScrapeError, match="no valid entries"):
            scrape_wrestlingattitude()

    def test_intro_sentence_only_raises(self, monkeypatch):
        page = BeautifulSoup("<p>All figures are in Million Viewers.</p>", "html.parser")
        monkeypatch.setattr(scraper, "fetch_page", lambda url: page)
        with pytest.raises(ScrapeError, match="no valid entries"):
            scrape_wrestlingattitude()

    def test_headings_kept_but_tables_emptied_raises(self, monkeypatch, soup_2025):
        headings_only = table_page({h: (NIELSEN_HEADER, []) for h in (
            "WWE RAW on Netflix", "WWE SmackDown", "WWE NXT", "AEW Dynamite",
            "AEW Collision", "TNA iMPACT")})
        monkeypatch.setattr(scraper, "fetch_page",
                            lambda url: soup_2025 if "2025" in url else headings_only)
        with pytest.raises(ScrapeError, match="2026 page has no valid entries for"):
            scrape_wrestlingattitude()

    def test_one_show_missing_raises(self, monkeypatch, soup_2025, soup_tables):
        soup_tables.find(string=lambda t: t and "TNA iMPACT (Million Viewers)" in t) \
            .find_parent("h3").find_next_sibling("figure").decompose()
        monkeypatch.setattr(scraper, "fetch_page",
                            lambda url: soup_2025 if "2025" in url else soup_tables)
        with pytest.raises(ScrapeError, match="no valid entries for tna"):
            scrape_wrestlingattitude()

    def test_fetch_failure_raises(self, monkeypatch, soup_2025):
        def fetch(url):
            if "2026" in url:
                raise ConnectionError("timed out")
            return soup_2025
        monkeypatch.setattr(scraper, "fetch_page", fetch)
        with pytest.raises(ScrapeError, match="2026 page fetch failed"):
            scrape_wrestlingattitude()

    def test_both_layouts_combine(self, monkeypatch, soup_2025, soup_tables):
        monkeypatch.setattr(scraper, "fetch_page",
                            lambda url: soup_2025 if "2025" in url else soup_tables)
        nielsen, raw = scrape_wrestlingattitude()
        assert {e["date"][:4] for e in nielsen["smackdown"]} == {"2025", "2026"}
        assert {e["date"][:4] for e in raw} == {"2025", "2026"}
