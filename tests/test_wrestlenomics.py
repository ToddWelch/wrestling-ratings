"""Tests for the Wrestlenomics backup scraper. The category page fixture was
captured 2026-10-28, after article URLs moved from /tv-ratings/ to /articles/."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import scraper_wrestlenomics as wn
from errors import ScrapeError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class TestUrlParsing:
    def test_articles_path(self):
        url = ("https://wrestlenomics.com/articles/2026/wwe-smackdown-oct-16-on-usa-network-"
               "1327000-viewers-0-32-p18-49-rating-tv-ratings-analysis/")
        assert wn.parse_nielsen_from_url(url) == {
            "type": "nielsen",
            "show_id": "smackdown",
            "entry": {"date": "2026-10-16", "viewers": 1.327, "demo": 0.32},
        }

    def test_old_tv_ratings_path(self):
        url = ("https://wrestlenomics.com/tv-ratings/2026/wwe-smackdown-mar-13-on-usa-network-"
               "1419000-viewers-0-32-p18-49-rating-tv-ratings-analysis/")
        assert wn.parse_nielsen_from_url(url)["entry"] == {
            "date": "2026-03-13", "viewers": 1.419, "demo": 0.32,
        }

    def test_raw_streaming(self):
        url = ("https://wrestlenomics.com/articles/2026/wwe-raw-oct-19-on-netflix-"
               "2500000-global-views-tv-ratings-analysis/")
        assert wn.parse_streaming_from_url(url)["entry"] == {"date": "2026-10-19", "viewers": 2.5}

    def test_december_show_written_up_in_january(self):
        # Article year is the publication year; the show aired the year before
        url = ("https://wrestlenomics.com/articles/2027/wwe-raw-dec-28-on-netflix-"
               "2600000-global-views-tv-ratings-analysis/")
        entry = wn.parse_streaming_from_url(url, today=date(2027, 1, 6))["entry"]
        assert entry["date"] == "2026-12-28"

    def test_tna_new_years_eve(self):
        url = ("https://wrestlenomics.com/articles/2027/tna-impact-dec-31-on-amc-"
               "210000-viewers-0-04-p18-49-rating-tv-ratings-analysis/")
        assert wn.parse_nielsen_from_url(url, today=date(2027, 1, 7))["entry"]["date"] == "2026-12-31"

    def test_same_year_date_unchanged(self):
        assert wn.air_date(2026, 10, 21, today=date(2026, 10, 28)) == "2026-10-21"

    def test_tonight_across_utc_midnight_unchanged(self):
        # A show dated one day past today's UTC date is treated as this year
        assert wn.air_date(2026, 10, 29, today=date(2026, 10, 28)) == "2026-10-29"

    def test_impossible_date(self):
        assert wn.air_date(2027, 2, 29, today=date(2027, 3, 5)) is None

    def test_non_ratings_article(self):
        url = ("https://wrestlenomics.com/articles/2025/nielsen-has-changed-how-tv-ratings-"
               "are-measured-heres-what-it-means-for-wrestling-programs/")
        assert wn.parse_nielsen_from_url(url) is None
        assert wn.parse_streaming_from_url(url) is None


class TestScrape:
    def test_category_page_yields_entries(self, monkeypatch):
        html = (FIXTURES_DIR / "wrestlenomics_category_2026-10.html").read_text()
        monkeypatch.setattr(wn.requests, "get", lambda url, **kw: FakeResponse(html))
        data = wn.scrape_wrestlenomics()
        assert {"date": "2026-10-21", "viewers": 0.661, "demo": 0.15} in data["nielsen"]["dynamite"]
        assert {"date": "2026-10-19", "viewers": 2.5} in data["streaming"]["raw"]
        assert data["nielsen"]["tna"], "TNA (AMC) article not parsed"

    def test_no_parseable_links_raises(self, monkeypatch):
        html = '<a href="https://wrestlenomics.com/articles/2026/some-ratings-roundup/">x</a>'
        monkeypatch.setattr(wn.requests, "get", lambda url, **kw: FakeResponse(html))
        with pytest.raises(ScrapeError, match="none parsed"):
            wn.scrape_wrestlenomics()

    def test_all_category_pages_down_raises(self, monkeypatch):
        def fail(url, **kw):
            raise ConnectionError("refused")
        monkeypatch.setattr(wn.requests, "get", fail)
        with pytest.raises(ScrapeError, match="every Wrestlenomics category page"):
            wn.scrape_wrestlenomics()
