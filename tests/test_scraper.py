"""Tests for WrestlingAttitude scraper using saved HTML snapshots."""
import sys
import os
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from scraper import (
    extract_sections_from_dom,
    extract_nielsen_entries,
    extract_raw_entries,
    validate_entries,
    parse_viewer_number,
    NIELSEN_HEADERS,
    VIEWERSHIP_RANGES,
    RAW_HEADER,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def soup_2025():
    with open(FIXTURES_DIR / "wrestlingattitude_2025.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def soup_2026():
    with open(FIXTURES_DIR / "wrestlingattitude_2026.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


class TestParseViewerNumber:
    def test_european_comma(self):
        assert parse_viewer_number("1,175") == 1.175

    def test_zero_prefix(self):
        assert parse_viewer_number("0,990") == 0.99

    def test_trailing_period(self):
        assert parse_viewer_number("2,5.") == 2.5

    def test_plain_decimal(self):
        assert parse_viewer_number("3.2") == 3.2


class TestExtractSectionsFromDom:
    def test_2026_finds_all_sections(self, soup_2026):
        sections = extract_sections_from_dom(soup_2026)
        # Should find Raw, SmackDown, NXT, Dynamite, Collision, TNA
        assert len(sections) >= 6

    def test_2025_finds_sections(self, soup_2025):
        sections = extract_sections_from_dom(soup_2025)
        # 2025 has Raw, SmackDown, NXT, Dynamite, Collision (no TNA)
        assert len(sections) >= 5

    def test_sections_do_not_contain_footer(self, soup_2026):
        sections = extract_sections_from_dom(soup_2026)
        for header, content in sections.items():
            # Footer contains "Highest Viewership" text
            assert "Highest Viewership" not in content, (
                f"Section '{header}' contains footer content"
            )

    def test_tna_section_is_clean(self, soup_2026):
        """TNA is the last section; it must not contain other shows' data."""
        sections = extract_sections_from_dom(soup_2026)
        tna_content = None
        for header, content in sections.items():
            if "TNA" in header:
                tna_content = content
                break
        assert tna_content is not None, "TNA section not found"
        # TNA section should not contain SmackDown-level numbers
        assert "1,459" not in tna_content
        assert "1,419" not in tna_content


class TestExtractNielsenEntries:
    def test_smackdown_2026(self, soup_2026):
        sections = extract_sections_from_dom(soup_2026)
        for header, content in sections.items():
            if "SmackDown" in header:
                entries = extract_nielsen_entries(content, 2026)
                assert len(entries) > 5
                # First entry should be Jan 2
                assert entries[0]["date"] == "2026-01-02"
                assert entries[0]["viewers"] == 1.175
                assert entries[0]["demo"] == 0.28
                break

    def test_tna_2026_entries_count(self, soup_2026):
        sections = extract_sections_from_dom(soup_2026)
        for header, content in sections.items():
            if "TNA" in header:
                entries = extract_nielsen_entries(content, 2026)
                # TNA started Jan 2026 on AMC; should have ~9-12 entries
                assert 8 <= len(entries) <= 15
                break

    def test_no_entries_have_wrong_year(self, soup_2026):
        sections = extract_sections_from_dom(soup_2026)
        for header, content in sections.items():
            for prefix, show_id in NIELSEN_HEADERS.items():
                if prefix in header:
                    entries = extract_nielsen_entries(content, 2026)
                    for e in entries:
                        assert e["date"].startswith("2026"), (
                            f"{show_id} has entry with wrong year: {e}"
                        )


class TestValidateEntries:
    def test_rejects_out_of_range(self):
        entries = [
            {"date": "2026-01-01", "viewers": 1.5, "demo": 0.35},  # SmackDown-level
            {"date": "2026-01-08", "viewers": 0.2, "demo": 0.04},  # TNA-level
        ]
        valid = validate_entries(entries, "tna")
        assert len(valid) == 1
        assert valid[0]["viewers"] == 0.2

    def test_rejects_duplicates(self):
        entries = [
            {"date": "2026-01-01", "viewers": 0.2, "demo": 0.04},
            {"date": "2026-01-01", "viewers": 0.21, "demo": 0.04},
        ]
        valid = validate_entries(entries, "tna")
        assert len(valid) == 1

    def test_passes_valid_entries(self):
        entries = [
            {"date": "2026-01-01", "viewers": 1.2, "demo": 0.30},
            {"date": "2026-01-08", "viewers": 1.4, "demo": 0.35},
        ]
        valid = validate_entries(entries, "smackdown")
        assert len(valid) == 2


class TestNoCrossShowContamination:
    """The critical test: verify no show contains another show's data."""

    def _get_all_entries(self, soup, year):
        sections = extract_sections_from_dom(soup)
        result = {}
        for header, content in sections.items():
            for prefix, show_id in NIELSEN_HEADERS.items():
                if prefix in header:
                    entries = extract_nielsen_entries(content, year)
                    entries = validate_entries(entries, show_id)
                    result[show_id] = entries
        return result

    def test_2026_no_contamination(self, soup_2026):
        data = self._get_all_entries(soup_2026, 2026)
        for show_id, entries in data.items():
            vmin, vmax = VIEWERSHIP_RANGES[show_id]
            for e in entries:
                assert vmin <= e["viewers"] <= vmax, (
                    f"{show_id} has out-of-range entry: {e}"
                )

    def test_2025_no_contamination(self, soup_2025):
        data = self._get_all_entries(soup_2025, 2025)
        for show_id, entries in data.items():
            vmin, vmax = VIEWERSHIP_RANGES[show_id]
            for e in entries:
                assert vmin <= e["viewers"] <= vmax, (
                    f"{show_id} has out-of-range entry: {e}"
                )

    def test_no_duplicate_dates_within_show(self, soup_2026):
        data = self._get_all_entries(soup_2026, 2026)
        for show_id, entries in data.items():
            dates = [e["date"] for e in entries]
            assert len(dates) == len(set(dates)), (
                f"{show_id} has duplicate dates: {[d for d in dates if dates.count(d) > 1]}"
            )

    def test_no_duplicate_dates_2025(self, soup_2025):
        data = self._get_all_entries(soup_2025, 2025)
        for show_id, entries in data.items():
            dates = [e["date"] for e in entries]
            assert len(dates) == len(set(dates)), (
                f"{show_id} has duplicate dates: {[d for d in dates if dates.count(d) > 1]}"
            )


class TestRawScraper:
    def test_raw_entries_2026(self, soup_2026):
        sections = extract_sections_from_dom(soup_2026)
        for header, content in sections.items():
            if RAW_HEADER in header:
                # Include the header <p> text (contains the data intro)
                header_nodes = soup_2026.find_all(string=lambda t: t and RAW_HEADER in t)
                for node in header_nodes:
                    p = node
                    while p and getattr(p, 'name', None) != 'p':
                        p = p.parent
                    if p:
                        content = p.get_text() + " " + content
                        break
                entries = extract_raw_entries(content, 2026)
                assert len(entries) >= 5
                # All values should be reasonable Netflix global views (1-8M)
                for e in entries:
                    assert 1.0 <= e["viewers"] <= 8.0, (
                        f"Raw entry out of range: {e}"
                    )
                break
