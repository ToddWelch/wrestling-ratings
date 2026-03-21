import { useState, useMemo, useEffect, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts";

/* ======= SHOW CONFIG ======= */
const NIELSEN_SHOWS = [
  { id: "smackdown", name: "SmackDown", color: "#60A5FA", network: "USA/SyFy", day: "Fri" },
  { id: "nxt", name: "NXT", color: "#FACC15", network: "CW", day: "Tue" },
  { id: "dynamite", name: "Dynamite", color: "#EF4444", network: "TBS", day: "Wed" },
  { id: "collision", name: "Collision", color: "#F472B6", network: "TNT", day: "Sat" },
  { id: "tna", name: "TNA iMPACT", color: "#22C55E", network: "AMC", day: "Thu" },
];

const RAW_SHOW = { id: "raw", name: "WWE Raw", color: "#DC2626", network: "Netflix", day: "Mon" };

const STREAMING_SHOWS = [
  { id: "raw", name: "WWE Raw", color: "#DC2626", platform: "Netflix", metric: "Global Views (M)" },
  { id: "roh", name: "ROH", color: "#F97316", platform: "HonorClub/YT", metric: "YouTube Views (K)" },
  { id: "nwa", name: "NWA Powerrr", color: "#06B6D4", platform: "Roku/YT", metric: "YouTube Views (K)" },
];

/* ======= HELPERS ======= */
const MO = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function fmtTimeAgo(date) {
  const s = Math.floor((Date.now() - date.getTime()) / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function fmtDate(v) {
  const d = v instanceof Date ? v : typeof v === "number" ? new Date(v) : new Date(v + "T00:00:00");
  return `${MO[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

function toTs(dateStr) {
  return new Date(dateStr + "T00:00:00").getTime();
}

function fmtLabel(ts, weekly) {
  const d = new Date(ts);
  if (weekly) {
    return `${MO[d.getMonth()]} ${d.getDate()}`;
  }
  return `${MO[d.getMonth()]} '${String(d.getFullYear()).slice(2)}`;
}

function pickTicks(data, weekly) {
  if (!data.length) return [];
  if (weekly) {
    return data.map((d) => d.ts);
  }
  // Monthly: one tick on the 1st of each month within the data range
  const first = data[0].ts;
  const last = data[data.length - 1].ts;
  const ticks = [];
  const start = new Date(first);
  // Start at the 1st of the next month after the first data point
  let d = new Date(start.getFullYear(), start.getMonth() + 1, 1);
  while (d.getTime() <= last) {
    ticks.push(d.getTime());
    d = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  }
  return ticks;
}

const RANGES = [
  { id: "1m", label: "1M", days: 30 },
  { id: "3m", label: "3M", days: 90 },
  { id: "6m", label: "6M", days: 180 },
  { id: "1y", label: "1Y", days: 365 },
  { id: "all", label: "ALL", days: 9999 },
];

function filterRange(data, range) {
  if (range === "all") return data;
  const days = RANGES.find((r) => r.id === range)?.days || 365;
  const cut = new Date();
  cut.setDate(cut.getDate() - days);
  const cs = cut.toISOString().split("T")[0];
  return data.filter((d) => d.date >= cs);
}

/* ======= TRANSFORM API DATA TO CHART FORMAT ======= */

// Get the Monday of the week for a given date string
function weekOf(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon, ...
  const diff = day === 0 ? -6 : 1 - day; // shift to Monday
  d.setDate(d.getDate() + diff);
  return d.toISOString().split("T")[0];
}

function transformNielsen(nielsen, streaming) {
  if (!nielsen) return [];
  const weekMap = {};

  for (const [showId, entries] of Object.entries(nielsen)) {
    for (const entry of entries) {
      const week = weekOf(entry.date);
      if (!weekMap[week]) {
        weekMap[week] = { date: week, ts: toTs(week) };
      }
      weekMap[week][showId] = entry.viewers;
      weekMap[week][showId + "_demo"] = entry.demo;
    }
  }

  // Merge Raw (Netflix) into the combined chart data
  if (streaming?.raw) {
    for (const entry of streaming.raw) {
      const week = weekOf(entry.date);
      if (!weekMap[week]) {
        weekMap[week] = { date: week, ts: toTs(week) };
      }
      weekMap[week].raw = entry.viewers;
    }
  }

  return Object.values(weekMap).sort((a, b) => a.ts - b.ts);
}

function transformStreaming(streaming) {
  if (!streaming) return [];
  const weekMap = {};

  for (const [showId, entries] of Object.entries(streaming)) {
    for (const entry of entries) {
      const week = weekOf(entry.date);
      if (!weekMap[week]) {
        weekMap[week] = { date: week, ts: toTs(week) };
      }
      if (showId === "raw") {
        weekMap[week][showId] = entry.viewers;
      } else {
        weekMap[week][showId] = entry.views ? entry.views / 1000 : null;
      }
    }
  }

  return Object.values(weekMap).sort((a, b) => a.ts - b.ts);
}

/* ======= TOOLTIP ======= */
function Tip({ active, payload, label, metric }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#0c1812", border: "1px solid #2a5a3a", borderRadius: 6,
      padding: "10px 14px", fontSize: 12, fontFamily: "monospace",
    }}>
      <div style={{ color: "#8acca0", marginBottom: 6, fontWeight: 700, fontSize: 13 }}>{fmtDate(label)}</div>
      {payload.filter((p) => p.value != null).map((p, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "2px 0" }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: p.color, flexShrink: 0 }} />
          <span style={{ color: "#8acca0", flex: 1 }}>{p.name}</span>
          <span style={{ color: "#e8f5ee", fontWeight: 700 }}>
            {metric === "demo" ? p.value.toFixed(2) : p.value.toFixed(3) + "M"}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ======= MAIN ======= */
export default function App() {
  const [metric, setMetric] = useState("viewers");
  const [range, setRange] = useState("1y");
  const [shows, setShows] = useState(
    Object.fromEntries([...NIELSEN_SHOWS, ...STREAMING_SHOWS].map((s) => [s.id, true]))
  );
  const [nielsenData, setNielsenData] = useState([]);
  const [streamingData, setStreamingData] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [scrapeDetails, setScrapeDetails] = useState({});

  const toggle = (id) => setShows((p) => ({ ...p, [id]: !p[id] }));

  const fetchRatings = useCallback(async () => {
    try {
      const resp = await fetch("/api/ratings");
      const data = await resp.json();

      if (data.lastUpdated !== lastUpdated) {
        setNielsenData(transformNielsen(data.nielsen, data.streaming));
        setStreamingData(transformStreaming(data.streaming));
        setLastUpdated(data.lastUpdated);
        if (data.scrapeDetails) setScrapeDetails(data.scrapeDetails);
      }
    } catch (e) {
      console.error("Failed to fetch ratings:", e);
    }
  }, [lastUpdated]);

  useEffect(() => {
    fetchRatings();
    const interval = setInterval(fetchRatings, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchRatings]);

  const fN = useMemo(() => filterRange(nielsenData, range), [nielsenData, range]);
  const fS = useMemo(() => filterRange(streamingData, range), [streamingData, range]);

  const isWeekly = range === "1m" || range === "3m";
  const nielsenTicks = useMemo(() => pickTicks(fN, isWeekly), [fN, isWeekly]);
  const streamingTicks = useMemo(() => pickTicks(fS, isWeekly), [fS, isWeekly]);

  const btn = (on) => ({
    background: on ? "#4ade8018" : "transparent",
    border: on ? "1px solid #4ade8040" : "1px solid #1a3a2a",
    borderRadius: 3, padding: "2px 7px", cursor: "pointer",
    color: on ? "#4ade80" : "#8acca0",
    fontSize: 12, fontWeight: 700, fontFamily: "monospace", transition: "all 0.15s",
  });

  const showBtn = (s, on) => ({
    background: on ? `${s.color}18` : "transparent",
    border: `1px solid ${on ? s.color + "60" : "#1a3a2a"}`,
    borderRadius: 3, padding: "2px 7px", cursor: "pointer",
    color: on ? s.color : "#8acca0",
    fontSize: 12, fontWeight: 700, fontFamily: "monospace", opacity: on ? 1 : 0.5,
    transition: "all 0.15s",
  });

  const dot = (color, on) => ({
    display: "inline-block", width: 7, height: 7, borderRadius: "50%",
    background: on ? color : "#1a3a2a", marginRight: 5, verticalAlign: "middle",
  });

  return (
    <div style={{ background: "#070f0b", minHeight: "100vh", color: "#c0d8cc", fontFamily: "'Segoe UI',system-ui,sans-serif" }}>

      {/* === HEADER === */}
      <header style={{ borderBottom: "1px solid #1a3a2a", padding: "16px 20px 14px", background: "linear-gradient(180deg, #0e2118 0%, #070f0b 100%)" }}>
        <h1 style={{ margin: 0, fontSize: 21, fontWeight: 800, color: "#e8f5ee", letterSpacing: "-0.02em" }}>
          <span style={{ color: "#4ade80" }}>Pro Wrestling</span> TV Ratings Tracker
        </h1>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8, margin: "4px 0 0" }}>
          <p style={{ margin: 0, fontSize: 14, color: "#8acca0", fontFamily: "monospace", letterSpacing: "0.1em" }}>
            WEEKLY VIEWERSHIP FOR WWE, AEW, TNA, ROH, AND NWA &bull; NIELSEN + STREAMING
          </p>
          {lastUpdated && (
            <span style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace" }}>
              Last updated: {fmtDate(new Date(lastUpdated))}
            </span>
          )}
        </div>

        {/* Metric + Range */}
        <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", marginRight: 6, letterSpacing: "0.08em" }}>METRIC</span>
            <button onClick={() => setMetric("viewers")} style={btn(metric === "viewers")}>VIEWERS</button>
            <button onClick={() => setMetric("demo")} style={btn(metric === "demo")}>KEY DEMO 18-49</button>
          </div>
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", marginRight: 6, letterSpacing: "0.08em" }}>RANGE</span>
            {RANGES.map((r) => (
              <button key={r.id} onClick={() => setRange(r.id)} style={btn(range === r.id)}>{r.label}</button>
            ))}
          </div>
        </div>

        {/* Show toggles */}
        <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", marginRight: 6, alignSelf: "center", letterSpacing: "0.08em" }}>SHOWS</span>
          {NIELSEN_SHOWS.map((s) => (
            <button key={s.id} onClick={() => toggle(s.id)} style={showBtn(s, shows[s.id])}>
              <span style={dot(s.color, shows[s.id])} />{s.name}
              <span style={{ fontSize: 12, opacity: 0.5, marginLeft: 4 }}>({s.network})</span>
            </button>
          ))}
          <button onClick={() => toggle("raw")} style={showBtn(RAW_SHOW, shows.raw)}>
            <span style={dot(RAW_SHOW.color, shows.raw)} />{RAW_SHOW.name}
            <span style={{ fontSize: 12, opacity: 0.5, marginLeft: 4 }}>({RAW_SHOW.network})</span>
          </button>
        </div>
      </header>

      {/* === COMBINED VIEWERSHIP CHART === */}
      <section style={{ padding: "16px 12px 8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, paddingLeft: 8, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#e8f5ee" }}>Weekly Viewership</h2>
          <span style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", letterSpacing: "0.08em" }}>
            {metric === "viewers" ? "TOTAL VIEWERS (MILLIONS)" : "18-49 KEY DEMO RATING"}
          </span>
        </div>
        {shows.raw && metric === "viewers" && (
          <div style={{ paddingLeft: 8, marginBottom: 6, fontSize: 13, color: "#DC2626", fontFamily: "monospace" }}>
            * WWE Raw uses Netflix global views, not Nielsen. Not directly comparable to cable ratings.
          </div>
        )}
        <ResponsiveContainer width="100%" height={370}>
          <LineChart data={fN} margin={{ top: 5, right: 20, left: 0, bottom: 30 }}>
            <CartesianGrid strokeDasharray="6 4" stroke="#1a3a2a" />
            <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]}
              ticks={nielsenTicks}
              tickFormatter={(ts) => fmtLabel(ts, isWeekly)}
              tick={{ fill: "#6a9a7a", fontSize: 12, fontFamily: "monospace" }}
              stroke="#1a3a2a"
              angle={-45} textAnchor="end" height={50} />
            <YAxis tick={{ fill: "#6a9a7a", fontSize: 12, fontFamily: "monospace" }} stroke="#1a3a2a"
              domain={metric === "demo" ? [0, 0.6] : [0, shows.raw ? 6.0 : 2.0]}
              tickFormatter={(v) => metric === "demo" ? v.toFixed(2) : v.toFixed(1)} />
            <Tooltip content={<Tip metric={metric} />} />
            <ReferenceLine x={toTs("2025-09-26")} stroke="#F59E0B44" strokeDasharray="4 4"
              label={{ value: "Nielsen Change", fill: "#F59E0B88", fontSize: 12, fontFamily: "monospace", position: "top" }} />
            {NIELSEN_SHOWS.map((s) => shows[s.id] && (
              <Line key={s.id} type="monotone" dataKey={metric === "demo" ? s.id + "_demo" : s.id}
                name={s.name} stroke={s.color} strokeWidth={2} dot={false} connectNulls={false}
                activeDot={{ r: 4, fill: s.color }} />
            ))}
            {shows.raw && metric === "viewers" && (
              <Line type="monotone" dataKey="raw" name="Raw (Netflix*)" stroke="#DC2626"
                strokeWidth={2} strokeDasharray="6 3" dot={false} connectNulls={true}
                activeDot={{ r: 4, fill: "#DC2626" }} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </section>

      {/* === STREAMING CHART === */}
      <section style={{ padding: "8px 12px 12px", borderTop: "1px solid #1a3a2a" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, paddingLeft: 8 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#e8f5ee" }}>Streaming &amp; Digital Views</h2>
          <span style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", letterSpacing: "0.08em" }}>
            DIFFERENT METRICS: NOT COMPARABLE TO NIELSEN
          </span>
        </div>

        {/* Streaming toggles */}
        <div style={{ display: "flex", gap: 6, marginBottom: 8, paddingLeft: 8, flexWrap: "wrap" }}>
          {STREAMING_SHOWS.map((s) => (
            <button key={s.id} onClick={() => toggle(s.id)} style={showBtn(s, shows[s.id])}>
              <span style={dot(s.color, shows[s.id])} />{s.name}
              <span style={{ fontSize: 12, opacity: 0.5, marginLeft: 4 }}>({s.platform})</span>
            </button>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={fS} margin={{ top: 5, right: 20, left: 0, bottom: 30 }}>
            <CartesianGrid strokeDasharray="6 4" stroke="#1a3a2a" />
            <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]}
              ticks={streamingTicks}
              tickFormatter={(ts) => fmtLabel(ts, isWeekly)}
              tick={{ fill: "#6a9a7a", fontSize: 12, fontFamily: "monospace" }}
              stroke="#1a3a2a"
              angle={-45} textAnchor="end" height={50} />
            <YAxis tick={{ fill: "#6a9a7a", fontSize: 12, fontFamily: "monospace" }} stroke="#1a3a2a" domain={[0, 5]} tickFormatter={(v) => v.toFixed(1) + "M"} />
            <Tooltip content={<Tip metric="viewers" />} />
            {shows.raw && <Line type="monotone" dataKey="raw" name="Raw (Netflix)" stroke="#DC2626" strokeWidth={2} dot={false} connectNulls={false} activeDot={{ r: 4, fill: "#DC2626" }} />}
            {shows.roh && <Line type="monotone" dataKey="roh" name="ROH (YouTube)" stroke="#F97316" strokeWidth={2} dot={false} connectNulls={false} activeDot={{ r: 4, fill: "#F97316" }} />}
            {shows.nwa && <Line type="monotone" dataKey="nwa" name="NWA Powerrr (YT)" stroke="#06B6D4" strokeWidth={2} dot={false} connectNulls={false} activeDot={{ r: 4, fill: "#06B6D4" }} />}
          </LineChart>
        </ResponsiveContainer>

        {/* Data source notes */}
        <div style={{ marginTop: 8, padding: "10px 12px", background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, fontSize: 14, color: "#6a9a7a", fontFamily: "monospace", lineHeight: 1.7 }}>
          <span style={{ color: "#DC2626", fontWeight: 700 }}>WWE Raw:</span> Netflix global views (millions). Not a Nielsen metric.
          <br /><span style={{ color: "#F97316", fontWeight: 700 }}>ROH:</span> Airs on HonorClub (Thu) and YouTube (Fri). YouTube view counts tracked when available.
          <br /><span style={{ color: "#06B6D4", fontWeight: 700 }}>NWA Powerrr:</span> Moved to Roku Channel (Jul 2025). YouTube clips/episodes tracked when posted. No Roku viewership data is publicly reported.
          <br /><span style={{ color: "#F5C518", fontWeight: 700 }}>NIELSEN NOTE:</span> Nielsen switched to "Big Data + Panel" on Sep 26, 2025. Pre/post numbers are not directly comparable. Wrestling was disproportionately affected by the methodology change.
        </div>
      </section>

      {/* === SEO CONTENT SECTION === */}
      <article style={{ borderTop: "1px solid #1a3a2a", padding: "20px 20px 12px", background: "#0a1610" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 700, color: "#e8f5ee" }}>
          About Pro Wrestling TV Ratings
        </h2>
        <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7, maxWidth: 800 }}>
          <p style={{ margin: "0 0 10px" }}>
            This tracker provides weekly television ratings and viewership data for all major professional wrestling programs in the United States, including WWE SmackDown, WWE NXT, AEW Dynamite, AEW Collision, TNA iMPACT, WWE Raw on Netflix, Ring of Honor (ROH), and NWA Powerrr.
          </p>
          <p style={{ margin: "0 0 10px" }}>
            <strong style={{ color: "#8acca0" }}>Total Viewers</strong> represents the estimated number of people who watched the broadcast, reported in millions. <strong style={{ color: "#8acca0" }}>Key Demo (P18-49)</strong> is the rating among adults aged 18 to 49, which is considered the primary advertising currency for television programming.
          </p>
          <p style={{ margin: "0 0 10px" }}>
            In October 2025, Nielsen transitioned to a new "Big Data + Panel" measurement system that blends traditional panel data with viewing data from 45 million households. This change significantly impacted reported wrestling viewership numbers, with most shows seeing double-digit percentage declines under the new methodology. A subsequent adjustment in January 2026 partially reversed these declines for cable programming.
          </p>
          <p style={{ margin: "0 0 10px" }}>
            WWE Raw moved from the USA Network to Netflix in January 2025 and is now measured by Netflix's global views metric (total hours viewed divided by runtime) rather than traditional Nielsen TV ratings. Ring of Honor streams weekly on HonorClub and YouTube, while NWA Powerrr airs on The Roku Channel with clips available on YouTube.
          </p>
          <p style={{ margin: 0 }}>
            Data is sourced from publicly reported Nielsen ratings, Netflix weekly engagement reports, and YouTube public view counts. This site is updated weekly and is not affiliated with WWE, AEW, TNA, ROH, NWA, or Nielsen.
          </p>
        </div>

        {/* Show schedule grid */}
        <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 8 }}>
          {[
            { name: "WWE SmackDown", day: "Friday", net: "USA Network (SyFy overflow)", time: "8:00 PM ET" },
            { name: "WWE NXT", day: "Tuesday", net: "The CW", time: "8:00 PM ET" },
            { name: "AEW Dynamite", day: "Wednesday", net: "TBS", time: "8:00 PM ET" },
            { name: "AEW Collision", day: "Saturday", net: "TNT", time: "8:00 PM ET" },
            { name: "TNA iMPACT", day: "Thursday", net: "AMC", time: "8:00 PM ET" },
            { name: "WWE Raw", day: "Monday", net: "Netflix (Streaming)", time: "8:00 PM ET" },
            { name: "ROH Wrestling", day: "Thu/Fri", net: "HonorClub / YouTube", time: "7:00 PM ET" },
            { name: "NWA Powerrr", day: "Tuesday", net: "Roku Channel", time: "8:00 PM ET" },
          ].map((s, i) => (
            <div key={i} style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "8px 10px" }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#8acca0" }}>{s.name}</div>
              <div style={{ fontSize: 14, color: "#6a9a7a", marginTop: 2 }}>{s.day} &bull; {s.net} &bull; {s.time}</div>
            </div>
          ))}
        </div>
      </article>

      {/* === HOW THIS WEBSITE WORKS === */}
      <section style={{ borderTop: "1px solid #1a3a2a", padding: "20px 20px 16px", background: "#0a1610" }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700, color: "#e8f5ee" }}>
          How This Website Works
        </h2>

        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 12 }}>

          {/* Architecture */}
          <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 6, fontFamily: "monospace" }}>ARCHITECTURE</div>
            <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
              This is a full-stack single-page application built with a Python/Flask backend and a React frontend bundled with Vite. Flask serves both the REST API and the static production build as a single process. No database is needed. Ratings data is stored in a single JSON file that the scrapers update and the API serves directly.
            </div>
          </div>

          {/* Data Pipeline */}
          <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 6, fontFamily: "monospace" }}>LIVE DATA PIPELINE</div>
            <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
              Ratings update automatically through a multi-source data pipeline with built-in redundancy. Primary: WrestlingAttitude.com, parsed with BeautifulSoup. Backup: Wrestlenomics, with viewership data extracted directly from article URL slugs. Fallback: Wrestling Inc individual article scraping. Safety net: existing data is never overwritten with fewer entries. An APScheduler cron runs the full pipeline every 6 hours. The frontend polls the API every 10 minutes and re-renders when new data arrives. If two or more sources fail, a Slack alert is sent automatically.
            </div>
          </div>

          {/* Reconciliation */}
          <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 6, fontFamily: "monospace" }}>DATA RECONCILIATION</div>
            <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
              A reconciliation engine cross-references all three data sources for every show and date. If two out of three sources agree on a viewership number (within 5% tolerance), their average is used. If only one source has data for a given week, that value fills the gap. This provides both accuracy through consensus and coverage through redundancy.
            </div>
          </div>

          {/* Charts */}
          <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 6, fontFamily: "monospace" }}>CHART RENDERING</div>
            <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
              Charts are rendered with Recharts using a true time-scaled x-axis so that months are always proportionally spaced regardless of how many data points exist. All shows are grouped by week (normalized to Monday) regardless of their actual air day. The x-axis switches between weekly labels (1M/3M) and monthly labels (6M/1Y/ALL) based on the selected range.
            </div>
          </div>

          {/* Interaction */}
          <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 6, fontFamily: "monospace" }}>INTERACTION</div>
            <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
              The combined chart shows all shows on one view, including WWE Raw (Netflix) displayed as a dashed line with a disclaimer since Netflix global views are not directly comparable to Nielsen TV ratings. Toggle between Total Viewers and 18-49 Key Demo metrics, which switches the y-axis scale and data series. Five time range presets (1M, 3M, 6M, 1Y, ALL) filter the data window. Individual show lines can be toggled on and off. Hovering shows a tooltip with exact values for all visible shows on that date.
            </div>
          </div>

          {/* Deployment */}
          <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 6, fontFamily: "monospace" }}>DEPLOYMENT</div>
            <div style={{ fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
              The app is containerized in a multi-stage Docker build: Node 20 compiles the React frontend, then Python 3.11 serves it via Gunicorn. Deployed on Railway with automatic deploys from the main branch. Health checks hit /api/health. SEO is handled with a server-rendered HTML shell containing Open Graph meta tags, JSON-LD structured data, and a dynamic sitemap.xml. Live scrape status for each data source is displayed on the site with last scrape time, success/failure state, and entry counts.
            </div>
          </div>

        </div>

        {/* Tech stack badges */}
        <div style={{ marginTop: 14, display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          {["Python 3.11", "Flask", "Gunicorn", "APScheduler", "BeautifulSoup", "React 18", "Vite", "Recharts", "Docker", "Railway"].map((tech) => (
            <span key={tech} style={{
              fontSize: 13, fontWeight: 700, fontFamily: "monospace",
              padding: "2px 6px", borderRadius: 2,
              color: "#4ade80", background: "#4ade8044", border: "1px solid #4ade8025",
            }}>{tech}</span>
          ))}
        </div>

        {/* Open Source */}
        <div style={{ marginTop: 12, fontSize: 15, color: "#6a9a7a", lineHeight: 1.7 }}>
          <span style={{ fontWeight: 700, color: "#8acca0" }}>Open Source</span>
          {" "}The full source code is available at{" "}
          <a href="https://github.com/ToddWelch/wrestling-ratings" target="_blank" rel="noopener noreferrer"
            style={{ color: "#8acca0", textDecoration: "none", borderBottom: "1px dashed #8acca044" }}>
            github.com/ToddWelch/wrestling-ratings</a>.
        </div>
      </section>

      {/* === SCRAPE STATUS === */}
      {Object.keys(scrapeDetails).length > 0 && (
        <div style={{ borderTop: "1px solid #1a3a2a", padding: "14px 20px", background: "#0a1610" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#8acca0", marginBottom: 8, fontFamily: "monospace", letterSpacing: "0.08em" }}>DATA SOURCE STATUS</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 8 }}>
            {[
              { key: "wrestlingattitude", label: "WrestlingAttitude" },
              { key: "wrestlenomics", label: "Wrestlenomics" },
              { key: "wrestlinginc", label: "Wrestling Inc" },
              { key: "youtube", label: "YouTube API" },
            ].map(({ key, label }) => {
              const info = scrapeDetails[key];
              if (!info) return (
                <div key={key} style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 3, padding: "8px 10px" }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#6a9a7a" }}>{label}</div>
                  <div style={{ fontSize: 12, color: "#3e6e4e", fontFamily: "monospace", marginTop: 2 }}>No data yet</div>
                </div>
              );
              const ok = info.status === "success";
              const date = info.lastScrape ? new Date(info.lastScrape) : null;
              const ago = date ? fmtTimeAgo(date) : "never";
              return (
                <div key={key} style={{ background: "#0c1812", border: `1px solid ${ok ? "#1a3a2a" : "#5a2020"}`, borderRadius: 3, padding: "8px 10px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: ok ? "#8acca0" : "#EF4444" }}>{label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, fontFamily: "monospace", color: ok ? "#22C55E" : "#EF4444" }}>
                      {ok ? "OK" : "FAILED"}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", marginTop: 2 }}>
                    {ago}{info.entriesFound > 0 ? ` \u00B7 ${info.entriesFound} entries` : ""}
                  </div>
                  {info.error && <div style={{ fontSize: 12, color: "#EF4444", fontFamily: "monospace", marginTop: 2 }}>{info.error}</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* === DATA SOURCE FOOTER === */}
      <div style={{ borderTop: "1px solid #1a3a2a", padding: "12px 20px", display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8, background: "#0a1610" }}>
        <span style={{ fontSize: 13, color: "#6a9a7a", fontFamily: "monospace" }}>
          Data: wrestlingattitude.com &bull; Netflix &bull; YouTube API &bull; Updated weekly
        </span>
        <span style={{ fontSize: 13, color: "#6a9a7a", fontFamily: "monospace" }}>
          wrestlingratings.welchcommercesystems.com
        </span>
      </div>

      {/* BUILT BY */}
      <footer style={{ borderTop: "1px solid #1a3a2a", padding: "16px 20px", background: "#080e0a", textAlign: "center" }}>
        <p style={{ fontSize: 13, color: "#6a9a7a", lineHeight: 1.6, margin: 0 }}>
          This site was designed and built entirely by{" "}
          <a href="https://claude.ai/code" target="_blank" rel="noopener noreferrer"
            style={{ color: "#8acca0", textDecoration: "none", borderBottom: "1px dashed #8acca044" }}>Claude Code</a>
          {" "}(AI), prompted by{" "}
          <a href="https://welchcommercesystems.com" target="_blank" rel="noopener noreferrer"
            style={{ color: "#4ade80", textDecoration: "none", fontWeight: 700, borderBottom: "1px dashed #4ade8044" }}>Welch Commerce Systems</a>.
        </p>
        <p style={{ fontSize: 12, color: "#5a8a6a", marginTop: 6, marginBottom: 0 }}>
          Want an AI-built app like this for your business?{" "}
          <a href="https://welchcommercesystems.com" target="_blank" rel="noopener noreferrer"
            style={{ color: "#8acca0", textDecoration: "none", borderBottom: "1px solid #8acca066" }}>
            Let's talk AI assisted automation &amp; development
          </a>
        </p>
      </footer>
    </div>
  );
}
