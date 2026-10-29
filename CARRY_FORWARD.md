# CARRY_FORWARD

Deferred review and gate findings, ranked. Each names where it came from.
Remove an item only when the PR that fixes it merges.

## Next PR (pipeline hardening), ranked

1. **Merge stored data by date instead of the fewer-entries guard.** New
   entries replace stored ones for the same date; stored dates the scrape did
   not return are kept. That holds "never lose data" structurally and closes
   three findings at once:
   - gate I-1: a failure on the static 2025 page raises for the whole primary
     source and discards the good 2026 scrape (dropping 2025 alone would still
     lose to the count guard);
   - gate I-2 and Crash Override note: a partial loss of the newest rows, or a
     source that trims its tables to recent weeks, freezes the chart with no
     alert;
   - then require only the current-year page for success and log or alert on
     earlier-year page problems.
   Add a freshness alert: a weekly show's newest date more than about 3 weeks
   behind today, or behind the backup's newest date.
   Needs a removal rule too (Crash Override): a pure union keeps bad rows
   forever, including misdated or cross-show rows like the 260-row SmackDown
   contamination that forced the 2026-10-28 reseed. For example, drop stored
   dates inside the scraped window that the source no longer lists.
2. **Manual scrape endpoints run outside the scheduler thread** (gate I-3,
   Crash Override item 4). `/api/scrape` and `/api/reset-data` start their own
   threads; `/api/reset-data` deletes the file first. Route both through the
   scheduler (`add_job(..., next_run_time=now)`) and have reset scrape before
   it swaps the file.
3. **Outside dead-man check** (Crash Override): alert when
   `/api/scrape-status` `lastScrape` is older than about 7 hours; it catches
   any way the scheduler stops (for example a build that skips the Dockerfile),
   where the in-app alerting itself would be gone.
4. **Exact column-header match** (Crash Override note): `_column_indexes`
   takes the first header containing the text, so a "Prev Viewership" column
   placed first would be read instead.
5. **Wrestlenomics page-1 failure** (gate M-4): fail when the newest category
   page fails, not only when all three do.
6. **Open tabs never show a failure** (Crash Override note):
   `frontend/src/App.jsx` refreshes the status cards only when `lastUpdated`
   changes, which no longer happens during an outage.
7. **`SCRAPE_KEY` compared with `!=`** (gate M-3): use `hmac.compare_digest`.

## With the on-page SEO fixes (`docs/seo/on-page-fixes-2026-10.md`)

- **ROH still in the UI** (gate M-1, Crash Override note): toggle, line, note,
  schedule row, subtitle, SEO copy.

## Before ROH (or any YouTube channel) is switched back on

- **The YouTube API key can land in logs and on the public status card.** A
  `googleapiclient` `HttpError` carries the request URL, including the `key=`
  query parameter, within its first 200 characters (Crash Override confirmed
  with a fake key). Three places pass that text on:
  1. `youtube_scraper.scrape_youtube` logs it (per-channel `except`);
  2. `youtube_scraper.run_youtube_scrape` logs it;
  3. `scheduler.start_scheduler`'s `youtube_with_status` stores `str(e)` in
     the scrape status file, and `/api/scrape-status` and the site's status
     card show its first 200 characters publicly.
  Latent today: with `CHANNELS` empty the API is never called. Log and store
  the exception type and status only, as `scheduler._send_alert` now does
  (fixed before the 2026-10-28 merge, gate M-2).

## Dated

- **January 2027:** add the 2027 page to `URLS` with only the shows that
  already have 2027 rows in `EXPECTED_SHOWS`, then widen the set as each show
  airs (Raw's numbers lag about 8 days).
