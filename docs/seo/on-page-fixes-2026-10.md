# On-page SEO fixes, checked 2026-10-28 (NOT YET MADE)

Checked against the served HTML at wrestling-ratings-production.up.railway.app
(the same build the custom domain will serve). Nothing here has been changed;
each item needs Todd's go-ahead because it alters public copy or adds a page.

## Do first (small, and they block the posts from helping)

1. **Crawlers see an empty page.** The served HTML is `<div id="root"></div>`
   plus head tags; the H1, the "About Pro Wrestling TV Ratings" text and the
   show schedule exist only after JavaScript runs. Google renders JS on a
   delay; Bing, social previews and most other crawlers do not. The project
   CLAUDE.md already requires SEO text on initial load. Fix: render the H1,
   about text and schedule into index.html at build time (a static block or a
   prerender step), and let React take over.
2. **Title, description and JSON-LD still name NWA Powerrr** (dropped from the
   site in March, commit 5e5b192) and ROH (now switched off). The title is 81
   characters; Google shows about 60. Proposed:
   - Title: `Pro Wrestling TV Ratings 2026: WWE, AEW and TNA Viewership`
   - Description: `Weekly TV ratings for WWE SmackDown, NXT, AEW Dynamite, Collision, TNA iMPACT and WWE Raw on Netflix. Interactive charts of viewers and 18-49 demo.`
3. **No share image.** `twitter:card` is `summary_large_image` but there is no
   `og:image` or `twitter:image`, so shared links show no picture. Add a
   1200x630 chart image.
4. **Page copy is out of date.**
   - "How This Website Works, Data Reconciliation" says "all three data
     sources" and "two out of three"; there are two.
   - Footer says "Updated weekly"; the scheduler runs every 6 hours.
   - The about text dates the Nielsen change to "October 2025"; the chart's
     reference line is Sept 26, 2025. Pick one. The same paragraph says "a
     subsequent adjustment in January 2026 partially reversed these declines";
     verify that or cut it.
   - The ROH note says YouTube view counts are tracked; with ROH switched off
     it should say ROH airs on HonorClub and is not charted.
5. **Sitemap `lastmod` has been 2026-03-20 since launch.** It reads
   `lastUpdated`, so it fixes itself once the scheduler runs in production.
   Check it after the deploy.

## Later (worth doing once posts exist)

6. **Report pages.** Each post at `/reports/<slug>`, rendered on the server so
   the text is in the HTML, listed in the sitemap, and linked from the home
   page. The sitemap generator in `backend/seo.py` lists one URL today.
7. **Dataset structured data.** Add a schema.org `Dataset` block (name,
   temporalCoverage 2025-01-01/.., variableMeasured viewers and 18-49 demo,
   creator) next to the existing `WebApplication` block. It makes the data
   eligible for Google Dataset Search.
8. **Per-show pages.** `/smackdown-ratings`, `/aew-dynamite-ratings` and so on,
   each with that show's chart and a short summary. These match the way people
   search ("smackdown ratings this week").
9. **Search Console.** Once the domain resolves, submit the sitemap in Google
   Search Console for `wrestlingratings.welchcommercesystems.com` (Todd action;
   whether a property exists is unknown).

## Already fine

- `robots.txt` allows everything and points at the sitemap.
- Canonical URL is set to the custom domain.
- `meta keywords` is ignored by Google; harmless, no action.
