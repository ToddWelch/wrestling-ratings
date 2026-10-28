# SESSION_LOG

Newest first. Never delete entries.

## 2026-10-28: Revive (site down, stale data, SEO drafts)

Handoff: `/home/todd/projects/Welch-Advisory-Team/scratch/handoff-wrestling-ratings-revive-2026-10-28.md`. Build class EXTERNAL. Branch `fix/revive-scrapers-scheduler`.

### Done
1. **Diagnosed the outage (read-only).** The custom domain has no DNS record and never had one. Cloudflare zone `welchcommercesystems.com` was added 2026-03-20 17:35 UTC; its audit log (333 entries since) shows no `wrestlingratings` record. Railway's custom-domain status: DNS requires update, required `CNAME wrestlingratings -> xn0jbavb.up.railway.app`, certificate issuing. The Railway service itself was healthy (deployment `2b40168c`, SUCCESS 2026-05-25, commit `bed0b1a`).
2. **Found the data had never refreshed.** The Dockerfile runs gunicorn, and the scheduler only started in `app.py`'s `__main__` block, so production served the 2026-03-20 seed file. That seed predates the 2026-03-22 contamination fix (SmackDown had 260 rows mixed with Dynamite and Collision numbers).
3. **Found both sources broken for 2026.** The WrestlingAttitude 2026 page moved to h3 headers plus tables (0 rows parsed). Wrestlenomics moved articles from `/tv-ratings/YYYY/` to `/articles/YYYY/` (0 rows parsed).
4. **Fixed on the branch** (commit `18944bf`): `backend/gunicorn.conf.py` starts the scheduler (one worker); single-thread executor with a 1h misfire grace; both page layouts parsed; Wrestlenomics URL fix; empty or failed sources raise `ScrapeError`; ROH YouTube switched off (uploads are clips, not episodes); `ratings.json` reseeded from a clean scrape (2025-01-01 to 2026-10-21). 52 tests, 33 new.
5. **Verified live:** the exact gunicorn command from a scratch copy scraped both sources (495 + 18 rows), and the YouTube API probe returned 32 ROH uploads (all clips, hence ROH off). Browser smoke of that local server in Chrome: charts, toggles, ranges, tooltip, status cards; no console messages.
6. **Monthly cost:** about $0.47 of Railway usage: 0.046 GB memory at $10 per GB-month ($0.46), CPU 0.0001 vCPU at $20 per vCPU-month (under $0.01), egress negligible. Measured before the scheduler ran in production; scheduled scraping adds a little CPU. Inside the Pro plan's $20 included credit. The workspace total was not readable (Not Authorized).
7. **SEO drafts (not published):** five posts in `docs/seo/post-drafts-2026-10.md`; on-page fix list in `docs/seo/on-page-fixes-2026-10.md`.
8. **CLAUDE.md "Current State"** rewritten (it said "not scaffolded").
9. **Crash Override: APPROVED WITH NOTES** on `a6fd1a3`, no blocking findings. It booted the Dockerfile command and confirmed one scheduler, the boot-time scrape, health under 16 ms during it, and a seed equal to a fresh scrape. Should-fix items addressed in the follow-up commit:
   - fail-loud now requires every `EXPECTED_SHOWS` show to yield entries, maps table columns by header text, reads `<th>` row cells, and range-checks Raw;
   - alerts fire when either source newly fails (once per outage), and `lastUpdated` moves only when data changes;
   - Wrestlenomics `air_date` fixes the January year rollover;
   - draft corrections: TNA 37 reported weeks of 40, Raw three missing weeks, SmackDown demo 0.28, the April 3 note.
   Live re-run with the stricter checks: both sources succeed, no alerts, nothing written (the seed matches). 74 tests.
10. **Railway overrides checked (reviewer's open item):** `startCommand` is null and the only variables are `SCRAPE_KEY`, `SLACK_WEBHOOK_URL` and `YOUTUBE_API_KEY`. No `GUNICORN_CMD_ARGS` or `WEB_CONCURRENCY`, so the Dockerfile CMD and `workers=1` apply. Crash Override confirmed this independently.
11. **Crash Override re-review: APPROVED WITH NOTES on `8888b9c`.** New time-bound item: Railway stops honoring `railway.toml` on 2026-12-01, and the service setting underneath is Railpack with no health check (decision 5 on the review page; `CARRY_FORWARD.md` item 4).
12. **Cross-model gate fired** (event 6: Crash Override named Slack delivery and Railway's post-Dec-1 behavior as unverified). Fresh-eyes Sonnet, prompt `scratch/fresh-eyes-prompt-revive-scrapers-2026-10-28.md`, findings `scratch/fresh-eyes-review-revive-scrapers-2026-10-28.md`: **0 BLOCKING, 3 IMPORTANT, 4 MINOR. Gate cleared.** All seven are AGREE and deferred to `CARRY_FORWARD.md`. The one re-review allowed for this ship point is spent, the top two need a design change (merge by date), and production today is worse on every count. The webhook-in-logs miss is logged in `/home/todd/.claude/logs/gate-catches.md`.

### In progress / state
- Review page for Todd: `/home/todd/projects/Wrestling Ratings/scratch/wrestling-ratings-revive-2026-10-28.html` (decisions: deploy, DNS record, region move, where posts live, Railway build settings; ROH off is settled and overridable).
- PR open, not merged. Production unchanged. No DNS, domain or variable change made.

### Next
1. Todd approves the merge and deploy (any merge to main deploys, because Railway has no watch patterns).
2. Merge the PR; watch the Railway deploy; confirm `/api/scrape-status` shows both sources succeeding and `lastUpdated` is current.
3. Todd adds the CNAME (the token here cannot write that zone); confirm DNS, the certificate, and a browser smoke at `https://wrestlingratings.welchcommercesystems.com`.
4. On Todd's go-ahead: on-page SEO fixes, then report pages for the posts.
5. Record the post-deploy results in the next change's log entry. A docs-only commit to main would itself redeploy.

### Open decisions (on the review page)
- Region: move from asia-southeast1 to US East (recommended; `/api/health` takes 0.44 to 0.66 s to first byte from Ashburn).
- Where posts live: `/reports/<slug>` on this site (recommended) or the WCS blog.
- Railway build settings: pin builder = Dockerfile and the health check in service settings before 2026-12-01 (recommended, with this deploy).

### Not done, recorded
- Deferred review and gate findings: `CARRY_FORWARD.md`, ranked (includes January 2027, the manual endpoints and the Railway cutoff).
- Whether `SLACK_WEBHOOK_URL` delivers is unverified. `/api/test-alert` would send a real Slack message, so it needs Todd's OK, and `CARRY_FORWARD.md` item 2 (webhook URL in logs) should land first.
- The YouTube status card reports OK even when the key is missing (existing behavior).
- The repo has no branch protection and no CI. Recommend protecting `main` and adding a pytest workflow (Todd's call, repo settings).

### Estimate vs actual
No estimate was given up front. Agent compute time about 3.5 hours, including diagnosis, the fix and two review rounds, the gate, the live runs, drafts and the review page.
