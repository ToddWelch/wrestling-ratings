import { useState, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

/* ═══════════ SHOW CONFIG ═══════════ */
const NIELSEN_SHOWS = [
  { id: "smackdown", name: "SmackDown", color: "#3B82F6", network: "USA/SyFy", day: "Fri" },
  { id: "nxt", name: "NXT", color: "#F59E0B", network: "CW", day: "Tue" },
  { id: "dynamite", name: "Dynamite", color: "#EF4444", network: "TBS", day: "Wed" },
  { id: "collision", name: "Collision", color: "#EC4899", network: "TNT", day: "Sat" },
  { id: "tna", name: "TNA iMPACT", color: "#10B981", network: "AMC", day: "Thu" },
];

const STREAMING_SHOWS = [
  { id: "raw", name: "WWE Raw", color: "#8B5CF6", platform: "Netflix", metric: "Global Views (M)" },
  { id: "roh", name: "ROH", color: "#F97316", platform: "HonorClub/YT", metric: "YouTube Views (K)" },
  { id: "nwa", name: "NWA Powerrr", color: "#06B6D4", platform: "Roku/YT", metric: "YouTube Views (K)" },
];

/* ═══════════ SAMPLE DATA ═══════════ */
function dt(y,m,day){ return `${y}-${String(m).padStart(2,"0")}-${String(day).padStart(2,"0")}`; }

const NIELSEN_DATA = [
  {date:dt(2025,3,21),smackdown:1.459,nxt:0.672,dynamite:null,collision:null,tna:null,smackdown_demo:0.39,nxt_demo:0.15,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,3,28),smackdown:1.350,nxt:0.741,dynamite:null,collision:null,tna:null,smackdown_demo:0.40,nxt_demo:0.16,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,4,4),smackdown:1.578,nxt:0.650,dynamite:null,collision:null,tna:null,smackdown_demo:0.47,nxt_demo:0.15,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,4,18),smackdown:1.741,nxt:0.663,dynamite:null,collision:null,tna:null,smackdown_demo:0.55,nxt_demo:0.14,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,5,2),smackdown:1.406,nxt:0.674,dynamite:null,collision:null,tna:null,smackdown_demo:0.37,nxt_demo:0.15,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,5,16),smackdown:1.290,nxt:0.664,dynamite:null,collision:null,tna:null,smackdown_demo:0.36,nxt_demo:0.15,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,5,30),smackdown:1.383,nxt:0.650,dynamite:null,collision:null,tna:null,smackdown_demo:0.34,nxt_demo:0.14,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,6,13),smackdown:1.401,nxt:0.726,dynamite:null,collision:null,tna:null,smackdown_demo:0.38,nxt_demo:0.15,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,6,27),smackdown:1.450,nxt:0.729,dynamite:null,collision:null,tna:null,smackdown_demo:0.41,nxt_demo:0.16,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,7,11),smackdown:1.399,nxt:0.695,dynamite:null,collision:null,tna:null,smackdown_demo:0.37,nxt_demo:0.16,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,7,25),smackdown:1.707,nxt:0.747,dynamite:null,collision:null,tna:null,smackdown_demo:0.48,nxt_demo:0.16,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,8,8),smackdown:1.557,nxt:0.728,dynamite:null,collision:null,tna:null,smackdown_demo:0.48,nxt_demo:0.17,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,8,22),smackdown:1.258,nxt:0.616,dynamite:null,collision:null,tna:null,smackdown_demo:0.35,nxt_demo:0.12,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,9,5),smackdown:1.585,nxt:0.645,dynamite:null,collision:null,tna:null,smackdown_demo:0.51,nxt_demo:0.14,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,9,19),smackdown:1.342,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.37,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,10,3),smackdown:1.030,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.29,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,10,17),smackdown:1.180,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.28,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,10,31),smackdown:0.933,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.20,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,11,14),smackdown:1.158,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.27,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,11,28),smackdown:1.142,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.28,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,12,12),smackdown:1.240,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.26,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2025,12,26),smackdown:1.138,nxt:null,dynamite:null,collision:null,tna:null,smackdown_demo:0.27,nxt_demo:null,dynamite_demo:null,collision_demo:null,tna_demo:null},
  {date:dt(2026,1,2),smackdown:1.175,nxt:0.627,dynamite:0.516,collision:0.241,tna:null,smackdown_demo:0.28,nxt_demo:0.10,dynamite_demo:0.08,collision_demo:0.03,tna_demo:null},
  {date:dt(2026,1,9),smackdown:0.990,nxt:0.618,dynamite:0.526,collision:0.271,tna:null,smackdown_demo:0.26,nxt_demo:0.09,dynamite_demo:0.08,collision_demo:0.03,tna_demo:null},
  {date:dt(2026,1,16),smackdown:0.968,nxt:0.608,dynamite:0.498,collision:null,tna:0.173,smackdown_demo:0.21,nxt_demo:0.08,dynamite_demo:0.08,collision_demo:null,tna_demo:0.04},
  {date:dt(2026,1,23),smackdown:0.943,nxt:0.674,dynamite:0.653,collision:0.253,tna:0.171,smackdown_demo:0.22,nxt_demo:0.08,dynamite_demo:0.09,collision_demo:0.02,tna_demo:0.03},
  {date:dt(2026,1,30),smackdown:1.260,nxt:0.629,dynamite:0.654,collision:0.492,tna:0.201,smackdown_demo:0.29,nxt_demo:0.08,dynamite_demo:0.15,collision_demo:0.07,tna_demo:0.04},
  {date:dt(2026,2,6),smackdown:1.459,nxt:0.637,dynamite:0.604,collision:0.388,tna:0.241,smackdown_demo:0.35,nxt_demo:0.12,dynamite_demo:0.12,collision_demo:0.07,tna_demo:0.05},
  {date:dt(2026,2,13),smackdown:1.042,nxt:0.744,dynamite:0.692,collision:0.561,tna:0.254,smackdown_demo:0.26,nxt_demo:0.09,dynamite_demo:0.12,collision_demo:0.10,tna_demo:0.05},
  {date:dt(2026,2,20),smackdown:1.100,nxt:0.589,dynamite:0.633,collision:0.470,tna:0.233,smackdown_demo:0.29,nxt_demo:0.08,dynamite_demo:0.10,collision_demo:0.07,tna_demo:0.05},
  {date:dt(2026,2,27),smackdown:1.379,nxt:0.604,dynamite:0.650,collision:0.365,tna:0.233,smackdown_demo:0.34,nxt_demo:0.09,dynamite_demo:0.12,collision_demo:0.06,tna_demo:0.03},
  {date:dt(2026,3,6),smackdown:1.190,nxt:0.541,dynamite:0.619,collision:0.370,tna:0.249,smackdown_demo:0.27,nxt_demo:0.08,dynamite_demo:0.09,collision_demo:0.05,tna_demo:0.04},
  {date:dt(2026,3,13),smackdown:1.419,nxt:0.588,dynamite:null,collision:0.458,tna:0.259,smackdown_demo:0.32,nxt_demo:0.07,dynamite_demo:null,collision_demo:0.07,tna_demo:0.04},
];

const STREAMING_DATA = [
  {date:dt(2025,3,17),raw:3.1,roh:null,nwa:null},{date:dt(2025,4,7),raw:2.8,roh:null,nwa:null},
  {date:dt(2025,4,21),raw:3.6,roh:null,nwa:null},{date:dt(2025,5,5),raw:2.8,roh:null,nwa:null},
  {date:dt(2025,5,19),raw:2.7,roh:null,nwa:null},{date:dt(2025,6,2),raw:2.7,roh:null,nwa:null},
  {date:dt(2025,6,16),raw:2.7,roh:null,nwa:null},{date:dt(2025,6,30),raw:2.5,roh:null,nwa:null},
  {date:dt(2025,7,14),raw:2.7,roh:null,nwa:null},{date:dt(2025,7,28),raw:2.7,roh:null,nwa:null},
  {date:dt(2025,8,11),raw:2.8,roh:null,nwa:null},{date:dt(2025,8,25),raw:2.6,roh:null,nwa:null},
  {date:dt(2025,9,8),raw:2.6,roh:null,nwa:null},{date:dt(2025,9,22),raw:2.3,roh:null,nwa:null},
  {date:dt(2025,10,6),raw:2.4,roh:null,nwa:null},{date:dt(2025,10,20),raw:2.6,roh:null,nwa:null},
  {date:dt(2025,11,3),raw:2.4,roh:null,nwa:null},{date:dt(2025,11,17),raw:3.1,roh:null,nwa:null},
  {date:dt(2025,11,24),raw:3.9,roh:null,nwa:null},{date:dt(2025,12,8),raw:2.5,roh:null,nwa:null},
  {date:dt(2025,12,22),raw:3.2,roh:null,nwa:null},{date:dt(2026,1,5),raw:3.2,roh:null,nwa:null},
  {date:dt(2026,1,19),raw:2.5,roh:null,nwa:null},{date:dt(2026,2,2),raw:3.1,roh:null,nwa:null},
  {date:dt(2026,2,9),raw:2.9,roh:null,nwa:null},{date:dt(2026,2,16),raw:2.7,roh:null,nwa:null},
  {date:dt(2026,2,23),raw:2.8,roh:null,nwa:null},{date:dt(2026,3,2),raw:3.0,roh:null,nwa:null},
];

/* ═══════════ HELPERS ═══════════ */
const MO=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function fmtDate(s){const d=new Date(s+"T00:00:00");return`${MO[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;}
function fmtShort(s){const d=new Date(s+"T00:00:00");return`${MO[d.getMonth()]} '${String(d.getFullYear()).slice(2)}`;}

const RANGES=[{id:"3m",label:"3M",days:90},{id:"6m",label:"6M",days:180},{id:"1y",label:"1Y",days:365},{id:"all",label:"ALL",days:9999}];

function filterRange(data,range){
  if(range==="all")return data;
  const days=RANGES.find(r=>r.id===range)?.days||365;
  const cut=new Date();cut.setDate(cut.getDate()-days);
  const cs=cut.toISOString().split("T")[0];
  return data.filter(d=>d.date>=cs);
}

/* ═══════════ TOOLTIP ═══════════ */
function Tip({active,payload,label,metric}){
  if(!active||!payload?.length)return null;
  return(
    <div style={{background:"#111a14",border:"1px solid #2a4a3a",borderRadius:6,padding:"8px 12px",fontSize:11,fontFamily:"monospace"}}>
      <div style={{color:"#6aaa8a",marginBottom:4,fontWeight:700}}>{fmtDate(label)}</div>
      {payload.filter(p=>p.value!=null).map((p,i)=>(
        <div key={i} style={{display:"flex",alignItems:"center",gap:6,padding:"1px 0"}}>
          <span style={{width:8,height:8,borderRadius:"50%",background:p.color,flexShrink:0}}/>
          <span style={{color:"#8aaa9a",flex:1}}>{p.name}</span>
          <span style={{color:"#e8f5ee",fontWeight:700}}>
            {metric==="demo"?p.value.toFixed(2):p.value.toFixed(3)+"M"}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ═══════════ MAIN ═══════════ */
export default function App(){
  const [metric,setMetric]=useState("viewers");
  const [range,setRange]=useState("1y");
  const [shows,setShows]=useState(
    Object.fromEntries([...NIELSEN_SHOWS,...STREAMING_SHOWS].map(s=>[s.id,true]))
  );
  const toggle=(id)=>setShows(p=>({...p,[id]:!p[id]}));

  const fN=useMemo(()=>filterRange(NIELSEN_DATA,range),[range]);
  const fS=useMemo(()=>filterRange(STREAMING_DATA,range),[range]);

  const btn=(on)=>({
    background:on?"#4ade8018":"transparent",border:on?"1px solid #4ade8040":"1px solid #1e3e2e",
    borderRadius:4,padding:"4px 10px",cursor:"pointer",color:on?"#4ade80":"#3e6e4e",
    fontSize:10,fontWeight:700,fontFamily:"monospace",transition:"all 0.15s",
  });

  const showBtn=(s,on)=>({
    background:on?`${s.color}18`:"transparent",border:`1px solid ${on?s.color+"60":"#1e3e2e"}`,
    borderRadius:4,padding:"3px 8px",cursor:"pointer",color:on?s.color:"#2e4e3e",
    fontSize:9,fontWeight:700,fontFamily:"monospace",opacity:on?1:0.5,transition:"all 0.15s",
  });

  const dot=(color,on)=>({
    display:"inline-block",width:6,height:6,borderRadius:"50%",
    background:on?color:"#2e4e3e",marginRight:4,verticalAlign:"middle",
  });

  return(
    <div style={{background:"#070f0b",minHeight:"100vh",color:"#c0d8cc",fontFamily:"'Segoe UI',system-ui,sans-serif"}}>

      {/* ═══ HEADER ═══ */}
      <div style={{borderBottom:"1px solid #1a3a2a",padding:"16px 20px 14px",background:"linear-gradient(180deg,#0e2118,#070f0b)"}}>
        <h1 style={{margin:0,fontSize:22,fontWeight:800,color:"#e8f5ee",letterSpacing:"-0.02em"}}>
          <span style={{color:"#4ade80"}}>Pro Wrestling</span> TV Ratings Tracker
        </h1>
        <p style={{margin:"4px 0 0",fontSize:10,color:"#3e6e4e",fontFamily:"monospace",letterSpacing:"0.08em"}}>
          WEEKLY VIEWERSHIP FOR WWE, AEW, TNA, ROH, AND NWA &bull; UPDATED EVERY WEEK &bull; NIELSEN + STREAMING
        </p>

        {/* Metric + Range */}
        <div style={{display:"flex",gap:16,marginTop:12,flexWrap:"wrap",alignItems:"center"}}>
          <div style={{display:"flex",gap:4,alignItems:"center"}}>
            <span style={{fontSize:8,color:"#3e6e4e",fontFamily:"monospace",marginRight:4}}>METRIC</span>
            <button onClick={()=>setMetric("viewers")} style={btn(metric==="viewers")}>VIEWERS</button>
            <button onClick={()=>setMetric("demo")} style={btn(metric==="demo")}>KEY DEMO 18-49</button>
          </div>
          <div style={{display:"flex",gap:4,alignItems:"center"}}>
            <span style={{fontSize:8,color:"#3e6e4e",fontFamily:"monospace",marginRight:4}}>RANGE</span>
            {RANGES.map(r=><button key={r.id} onClick={()=>setRange(r.id)} style={btn(range===r.id)}>{r.label}</button>)}
          </div>
        </div>

        {/* Nielsen show toggles */}
        <div style={{display:"flex",gap:6,marginTop:10,flexWrap:"wrap"}}>
          <span style={{fontSize:8,color:"#3e6e4e",fontFamily:"monospace",marginRight:4,alignSelf:"center"}}>TV</span>
          {NIELSEN_SHOWS.map(s=>(
            <button key={s.id} onClick={()=>toggle(s.id)} style={showBtn(s,shows[s.id])}>
              <span style={dot(s.color,shows[s.id])}/>{s.name}
              <span style={{fontSize:7,opacity:0.5,marginLeft:3}}>({s.network})</span>
            </button>
          ))}
        </div>
      </div>

      {/* ═══ NIELSEN CHART ═══ */}
      <div style={{padding:"16px 12px 8px"}}>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8,paddingLeft:8}}>
          <h2 style={{margin:0,fontSize:14,fontWeight:700,color:"#e8f5ee"}}>Nielsen TV Ratings</h2>
          <span style={{fontSize:8,color:"#3e6e4e",fontFamily:"monospace"}}>
            {metric==="viewers"?"TOTAL VIEWERS (MILLIONS)":"18-49 KEY DEMO RATING"}
          </span>
        </div>
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={fN} margin={{top:5,right:20,left:0,bottom:5}}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2a20"/>
            <XAxis dataKey="date" tickFormatter={fmtShort} tick={{fill:"#3e6e4e",fontSize:9,fontFamily:"monospace"}} stroke="#1a3a2a" interval="preserveStartEnd"/>
            <YAxis tick={{fill:"#3e6e4e",fontSize:9,fontFamily:"monospace"}} stroke="#1a3a2a"
              domain={metric==="demo"?[0,0.6]:[0,2.0]}
              tickFormatter={v=>metric==="demo"?v.toFixed(2):v.toFixed(1)}/>
            <Tooltip content={<Tip metric={metric}/>}/>
            <ReferenceLine x="2025-09-26" stroke="#F59E0B44" strokeDasharray="4 4" label={{value:"Nielsen Change",fill:"#F59E0B55",fontSize:8,fontFamily:"monospace",position:"top"}}/>
            {NIELSEN_SHOWS.map(s=>shows[s.id]&&(
              <Line key={s.id} type="monotone" dataKey={metric==="demo"?s.id+"_demo":s.id}
                name={s.name} stroke={s.color} strokeWidth={2} dot={false} connectNulls={false}
                activeDot={{r:4,fill:s.color}}/>
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ═══ STREAMING CHART ═══ */}
      <div style={{padding:"8px 12px 12px",borderTop:"1px solid #1a3a2a10"}}>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8,paddingLeft:8}}>
          <h2 style={{margin:0,fontSize:14,fontWeight:700,color:"#e8f5ee"}}>Streaming &amp; Digital Views</h2>
          <span style={{fontSize:8,color:"#3e6e4e",fontFamily:"monospace"}}>
            DIFFERENT METRICS: NOT COMPARABLE TO NIELSEN
          </span>
        </div>

        {/* Streaming toggles */}
        <div style={{display:"flex",gap:6,marginBottom:8,paddingLeft:8,flexWrap:"wrap"}}>
          {STREAMING_SHOWS.map(s=>(
            <button key={s.id} onClick={()=>toggle(s.id)} style={showBtn(s,shows[s.id])}>
              <span style={dot(s.color,shows[s.id])}/>{s.name}
              <span style={{fontSize:7,opacity:0.5,marginLeft:3}}>({s.platform})</span>
            </button>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={fS} margin={{top:5,right:20,left:0,bottom:5}}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2a20"/>
            <XAxis dataKey="date" tickFormatter={fmtShort} tick={{fill:"#3e6e4e",fontSize:9,fontFamily:"monospace"}} stroke="#1a3a2a" interval="preserveStartEnd"/>
            <YAxis tick={{fill:"#3e6e4e",fontSize:9,fontFamily:"monospace"}} stroke="#1a3a2a" domain={[0,5]} tickFormatter={v=>v.toFixed(1)+"M"}/>
            <Tooltip content={<Tip metric="viewers"/>}/>
            {shows.raw&&<Line type="monotone" dataKey="raw" name="Raw (Netflix)" stroke="#8B5CF6" strokeWidth={2} dot={false} connectNulls={false} activeDot={{r:4,fill:"#8B5CF6"}}/>}
            {shows.roh&&<Line type="monotone" dataKey="roh" name="ROH (YouTube)" stroke="#F97316" strokeWidth={2} dot={false} connectNulls={false} activeDot={{r:4,fill:"#F97316"}}/>}
            {shows.nwa&&<Line type="monotone" dataKey="nwa" name="NWA Powerrr (YT)" stroke="#06B6D4" strokeWidth={2} dot={false} connectNulls={false} activeDot={{r:4,fill:"#06B6D4"}}/>}
          </LineChart>
        </ResponsiveContainer>

        {/* Data source notes */}
        <div style={{marginTop:8,padding:"10px 12px",background:"#0c1812",border:"1px solid #1a3a2a",borderRadius:4,fontSize:9,color:"#4a7a5a",fontFamily:"monospace",lineHeight:1.6}}>
          <span style={{color:"#8B5CF6",fontWeight:700}}>WWE Raw:</span> Netflix global views (millions). Not a Nielsen metric.
          <br/><span style={{color:"#F97316",fontWeight:700}}>ROH:</span> Airs on HonorClub (Thu) and YouTube (Fri). YouTube view counts tracked when available.
          <br/><span style={{color:"#06B6D4",fontWeight:700}}>NWA Powerrr:</span> Moved to Roku Channel (Jul 2025). YouTube clips/episodes tracked when posted. No Roku viewership data is publicly reported.
          <br/><span style={{color:"#F59E0B",fontWeight:700}}>NIELSEN NOTE:</span> Nielsen switched to "Big Data + Panel" on Sep 26, 2025. Pre/post numbers are not directly comparable. Wrestling was disproportionately affected by the methodology change.
        </div>
      </div>

      {/* ═══ SEO CONTENT SECTION ═══ */}
      <div style={{borderTop:"1px solid #1a3a2a",padding:"20px 20px 12px",background:"#0a1610"}}>
        <h2 style={{margin:"0 0 8px",fontSize:15,fontWeight:700,color:"#c0d8cc"}}>
          About Pro Wrestling TV Ratings
        </h2>
        <div style={{fontSize:11,color:"#5a8a6a",lineHeight:1.7,maxWidth:800}}>
          <p style={{margin:"0 0 10px"}}>
            This tracker provides weekly television ratings and viewership data for all major professional wrestling programs in the United States, including WWE SmackDown, WWE NXT, AEW Dynamite, AEW Collision, TNA iMPACT, WWE Raw on Netflix, Ring of Honor (ROH), and NWA Powerrr.
          </p>
          <p style={{margin:"0 0 10px"}}>
            <strong style={{color:"#7aaa8a"}}>Total Viewers</strong> represents the estimated number of people who watched the broadcast, reported in millions. <strong style={{color:"#7aaa8a"}}>Key Demo (P18-49)</strong> is the rating among adults aged 18 to 49, which is considered the primary advertising currency for television programming.
          </p>
          <p style={{margin:"0 0 10px"}}>
            In October 2025, Nielsen transitioned to a new "Big Data + Panel" measurement system that blends traditional panel data with viewing data from 45 million households. This change significantly impacted reported wrestling viewership numbers, with most shows seeing double-digit percentage declines under the new methodology. A subsequent adjustment in January 2026 partially reversed these declines for cable programming.
          </p>
          <p style={{margin:"0 0 10px"}}>
            WWE Raw moved from the USA Network to Netflix in January 2025 and is now measured by Netflix's global views metric (total hours viewed divided by runtime) rather than traditional Nielsen TV ratings. Ring of Honor streams weekly on HonorClub and YouTube, while NWA Powerrr airs on The Roku Channel with clips available on YouTube.
          </p>
          <p style={{margin:0}}>
            Data is sourced from publicly reported Nielsen ratings, Netflix weekly engagement reports, and YouTube public view counts. This site is updated weekly and is not affiliated with WWE, AEW, TNA, ROH, NWA, or Nielsen.
          </p>
        </div>

        {/* Keyword-rich show schedule reference */}
        <div style={{marginTop:16,display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))",gap:8}}>
          {[
            {name:"WWE SmackDown",day:"Friday",net:"USA Network (SyFy overflow)",time:"8:00 PM ET"},
            {name:"WWE NXT",day:"Tuesday",net:"The CW",time:"8:00 PM ET"},
            {name:"AEW Dynamite",day:"Wednesday",net:"TBS",time:"8:00 PM ET"},
            {name:"AEW Collision",day:"Saturday",net:"TNT",time:"8:00 PM ET"},
            {name:"TNA iMPACT",day:"Thursday",net:"AMC",time:"8:00 PM ET"},
            {name:"WWE Raw",day:"Monday",net:"Netflix (Streaming)",time:"8:00 PM ET"},
            {name:"ROH Wrestling",day:"Thu/Fri",net:"HonorClub / YouTube",time:"7:00 PM ET"},
            {name:"NWA Powerrr",day:"Tuesday",net:"Roku Channel",time:"8:00 PM ET"},
          ].map((s,i)=>(
            <div key={i} style={{background:"#0c1812",border:"1px solid #162a20",borderRadius:4,padding:"8px 10px"}}>
              <div style={{fontSize:10,fontWeight:700,color:"#8aaa9a"}}>{s.name}</div>
              <div style={{fontSize:9,color:"#4a7a5a",marginTop:2}}>{s.day} &bull; {s.net} &bull; {s.time}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ═══ FOOTER ═══ */}
      <div style={{borderTop:"1px solid #1a3a2a",padding:"10px 20px",display:"flex",justifyContent:"space-between",flexWrap:"wrap",gap:8,background:"#070f0b"}}>
        <span style={{fontSize:8,color:"#2e5e3e",fontFamily:"monospace"}}>
          Data: wrestlingattitude.com &bull; Netflix &bull; YouTube API &bull; Updated weekly
        </span>
        <span style={{fontSize:8,color:"#1e3e2e",fontFamily:"monospace"}}>
          wrestlingratings.welchproductsllc.com
        </span>
      </div>
    </div>
  );
}
