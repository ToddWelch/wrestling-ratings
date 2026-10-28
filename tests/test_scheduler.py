"""Tests that the scrape scheduler starts under gunicorn and runs its jobs.

Production runs gunicorn, which never executes app.py's __main__ block; the
scheduler went unstarted from launch until 2026-10-28 because of that.
"""
import importlib.util
import sys
import threading
import time
from pathlib import Path

import pytest

BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

import scheduler as scheduler_module
import scrape_status
import youtube_scraper


@pytest.fixture(autouse=True)
def isolated_scheduler(monkeypatch, tmp_path):
    monkeypatch.setattr(scrape_status, "STATUS_FILE", tmp_path / "scrape_status.json")
    yield
    if scheduler_module._scheduler is not None:
        # wait=True lets queued jobs finish while STATUS_FILE is still patched
        scheduler_module._scheduler.shutdown(wait=True)
        scheduler_module._scheduler = None


def load_gunicorn_conf():
    spec = importlib.util.spec_from_file_location("gunicorn_conf", BACKEND / "gunicorn.conf.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestGunicornConfig:
    def test_single_worker(self):
        assert load_gunicorn_conf().workers == 1

    def test_worker_init_starts_scheduler(self, monkeypatch):
        calls = []
        monkeypatch.setattr(scheduler_module, "start_scheduler", lambda: calls.append(1))
        load_gunicorn_conf().post_worker_init(worker=None)
        assert calls == [1]

    def test_dockerfile_uses_config(self):
        dockerfile = (BACKEND.parent / "Dockerfile").read_text()
        assert '"--config", "backend/gunicorn.conf.py"' in dockerfile


class TestStartScheduler:
    def test_first_runs_fire_at_start_and_in_sequence(self, monkeypatch):
        full_done = threading.Event()
        youtube_done = threading.Event()
        order = []

        def slow_full_scrape():
            time.sleep(2)  # longer than APScheduler's default 1s misfire grace
            order.append("full")
            full_done.set()

        def youtube():
            order.append("youtube")
            youtube_done.set()

        monkeypatch.setattr(scheduler_module, "run_full_scrape", slow_full_scrape)
        monkeypatch.setattr(youtube_scraper, "run_youtube_scrape", youtube)

        started = time.monotonic()
        scheduler_module.start_scheduler()
        assert time.monotonic() - started < 1, "start_scheduler must not block on scraping"

        assert full_done.wait(10), "full scrape did not run at startup"
        assert youtube_done.wait(10), "YouTube scrape was skipped after waiting its turn"
        assert order == ["full", "youtube"]
        deadline = time.monotonic() + 5  # status is written just after the job returns
        while "youtube" not in scrape_status.get_status() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert scrape_status.get_status()["youtube"]["status"] == "success"

    def test_jobs_and_intervals(self, monkeypatch):
        monkeypatch.setattr(scheduler_module, "run_full_scrape", lambda: None)
        monkeypatch.setattr(youtube_scraper, "run_youtube_scrape", lambda: None)
        sched = scheduler_module.start_scheduler()
        jobs = {job.id: job for job in sched.get_jobs()}
        assert set(jobs) == {"full_scrape", "youtube_scrape"}
        assert jobs["full_scrape"].trigger.interval.total_seconds() == 6 * 3600
        assert jobs["youtube_scrape"].trigger.interval.total_seconds() == 12 * 3600

    def test_second_start_is_a_no_op(self, monkeypatch):
        monkeypatch.setattr(scheduler_module, "run_full_scrape", lambda: None)
        monkeypatch.setattr(youtube_scraper, "run_youtube_scrape", lambda: None)
        first = scheduler_module.start_scheduler()
        second = scheduler_module.start_scheduler()
        assert first is second
