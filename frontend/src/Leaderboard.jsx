import { MO, fmtDate } from "./shows.js";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function airDay(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return `${DAYS[d.getDay()]} ${MO[d.getMonth()]} ${d.getDate()}`;
}

const label = { fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", letterSpacing: "0.08em" };
// Fixed widths keep the number columns aligned down the list at phone widths
const rank = { width: 16, flexShrink: 0 };
const num = { fontFamily: "monospace", fontWeight: 700, textAlign: "right", width: 54, flexShrink: 0, fontSize: 13 };
const demoCol = { width: 40 };
const row = { display: "flex", gap: 8, alignItems: "center", padding: "7px 10px" };

/* Ranking of the Nielsen shows for the latest complete week (see buildLeaderboard) */
export default function Leaderboard({ board, metric }) {
  if (!board || !board.ranked.length) return null;
  const byDemo = metric === "demo";

  return (
    <section style={{ padding: "16px 12px 4px" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 8, paddingLeft: 8, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#e8f5ee" }}>Leaderboard</h2>
        <span style={label}>WEEK OF {fmtDate(board.week).toUpperCase()}</span>
        <span style={label}>&bull; RANKED BY {byDemo ? "18-49 KEY DEMO" : "TOTAL VIEWERS"}</span>
      </div>

      <div style={{ background: "#0c1812", border: "1px solid #1a3a2a", borderRadius: 6, maxWidth: 640 }}>
        <div style={{ ...row, padding: "6px 10px", borderBottom: "1px solid #1a3a2a", ...label }}>
          <span style={rank}>#</span>
          <span style={{ flex: 1, minWidth: 0 }}>SHOW</span>
          <span style={{ ...num, ...label, fontWeight: 400, letterSpacing: "0.02em" }}>VIEWERS</span>
          <span style={{ ...num, ...demoCol, ...label, fontWeight: 400, letterSpacing: "0.02em" }}>18-49</span>
        </div>
        {board.ranked.map((r, i) => (
          <div key={r.id} style={{ ...row, borderBottom: i < board.ranked.length - 1 ? "1px solid #13261b" : "none" }}>
            <span style={{ ...rank, fontFamily: "monospace", fontWeight: 800, color: i === 0 ? "#4ade80" : "#8acca0" }}>{i + 1}</span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 7, whiteSpace: "nowrap", minWidth: 0 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: r.color, flexShrink: 0 }} />
                <span style={{ color: "#e8f5ee", fontWeight: 700, fontSize: 15, overflow: "hidden", textOverflow: "ellipsis" }}>{r.name}</span>
              </span>
              <span style={{ display: "block", fontSize: 12, color: "#6a9a7a", fontFamily: "monospace", marginTop: 1 }}>
                {r.network} &bull; {airDay(r.date)}
              </span>
            </span>
            <span style={{ ...num, color: byDemo ? "#8acca0" : "#e8f5ee" }}>{r.viewers.toFixed(3)}M</span>
            <span style={{ ...num, ...demoCol, color: byDemo ? "#e8f5ee" : "#8acca0" }}>{r.demo != null ? r.demo.toFixed(2) : "n/a"}</span>
          </div>
        ))}
      </div>

      {board.netflix && (
        <div style={{ marginTop: 6, fontSize: 12, color: "#8acca0", fontFamily: "monospace", maxWidth: 640 }}>
          <span style={{ color: board.netflix.color, fontWeight: 700 }}>{board.netflix.name}</span>
          {" "}({airDay(board.netflix.date)}): {board.netflix.viewers.toFixed(1)}M Netflix global views. Not ranked: a different metric from Nielsen.
        </div>
      )}
    </section>
  );
}
