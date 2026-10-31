// Run with: cd frontend && npm test (Node's built-in test runner, no dependencies)
import { test } from "node:test";
import assert from "node:assert/strict";
import { yAxisScale, rankPayload, buildLeaderboard } from "./chartLogic.js";
import { weekOf } from "./shows.js";

/* ======= yAxisScale ======= */

test("viewers: top rounds up to the next whole million", () => {
  const rows = [{ raw: 3.9, smackdown: 1.3 }, { raw: 2.5, smackdown: 1.58 }];
  assert.deepEqual(yAxisScale(rows, ["raw", "smackdown"], "viewers"), { top: 4, ticks: [0, 1, 2, 3, 4] });
});

test("viewers: a whole-number peak stays put", () => {
  assert.equal(yAxisScale([{ raw: 4 }], ["raw"], "viewers").top, 4);
});

test("viewers: hidden series do not count, and a low top gets half-million gridlines", () => {
  const rows = [{ raw: 5.9, smackdown: 1.58, tna: 0.3 }];
  assert.deepEqual(yAxisScale(rows, ["smackdown", "tna"], "viewers"), { top: 2, ticks: [0, 0.5, 1, 1.5, 2] });
});

test("viewers: above 4 bumps to 5 or 6", () => {
  assert.equal(yAxisScale([{ raw: 4.2 }], ["raw"], "viewers").top, 5);
  assert.equal(yAxisScale([{ raw: 5.9 }], ["raw"], "viewers").top, 6);
});

test("demo: top rounds up to the next 0.1", () => {
  const rows = [{ smackdown_demo: 0.32 }, { smackdown_demo: 0.42, nxt_demo: 0.14 }];
  assert.deepEqual(yAxisScale(rows, ["smackdown_demo", "nxt_demo"], "demo"), { top: 0.5, ticks: [0, 0.1, 0.2, 0.3, 0.4, 0.5] });
});

test("demo: float noise does not add a step", () => {
  assert.equal(yAxisScale([{ x: 0.1 + 0.2 }], ["x"], "demo").top, 0.3);
});

test("no visible data still gives a usable axis", () => {
  assert.deepEqual(yAxisScale([], ["raw"], "viewers"), { top: 1, ticks: [0, 0.5, 1] });
  assert.equal(yAxisScale([{ raw: null }], ["raw"], "demo").top, 0.1);
});

/* ======= rankPayload ======= */

test("tooltip rows sort highest first and drop empty values", () => {
  const payload = [
    { name: "NXT", value: 0.732 },
    { name: "TNA iMPACT", value: null },
    { name: "SmackDown", value: 1.327 },
    { name: "Dynamite", value: 0.715 },
  ];
  assert.deepEqual(rankPayload(payload).map((p) => p.name), ["SmackDown", "NXT", "Dynamite"]);
});

/* ======= buildLeaderboard ======= */

// Real numbers from the 2026-10-28 scrape: SmackDown, NXT and Dynamite have
// reported the week of Oct 19; Collision and TNA have not, so the latest
// complete week is Oct 12.
const nielsen = {
  smackdown: [
    { date: "2026-10-09", viewers: 1.352, demo: 0.32 },
    { date: "2026-10-16", viewers: 1.327, demo: 0.32 },
    { date: "2026-10-23", viewers: 1.3, demo: 0.3 },
  ],
  nxt: [
    { date: "2026-10-13", viewers: 0.732, demo: 0.14 },
    { date: "2026-10-20", viewers: 0.655, demo: 0.1 },
  ],
  dynamite: [
    { date: "2026-10-14", viewers: 0.715, demo: 0.14 },
    { date: "2026-10-21", viewers: 0.661, demo: 0.15 },
  ],
  collision: [
    { date: "2026-10-10", viewers: 0.372, demo: 0.04 },
    { date: "2026-10-14", viewers: 0.514, demo: 0.1 },
  ],
  tna: [{ date: "2026-10-15", viewers: 0.252, demo: 0.05 }],
};
const raw = [
  { date: "2026-10-12", viewers: 2.5 },
  { date: "2026-10-19", viewers: 2.5 },
];

test("leaderboard picks the latest week every active show has reported", () => {
  assert.equal(buildLeaderboard(nielsen, raw, "viewers").week, "2026-10-12");
});

test("leaderboard ranks by viewers", () => {
  const board = buildLeaderboard(nielsen, raw, "viewers");
  assert.deepEqual(board.ranked.map((r) => [r.id, r.date, r.viewers]), [
    ["smackdown", "2026-10-16", 1.327],
    ["nxt", "2026-10-13", 0.732],
    ["dynamite", "2026-10-14", 0.715],
    ["collision", "2026-10-14", 0.514],
    ["tna", "2026-10-15", 0.252],
  ]);
});

test("leaderboard ranks by demo, ties broken by viewers", () => {
  const board = buildLeaderboard(nielsen, raw, "demo");
  assert.deepEqual(board.ranked.map((r) => r.id), ["smackdown", "nxt", "dynamite", "collision", "tna"]);
});

test("Raw is reported separately and never ranked", () => {
  const board = buildLeaderboard(nielsen, raw, "viewers");
  assert.ok(!board.ranked.some((r) => r.id === "raw"));
  assert.deepEqual([board.netflix.date, board.netflix.viewers], ["2026-10-12", 2.5]);
});

test("a show with no number that week is left out, not waited for", () => {
  const preempted = { ...nielsen, tna: [{ date: "2026-10-08", viewers: 0.214, demo: 0.03 }, { date: "2026-10-22", viewers: 0.2, demo: 0.04 }] };
  const board = buildLeaderboard(preempted, raw, "viewers");
  assert.equal(board.week, "2026-10-12");
  assert.ok(!board.ranked.some((r) => r.id === "tna"));
});

test("a show last reported 2 weeks before the newest data still holds the week", () => {
  // Newest data is the week of Oct 19; Oct 5 is exactly 2 weeks earlier
  const late = { ...nielsen, tna: [{ date: "2026-10-08", viewers: 0.214, demo: 0.03 }] };
  assert.equal(buildLeaderboard(late, raw, "viewers").week, "2026-10-05");
});

test("a show silent for more than 2 weeks does not hold the week back", () => {
  const quiet = { ...nielsen, tna: [{ date: "2026-10-01", viewers: 0.182, demo: 0.02 }] };
  const board = buildLeaderboard(quiet, raw, "viewers");
  assert.equal(board.week, "2026-10-12");
  assert.ok(!board.ranked.some((r) => r.id === "tna"));
});

/* ======= time zones ======= */

// weekOf must give the same Monday wherever the browser is; it once returned
// the Sunday for anyone east of UTC. Node honours a runtime TZ change.
const ZONES = ["America/Los_Angeles", "UTC", "Europe/London", "Asia/Tokyo", "Pacific/Kiritimati"];
const WEEKS = {
  "2026-10-12": "2026-10-12", // Monday
  "2026-10-18": "2026-10-12", // Sunday
  "2026-03-08": "2026-03-02", // US clocks change
  "2026-03-29": "2026-03-23", // EU clocks change
  "2026-10-25": "2026-10-19", // EU clocks change back
  "2026-11-01": "2026-10-26", // US clocks change back
  "2026-01-01": "2025-12-29", // across the new year
};

function inZone(zone, fn) {
  const saved = process.env.TZ;
  process.env.TZ = zone;
  try { return fn(); } finally {
    if (saved === undefined) delete process.env.TZ; else process.env.TZ = saved;
  }
}

test("weekOf gives the same Monday in every time zone", () => {
  for (const zone of ZONES) {
    inZone(zone, () => {
      for (const [date, monday] of Object.entries(WEEKS)) {
        assert.equal(weekOf(date), monday, `${date} in ${zone}`);
      }
    });
  }
});

test("leaderboard week and ranking are the same in every time zone", () => {
  for (const zone of ZONES) {
    inZone(zone, () => {
      const board = buildLeaderboard(nielsen, raw, "viewers");
      assert.equal(board.week, "2026-10-12", zone);
      assert.deepEqual(board.ranked.map((r) => r.id), ["smackdown", "nxt", "dynamite", "collision", "tna"], zone);
    });
  }
});

test("no data gives no leaderboard", () => {
  assert.equal(buildLeaderboard({}, [], "viewers"), null);
  assert.equal(buildLeaderboard(null, null, "viewers"), null);
});
