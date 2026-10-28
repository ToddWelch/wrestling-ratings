"""Tests for the WrestlingAttitude table layout (2026 page, captured 2026-10-28)
and for the combined page parser that handles both layouts."""
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import scraper
from scraper import (
    extract_table_sections,
    parse_page,
    parse_table_number,
    parse_table_date,
    scrape_wrestlingattitude,
    ScrapeError,
    VIEWERSHIP_RANGES,
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
        assert parse_table_date("Sept 28", 2026) == "2026-09-28"

    def test_header_cell_is_not_a_date(self):
        assert parse_table_date("Date", 2026) is None


class TestTableSections:
    def test_finds_all_six_shows(self, soup_tables):
        sections = extract_table_sections(soup_tables)
        assert len(sections) == 6
        assert all(rows for rows in sections.values())

    def test_paragraph_layout_has_no_table_sections(self, soup_2025):
        assert extract_table_sections(soup_2025) == {}


class TestParsePageTables:
    def test_smackdown_first_entry(self, soup_tables):
        nielsen, _, _ = parse_page(soup_tables, 2026)
        assert nielsen["smackdown"][0] == {"date": "2026-01-02", "viewers": 1.175, "demo": 0.28}

    def test_data_runs_into_october(self, soup_tables):
        nielsen, raw, _ = parse_page(soup_tables, 2026)
        for show_id in ("smackdown", "nxt", "dynamite", "collision", "tna"):
            assert nielsen[show_id][-1]["date"] >= "2026-10-01", show_id
        assert raw[-1]["date"] >= "2026-10-01"

    def test_unsuffixed_rows_parse(self, soup_tables):
        nielsen, _, _ = parse_page(soup_tables, 2026)
        dynamite = {e["date"]: e for e in nielsen["dynamite"]}
        assert dynamite["2026-09-30"] == {"date": "2026-09-30", "viewers": 0.899, "demo": 0.22}

    def test_no_data_weeks_are_skipped(self, soup_tables):
        nielsen, raw, _ = parse_page(soup_tables, 2026)
        assert "2026-01-12" not in {e["date"] for e in raw}
        assert "2026-01-17" not in {e["date"] for e in nielsen["collision"]}

    def test_raw_first_entry(self, soup_tables):
        _, raw, _ = parse_page(soup_tables, 2026)
        assert raw[0] == {"date": "2026-01-05", "viewers": 3.2}

    def test_no_contamination_or_duplicates(self, soup_tables):
        nielsen, raw, _ = parse_page(soup_tables, 2026)
        for show_id, entries in nielsen.items():
            vmin, vmax = VIEWERSHIP_RANGES[show_id]
            dates = [e["date"] for e in entries]
            assert len(dates) == len(set(dates)), show_id
            for e in entries:
                assert vmin <= e["viewers"] <= vmax, (show_id, e)
                assert e["date"].startswith("2026")
        for e in raw:
            assert 1.0 <= e["viewers"] <= 8.0, e

    def test_paragraph_layout_still_parses(self, soup_2025):
        nielsen, raw, sections = parse_page(soup_2025, 2025)
        assert sections >= 5
        assert nielsen["smackdown"][0]["date"] == "2025-01-03"
        assert len(nielsen["smackdown"]) >= 50
        assert nielsen["tna"] == []
        assert len(raw) >= 45


class TestScrapeFailsLoudly:
    def test_layout_change_raises(self, monkeypatch):
        empty = BeautifulSoup("<html><body><p>Ratings coming soon</p></body></html>", "html.parser")
        monkeypatch.setattr(scraper, "fetch_page", lambda url: empty)
        with pytest.raises(ScrapeError, match="no recognizable show sections"):
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
        pages = {2025: soup_2025, 2026: soup_tables}
        monkeypatch.setattr(scraper, "fetch_page",
                            lambda url: pages[2025] if "2025" in url else pages[2026])
        nielsen, raw = scrape_wrestlingattitude()
        smackdown_years = {e["date"][:4] for e in nielsen["smackdown"]}
        assert smackdown_years == {"2025", "2026"}
        assert {e["date"][:4] for e in raw} == {"2025", "2026"}
