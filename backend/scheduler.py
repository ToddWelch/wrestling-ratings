import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def start_scheduler():
    from scraper import run_nielsen_scrape
    from youtube_scraper import run_youtube_scrape

    scheduler = BackgroundScheduler()

    # Nielsen scrape every 6 hours
    scheduler.add_job(run_nielsen_scrape, "interval", hours=6, id="nielsen_scrape")

    # YouTube scrape every 12 hours
    scheduler.add_job(run_youtube_scrape, "interval", hours=12, id="youtube_scrape")

    scheduler.start()
    logger.info("Scheduler started: Nielsen every 6h, YouTube every 12h")

    # Run initial scrapes
    logger.info("Running initial scrapes")
    run_nielsen_scrape()
    run_youtube_scrape()
