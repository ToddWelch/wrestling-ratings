# Session: Scraper Data Integrity Fix

**Date:** 2026-03-22
**Branch:** `fix/scraper-data-integrity` (merged to main)
**Reviewed by:** Crash Override (approved with notes)

## What Was Done

### Problem
The WrestlingAttitude scraper used `soup.get_text()` to flatten the entire HTML page into plain text, then tried to regex-split it into per-show sections. The last show section on each page absorbed all footer content, which contained "Highest Viewership" and "Related Posts" sections listing other shows' ratings. This caused massive cross-show data contamination (e.g., TNA showing SmackDown's 1.459M viewership).

### Fix
1. **Rewrote scraper.py** with DOM-based section parsing. `extract_sections_from_dom()` walks the HTML `<p>` elements between show headers, stopping at non-`<p>` elements (footer `<h2>`, `<ul>`, etc.). This naturally excludes footer content.

2. **Added viewership range validation** (`validate_entries()`). Each show has an expected viewership range (e.g., TNA 0.05-0.4M, SmackDown 0.5-2.5M). Entries outside the range are logged and rejected. This is defense in depth; even if the DOM structure changes, contaminated data is caught.

3. **Added duplicate date rejection** within each show.

4. **Added Raw Netflix scraping** (`scrape_raw()`) from the same WrestlingAttitude pages, parsing the "X,X Global" format.

5. **Removed dead WrestlingInc scraper**. It was scraping Google search results, which Google blocks. Returned 0 entries. Also a ToS concern.

6. **Added atomic file writes** via `file_utils.py`. All JSON writes now go to a temp file then `os.rename()` to prevent corruption from concurrent writes.

7. **Gated debug=True** behind `FLASK_DEBUG` env var.

8. **Added 19 unit tests** against saved HTML snapshots covering section isolation, contamination detection, range validation, duplicate rejection, and Raw parsing.

## Decisions Made

- **2-source pipeline** (WrestlingAttitude + Wrestlenomics) instead of 3. A third source can be added later with a proper approach (RSS, direct site scrape), not Google search scraping.
- **Fail safe over fail dirty.** If the DOM structure changes, the scraper will produce fewer entries (or zero) rather than contaminated entries. The "never overwrite with fewer entries" guard protects against data loss.
- **Viewership ranges are generous.** Collision upper bound is 0.8M. If a show breaks out of its range due to a special event, the entry gets logged as a warning and rejected. The range can be adjusted.

## What's Left

- **Crash Override noted:** `scrape_raw()` fetches the page a second time even though `scrape_nielsen()` already parsed it. Could optimize to parse both from the same fetch. Not a blocker.
- **Crash Override noted:** `scrape_raw()` has duplicated DOM-walking logic for the Raw header `<p>`. Could be folded into `extract_sections_from_dom()`. Not a blocker.
- **No rate limiting** on API endpoints. `/api/ratings` reads from disk every request. Fine for current traffic.
- **App.jsx is 568 lines.** Works for current scope but should be broken into components if new features are added.

## Files Changed

- `backend/scraper.py` - Complete rewrite
- `backend/scraper_wrestlinginc.py` - Deleted
- `backend/scheduler.py` - Updated for 2 sources
- `backend/data_reconciler.py` - Updated naming, atomic writes
- `backend/file_utils.py` - New
- `backend/scrape_status.py` - Updated naming, atomic writes
- `backend/youtube_scraper.py` - Atomic writes
- `backend/app.py` - debug gating
- `frontend/src/App.jsx` - Removed WrestlingInc from status, updated copy
- `tests/test_scraper.py` - New (19 tests)
- `tests/fixtures/` - New (saved HTML snapshots)
