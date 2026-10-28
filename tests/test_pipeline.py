"""Tests for run_full_scrape's reaction to source failures and for the
fewer-entries guard and lastUpdated handling in the save step."""
import json
import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

import data_reconciler
import scheduler
import scrape_status
import scraper
import scraper_wrestlenomics
import youtube_scraper
from errors import ScrapeError

SEED = BACKEND / "data" / "ratings.json"


@pytest.fixture
def data_dir(monkeypatch, tmp_path):
    """Point every module at a temp copy of the deploy seed."""
    ratings = tmp_path / "ratings.json"
    shutil.copy(SEED, ratings)
    for module in (data_reconciler, youtube_scraper):
        monkeypatch.setattr(module, "DATA_DIR", tmp_path)
        monkeypatch.setattr(module, "RATINGS_FILE", ratings)
    monkeypatch.setattr(scrape_status, "STATUS_FILE", tmp_path / "scrape_status.json")
    return ratings


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(scheduler, "_send_alert", lambda failed: sent.append(list(failed)))
    return sent


def seed_sources():
    """The seed's own data in the shape the two scrapers return."""
    seed = json.loads(SEED.read_text())
    primary = (seed["nielsen"], seed["streaming"]["raw"])
    backup = {"nielsen": {k: v[-1:] for k, v in seed["nielsen"].items()},
              "streaming": {"raw": seed["streaming"]["raw"][-1:]}}
    return primary, backup


def fail(*args, **kwargs):
    raise ScrapeError("2026 page has no valid entries for tna")


class TestFailureAlerts:
    def test_primary_failure_alerts_once_per_outage(self, monkeypatch, data_dir, alerts):
        _, backup = seed_sources()
        monkeypatch.setattr(scraper, "scrape_wrestlingattitude", fail)
        monkeypatch.setattr(scraper_wrestlenomics, "scrape_wrestlenomics", lambda: backup)
        before = json.loads(data_dir.read_text())

        scheduler.run_full_scrape()
        scheduler.run_full_scrape()

        assert alerts == [["WrestlingAttitude: 2026 page has no valid entries for tna"]]
        assert scrape_status.get_status()["wrestlingattitude"]["status"] == "failed"
        after = json.loads(data_dir.read_text())
        assert after == before, "backup-only data must not replace the stored lists or lastUpdated"

    def test_alerts_again_after_recovery_then_failure(self, monkeypatch, data_dir, alerts):
        primary, backup = seed_sources()
        monkeypatch.setattr(scraper_wrestlenomics, "scrape_wrestlenomics", lambda: backup)
        monkeypatch.setattr(scraper, "scrape_wrestlingattitude", fail)
        scheduler.run_full_scrape()
        monkeypatch.setattr(scraper, "scrape_wrestlingattitude", lambda: primary)
        scheduler.run_full_scrape()
        monkeypatch.setattr(scraper, "scrape_wrestlingattitude", fail)
        scheduler.run_full_scrape()
        assert len(alerts) == 2

    def test_backup_failure_alerts(self, monkeypatch, data_dir, alerts):
        primary, _ = seed_sources()
        monkeypatch.setattr(scraper, "scrape_wrestlingattitude", lambda: primary)
        monkeypatch.setattr(scraper_wrestlenomics, "scrape_wrestlenomics",
                            lambda: (_ for _ in ()).throw(ScrapeError("URL format changed?")))
        scheduler.run_full_scrape()
        assert alerts == [["Wrestlenomics: URL format changed?"]]

    def test_healthy_run_sends_nothing(self, monkeypatch, data_dir, alerts):
        primary, backup = seed_sources()
        monkeypatch.setattr(scraper, "scrape_wrestlingattitude", lambda: primary)
        monkeypatch.setattr(scraper_wrestlenomics, "scrape_wrestlenomics", lambda: backup)
        scheduler.run_full_scrape()
        assert alerts == []


class TestSaveReconciledData:
    def test_unchanged_data_keeps_last_updated(self, data_dir):
        seed = json.loads(SEED.read_text())
        reconciled = {"nielsen": seed["nielsen"], "streaming": seed["streaming"]}
        assert data_reconciler.save_reconciled_data(reconciled) is False
        assert json.loads(data_dir.read_text())["lastUpdated"] == seed["lastUpdated"]

    def test_new_episode_saves_and_bumps_last_updated(self, data_dir):
        seed = json.loads(SEED.read_text())
        nielsen = {k: list(v) for k, v in seed["nielsen"].items()}
        nielsen["smackdown"].append({"date": "2026-10-23", "viewers": 1.3, "demo": 0.3})
        assert data_reconciler.save_reconciled_data(
            {"nielsen": nielsen, "streaming": seed["streaming"]}) is True
        saved = json.loads(data_dir.read_text())
        assert saved["nielsen"]["smackdown"][-1]["date"] == "2026-10-23"
        assert saved["lastUpdated"] != seed["lastUpdated"]

    def test_fewer_entries_keep_existing(self, data_dir):
        seed = json.loads(SEED.read_text())
        nielsen = {k: list(v) for k, v in seed["nielsen"].items()}
        nielsen["nxt"] = nielsen["nxt"][-3:]
        data_reconciler.save_reconciled_data({"nielsen": nielsen, "streaming": seed["streaming"]})
        assert json.loads(data_dir.read_text())["nielsen"]["nxt"] == seed["nielsen"]["nxt"]


class TestYoutubeSave:
    def test_no_channels_does_not_bump_last_updated(self, data_dir):
        seed = json.loads(SEED.read_text())
        youtube_scraper.save_youtube_data({})
        saved = json.loads(data_dir.read_text())
        assert saved["lastUpdated"] == seed["lastUpdated"]
        assert saved["scrapeStatus"]["youtube"] == "ok"
