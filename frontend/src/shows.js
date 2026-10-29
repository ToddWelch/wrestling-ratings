/* ======= SHOW CONFIG ======= */
export const NIELSEN_SHOWS = [
  { id: "smackdown", name: "SmackDown", color: "#60A5FA", network: "USA/SyFy", day: "Fri" },
  { id: "nxt", name: "NXT", color: "#FACC15", network: "CW", day: "Tue" },
  { id: "dynamite", name: "Dynamite", color: "#EF4444", network: "TBS", day: "Wed" },
  { id: "collision", name: "Collision", color: "#F472B6", network: "TNT", day: "Sat" },
  { id: "tna", name: "TNA iMPACT", color: "#22C55E", network: "AMC", day: "Thu" },
];

export const RAW_SHOW = { id: "raw", name: "WWE Raw", color: "#DC2626", network: "Netflix", day: "Mon" };

export const STREAMING_SHOWS = [
  { id: "raw", name: "WWE Raw", color: "#DC2626", platform: "Netflix", metric: "Global Views (M)" },
  { id: "roh", name: "ROH", color: "#F97316", platform: "HonorClub/YT", metric: "YouTube Views (K)" },
];

/* ======= DATE HELPERS ======= */
export const MO = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmtDate(v) {
  const d = v instanceof Date ? v : typeof v === "number" ? new Date(v) : new Date(v + "T00:00:00");
  return `${MO[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

export function toTs(dateStr) {
  return new Date(dateStr + "T00:00:00").getTime();
}

// Get the Monday of the week for a given date string
export function weekOf(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon, ...
  const diff = day === 0 ? -6 : 1 - day; // shift to Monday
  d.setDate(d.getDate() + diff);
  return d.toISOString().split("T")[0];
}
