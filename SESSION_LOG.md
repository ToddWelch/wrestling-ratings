# SESSION_LOG

Newest first. Never delete entries.

## 2026-10-29 to 31: Chart fits its data, ranked tooltip, Leaderboard

Todd's requests (2026-10-29): (1) the weekly chart's y-axis top should be the top value rounded up to a whole number (3.9 to 4; 5 or 6 if ever needed), at the same height; (2) sort the hover list highest first; (3) a leaderboard for the latest complete week above Weekly Viewership.

### Done
1. **PR #3 merged** (`81515af`, reviewed head `0500f52`) and deployed (`73bd5cda`). Details:
   - **Axis:** the y-axis top is the highest visible value in the range, rounded up (viewers to a whole million, demo to the next 0.1), with half-million gridlines when the top is 2 or less.
   - **Tooltip:** rows sorted highest first.
   - **Leaderboard:** above the chart; it shows the latest week every show active in the last 2 weeks has reported, ranked by the selected metric, with Raw listed under it, not ranked.
   - **Code layout:** logic in `frontend/src/chartLogic.js` (19 tests, `cd frontend && npm test`, Node's built-in runner); show config and dates in `shows.js`.
2. **Crash Override round 1 (REVISE AND RESUBMIT on `4aa19a8`)** caught a real bug: `weekOf` took the weekday in local time and formatted it in UTC, so anyone east of UTC saw "Week of Oct 11" (a Sunday). That also fixed the same label bug already in the chart. Other fixes in that round:
   - phone layout from 320 to 390 px;
   - the active-show window cut from 5 to 2 weeks (one quiet show had kept the board weeks stale in a replay of last year);
   - tests across five time zones and daylight-saving changes.
   Round 2 APPROVED `0500f52`.
3. **PR #4 merged** (`f1eb997`, reviewed head `13c15bb`), deployed (`992e8d18`): Raw goes last in the tooltip, Todd's call 2026-10-31.
4. **Verified live** with headless Chromium (Playwright from `~/projects/winning-post`). Todd's VS Code tunnel was not forwarding, so there was no interactive browser.
   - Axis 0 to 4 on 1Y, half steps with Raw off.
   - Tooltip sorted, Raw last.
   - Leaderboard advanced by itself to the **week of Oct 19** when Collision and TNA numbers landed.
   - Heading correct in New York, Berlin, Tokyo and Sydney.
   - Phone widths clean, no console errors.
   - Live bundles match the reviewed builds byte for byte.
5. No cross-model gate fired: none of the six events, and Crash Override named nothing material unverified.

### State / next
- Todd should glance at the leaderboard on his phone; touch and iOS Safari were not testable here.
- New residuals are in `CARRY_FORWARD.md`: leaderboard accessibility, a "not rated this week" line, `App.jsx` size, no CI for frontend tests.
- Earlier next steps still stand: `CARRY_FORWARD.md` item 1, then the on-page SEO fixes and `/reports/<slug>` pages.

## 2026-10-29: Railway IaC applied and merged; revive complete

### Done
1. **Gate on the IaC PR:** fresh-eyes Sonnet, prompt `scratch/fresh-eyes-prompt-railway-iac-2026-10-28.md`, findings `scratch/fresh-eyes-review-railway-iac-2026-10-28.md`: 0 BLOCKING, 1 IMPORTANT, 1 MINOR. Cleared. IMPORTANT (merging before apply drops the build to Railpack) is AGREE and handled by the rollout order. MINOR (10 s health-check headroom) is AGREE and deferred: it matches the old setting and every deploy passed.
2. **Crash Override approved `e6c8943`** with the pinned plan `scratch/railway-plan.json` (CLI 5.47.2, `destructive: false`, 2 `resource.update`, `sourceTree` = `e6c8943:.railway`).
3. **Applied** with `railway config apply --plan scratch/railway-plan.json --yes` (no `--confirm-destructive`), approved by Todd in session. Before and after on the service: `dockerfilePath` null to `Dockerfile`, `healthcheckPath` null to `/api/health`, `healthcheckTimeout` null to 10. Every other field read was unchanged (`ipv6EgressEnabled`, restart policy, source and others), and the variable names were unchanged. The legacy `serviceInstance.builder` field still reads `RAILPACK`, while the config graph says `DOCKERFILE` and `plan --detailed-exit-code` exits 0. Apply redeploy `107955d8` SUCCESS; scrapes at 00:04:57Z.
4. **Merged PR #2** with Todd's OK, pinned to `e6c8943`, as merge commit `4a25716`. Deployment `9742bada`, the first without `railway.toml`: `configFile` none, builder DOCKERFILE, `dockerfilePath` Dockerfile, health check `/api/health` 10 s, region us-east4-eqdc4a, SUCCESS. Both sources scraped at 10:18:14Z, after the deploy. **The 2026-12-01 cutoff is closed.**

### State
- Live: `https://wrestlingratings.welchcommercesystems.com`, data through SmackDown 2026-10-23, scheduler every 6 h.
- Railway settings are code (`.railway/railway.ts`); see CLAUDE.md before changing them. The repo directory is `railway link`ed to the project (local CLI config only), so `railway config plan` works from the repo root.
- Todd's decisions still to build: report pages at `/reports/<slug>` for the post drafts, then the on-page SEO fixes (`docs/seo/`).
- Not committed by design: `/home/todd/.claude/infrastructure-access.md` (token widening record) and `/home/todd/.claude/logs/gate-catches.md` (one entry; that file's diff also holds other sessions' entries). That repo takes changes through its snapshot or a PR.

### Next
1. `CARRY_FORWARD.md` item 1 (merge stored data by date, with a removal rule) and the rest of that list.
2. On-page SEO fixes, ROH out of the UI, then `/reports/<slug>` pages and the posts after Todd's edits.
3. Slack test alert, only with Todd's OK. The webhook-in-logs fix is already live.

### Estimate vs actual
No estimate up front. Agent compute time across 2026-10-28 and 29 is about 5 hours, including two PRs, three review rounds and two gates.

## 2026-10-28 (later): Deployed, region moved, DNS live, Railway IaC migration

Todd's decisions (review page, pasted back): deploy yes; region us-east4; posts at `/reports/<slug>` on this site; Railway "the permanent fix"; ROH off. In chat: remove the push deny rule, widen the Cloudflare token, IaC as the next PR.

### Done
1. **Deployed.** PR #1 merged at the reviewed head `6d2b0c0` as merge commit `c520d8d` (`--match-head-commit`). Railway deployment `15086366` SUCCESS. The scheduler started at boot; WrestlingAttitude 495 and Wrestlenomics 18 entries, both success. It picked up SmackDown 2026-10-23, a new row.
2. **Push unblock.** `/home/todd/projects/Wrestling Ratings/.claude/settings.local.json` had `deny: Bash(git push *)` (machine-local, from 2026-03-22). Removed with Todd's approval. The running session kept the cached rule, so Todd ran the first push himself.
3. **Region moved** to `us-east4-eqdc4a` (`serviceInstanceUpdate` `multiRegionConfig`, then a redeploy, `4625abfb` SUCCESS). `/api/health` time to first byte from Ashburn went from 0.44 to 0.66 s to 0.026 to 0.033 s. Scrapes succeeded again after the move.
4. **Cloudflare token widened:** "Cloudflare Agent Token - 2026-04-15" DNS Write gained `welchcommercesystems.com` at 23:46 UTC. The IP condition and the other 3 policies were unchanged, and the value did not roll. Recorded in `/home/todd/.claude/infrastructure-access.md`.
5. **DNS live:** `CNAME wrestlingratings -> xn0jbavb.up.railway.app`, proxied, record id `75283a2637d99d2b3affec7771b42f14`, created 23:51 UTC. `https://wrestlingratings.welchcommercesystems.com` returns 200 and `/api/health` ok; the sitemap `lastmod` is now 2026-10-28.
6. **Browser smoke at the real domain** (Chrome): chart, ALL range, NXT toggle, tooltip, no console errors. Earlier on the railway.app URL: key demo, 3M, Collision toggle, tooltip on the week of Oct 12 matching the data, status cards all OK.
7. **Railway IaC** (branch `chore/railway-iac-migration`): `.railway/railway.ts` declares service `wrestling-ratings` with the Dockerfile builder, the `/api/health` check (10 s), one replica in us-east4, and the variables as `preserve()`. `railway.toml` removed. `railway config plan`: 0 add, 2 change (builder null to DOCKERFILE; health check null to /api/health, 10), 0 destroy. `railway config migrate` was NOT used as generated: it named the service "Wrestling Ratings", which would likely have created a second service, and it dropped the Dockerfile setting to a comment.

### In progress / state
- IaC PR #2: Crash Override APPROVED WITH NOTES on `70b8dd9`; its doc notes are folded in (the file is the complete desired state, omit = delete; stale DNS line; exact package pin with `npm ci`; `WRESTLING-RATINGS.md` marks `railway.toml` superseded). Rollout:
  1. pinned plan (`railway config plan --out`, CLI 5.47.2) at the final head;
  2. cross-model gate on that plan (event 1, first write through the IaC path);
  3. `railway config apply --plan <file>`, approved by Todd in chat ("apply only after the plan shows it updates wrestling-ratings and creates nothing"). Apply most likely redeploys `c520d8d`;
  4. verify that deploy and that `railway config plan --detailed-exit-code` exits 0;
  5. **Todd's OK before the merge** (the PR declares the service's variable list);
  6. merge, then verify the deployment's builder is DOCKERFILE, the health check is set, there is no `configFile`, and `/api/scrape-status` `lastScrape` is after the deploy.
  **Apply must come before the merge**: once `railway.toml` is gone, the merge deploy reads service settings, and the setting underneath is RAILPACK.
- Railway still shows the custom domain's certificate as "issuing" with DNS "requires update". It may lag; the site already serves over Cloudflare. The WCS apex, proxied the same way, shows VALID and PROPAGATED.

### Next
1. Finish the IaC PR as above, then verify the deployment used the Dockerfile builder and the scheduler started.
2. Next PR: `CARRY_FORWARD.md` items (merge by date first), then the on-page SEO fixes and `/reports/<slug>` pages.
3. Slack test alert only with Todd's OK.

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
11. **Crash Override re-review: APPROVED WITH NOTES on `8888b9c`.** New time-bound item: Railway stops honoring `railway.toml` on 2026-12-01, and the service setting underneath is Railpack with no health check (decision 5 on the review page; `CARRY_FORWARD.md` item 3).
12. **Cross-model gate fired** (event 6: Crash Override named Slack delivery and Railway's post-Dec-1 behavior as unverified). Fresh-eyes Sonnet, prompt `scratch/fresh-eyes-prompt-revive-scrapers-2026-10-28.md`, findings `scratch/fresh-eyes-review-revive-scrapers-2026-10-28.md`: **0 BLOCKING, 3 IMPORTANT, 4 MINOR. Gate cleared.** All seven are AGREE. Six are deferred to `CARRY_FORWARD.md`: the one re-review allowed for this ship point is spent, the top two need a design change (merge by date), and production today is worse on every count. The webhook-in-logs miss is logged in `/home/todd/.claude/logs/gate-catches.md`.
13. **Webhook-in-logs fixed before merge** (gate M-2). Crash Override's trivial-bar pass on `e7356ad` pointed out the leak covers any `requests` failure, not only HTTP errors, and goes live with this deploy's automatic alerts. `_send_alert` now logs the exception type and HTTP status only; two tests fail without the fix. The fix stays inside the finding, so it gets a confirm from Crash Override, not a re-review. Found alongside it: the same latent leak for the YouTube API key, never reached while ROH is off (`CARRY_FORWARD.md`, before ROH is switched back on). 76 tests.

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
- Whether `SLACK_WEBHOOK_URL` delivers is unverified. `/api/test-alert` would send a real Slack message, so it needs Todd's OK.
- The YouTube status card reports OK even when the key is missing (existing behavior).
- The repo has no branch protection and no CI. Recommend protecting `main` and adding a pytest workflow (Todd's call, repo settings).

### Estimate vs actual
No estimate was given up front. Agent compute time about 3.5 hours, including diagnosis, the fix and two review rounds, the gate, the live runs, drafts and the review page.
