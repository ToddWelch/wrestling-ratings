import { NIELSEN_SHOWS, RAW_SHOW, weekOf } from "./shows.js";

/* ======= Y-AXIS SCALE ======= */

// Top of the weekly chart's y-axis: the highest value in view, rounded up to
// the next whole million for viewers (3.9 -> 4) or the next 0.1 for the demo,
// so the lines spread across the full chart height. Viewer gridlines fall on
// half millions when the top is 2 or less, so the low lines keep references.
export function yAxisScale(rows, keys, metric) {
  const step = metric === "demo" ? 0.1 : 1;
  let max = 0;
  for (const row of rows) {
    for (const key of keys) {
      const v = row[key];
      if (typeof v === "number" && v > max) max = v;
    }
  }
  // The epsilon keeps float noise (0.30000000000000004) from adding a step
  const top = Math.max(1, Math.ceil(max / step - 1e-9)) * step;
  const tickStep = metric === "viewers" && top <= 2 ? 0.5 : step;
  const ticks = [];
  for (let i = 0; i * tickStep <= top + 1e-9; i++) ticks.push(Number((i * tickStep).toFixed(1)));
  return { top: Number(top.toFixed(1)), ticks };
}

/* ======= TOOLTIP ORDER ======= */

// Tooltip rows, highest value first, so the order reads as that week's ranking.
// Raw ranks by its number like every other show (Todd, 2026-11-05).
export function rankPayload(payload) {
  return payload.filter((p) => p.value != null).sort((a, b) => b.value - a.value);
}

/* ======= VIEWER NUMBERS ======= */

// "1.327M", or "2.5M" for Raw: Netflix publishes one decimal, and three would
// imply precision it doesn't have. A missing number renders as "n/a".
export function formatViewers(value, showId) {
  if (value == null) return "n/a";
  return `${value.toFixed(showId === RAW_SHOW.id ? 1 : 3)}M`;
}

/* ======= LEADERBOARD ======= */

// A show that last reported more than this many weeks before the newest data
// (ended, on hiatus, late) no longer holds the leaderboard back. Short on
// purpose: a dropped show's number rejoins its week as soon as it arrives,
// while a long window kept the board weeks stale behind one quiet show.
const ACTIVE_WEEKS = 2;

function newestWeek(entries) {
  let newest = null;
  for (const e of entries) {
    const w = weekOf(e.date);
    if (!newest || w > newest) newest = w;
  }
  return newest;
}

function shiftDays(dateStr, days) {
  const d = new Date(dateStr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().split("T")[0];
}

// The entry a show aired in the given week; if it aired twice, the later one,
// matching how the chart keeps one point per show per week.
function entryInWeek(entries, week) {
  let found = null;
  for (const e of entries) {
    if (weekOf(e.date) === week && (!found || e.date > found.date)) found = e;
  }
  return found;
}

// Rank the shows for the latest complete week.
//
// A show's number for a week can no longer arrive once it has reported a
// later week, so a week is complete when every active Nielsen show's newest
// entry falls in that week or later. Shows with no number that week (preempted,
// "NO DATA") are left out rather than holding the week back. Raw never moves
// the week; it joins the list if it has a number for that week.
//
// Raw ranks by its number and is marked `footnoted`, since it is Netflix global
// views, not Nielsen (Todd, 2026-11-05). A row with no number for the metric
// (Raw on the key demo) can't be ranked, so it comes back in `unranked`.
export function buildLeaderboard(nielsen, raw, metric) {
  const series = NIELSEN_SHOWS
    .map((show) => ({ show, entries: nielsen?.[show.id] || [] }))
    .map((s) => ({ ...s, newest: newestWeek(s.entries) }))
    .filter((s) => s.newest);
  if (!series.length) return null;

  const latest = series.reduce((w, s) => (s.newest > w ? s.newest : w), series[0].newest);
  const cutoff = shiftDays(latest, -7 * ACTIVE_WEEKS);
  const active = series.filter((s) => s.newest >= cutoff);
  const week = active.reduce((w, s) => (s.newest < w ? s.newest : w), active[0].newest);

  const rows = active
    .map((s) => {
      const e = entryInWeek(s.entries, week);
      return e ? { ...s.show, date: e.date, viewers: e.viewers, demo: e.demo ?? null } : null;
    })
    .filter(Boolean);

  const rawEntry = entryInWeek(raw || [], week);
  if (rawEntry) {
    rows.push({ ...RAW_SHOW, date: rawEntry.date, viewers: rawEntry.viewers, demo: null, footnoted: true });
  }

  const ranked = rows
    .filter((row) => row[metric] != null)
    .sort((a, b) => b[metric] - a[metric] || b.viewers - a.viewers);
  const unranked = rows.filter((row) => row[metric] == null);

  return { week, ranked, unranked };
}
