"""Build a self-contained HTML of the contest-linking graph.

    python -m arch_a.export_graph

Nodes are contests; an edge joins two contests that share >=1 team identity
(the cross-contest links that put every contest on one scale, strat sec 6). We
emit two keyings side by side -- the current roster/id keying and the same keying
with the contest year appended -- to show that year-keying severs the cross-year
links and fragments the single scale into per-year islands. Connected-component
counts are computed on the full graph (every shared team, weight >= 1); only
edges of weight >= 2 are embedded for a readable backbone.
"""

import itertools
import json
import os
from collections import Counter, defaultdict

from .load import _UnionFind, _roster_token, dedupe_contests

DATA_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "tagged.json")
OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
EDGE_MIN = 2  # embed only edges with at least this many shared teams (readability)


def _build_uf(raw, addyear):
    uf = _UnionFind()
    for c in raw:
        suff = ("@" + str(c.get("year"))) if addyear else ""
        for s in c["standings"]:
            tid = s["team_id"]
            stable = None if tid.startswith("$DEFAULT") else "id:" + tid + suff
            roster = _roster_token(s.get("members"))
            roster = (roster + suff) if roster else None
            if stable:
                uf.find(stable)
            if roster:
                uf.find(roster)
                if stable:
                    uf.union(stable, roster)
    return uf


def _key(c, s, uf, addyear):
    suff = ("@" + str(c.get("year"))) if addyear else ""
    roster = _roster_token(s.get("members"))
    if roster is not None:
        return uf.find(roster + suff)
    if s["team_id"].startswith("$DEFAULT"):
        return f"dj:{c['contest_id']}::{s['team_id']}" + suff
    return uf.find("id:" + s["team_id"] + suff)


def _scheme(raw, addyear):
    uf = _build_uf(raw, addyear)
    key_contests = defaultdict(set)
    for i, c in enumerate(raw):
        for s in c["standings"]:
            key_contests[_key(c, s, uf, addyear)].add(i)

    # weighted contest pair = number of shared team identities
    pair = Counter()
    for ks in key_contests.values():
        for a, b in itertools.combinations(sorted(ks), 2):
            pair[(a, b)] += 1

    # connected components over the FULL graph (every shared team)
    cuf = _UnionFind()
    for i in range(len(raw)):
        cuf.find(i)
    for (a, b) in pair:
        cuf.union(a, b)
    roots = {}
    comp_of = []
    for i in range(len(raw)):
        r = cuf.find(i)
        comp_of.append(roots.setdefault(r, len(roots)))
    sizes = Counter(comp_of)
    # relabel components largest-first for stable colours
    order = {c: rank for rank, (c, _) in enumerate(sizes.most_common())}
    comp_of = [order[c] for c in comp_of]

    edges = [[a, b, w] for (a, b), w in pair.items() if w >= EDGE_MIN]
    return {
        "components": len(sizes),
        "sizes": sorted(sizes.values(), reverse=True),
        "comp_of": comp_of,
        "edges": edges,
    }


def build_data():
    with open(DATA_PATH) as f:
        raw = json.load(f)
    raw = dedupe_contests(raw)
    nodes = [
        {
            "name": (c.get("contest_name") or str(c["contest_id"])),
            "year": str(c.get("year") or "?"),
        }
        for c in raw
    ]
    return {
        "edge_min": EDGE_MIN,
        "nodes": nodes,
        "schemes": {
            "A": {"label": "current keying (roster / id)", **_scheme(raw, False)},
            "B": {"label": "+ year appended to key", **_scheme(raw, True)},
        },
    }


def main():
    data = build_data()
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "contest_graph.html")
    with open(out_path, "w") as f:
        f.write(html)
    a, b = data["schemes"]["A"], data["schemes"]["B"]
    print(f"wrote {os.path.normpath(out_path)}  ({len(html)//1024} KB)")
    print(f"  current keying:  {a['components']} components, top sizes {a['sizes'][:5]}")
    print(f"  + year appended: {b['components']} components, top sizes {b['sizes'][:5]}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contest-linking graph</title>
<style>
  :root { --fg:#1b2330; --muted:#6b7785; --line:#e3e8ee; --bg:#f7f9fc; }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.45 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--fg); background:var(--bg); }
  header { padding:16px 22px; background:#fff; border-bottom:1px solid var(--line); }
  h1 { margin:0 0 4px; font-size:18px; }
  .sub { color:var(--muted); font-size:13px; max-width:880px; }
  .controls { display:flex; flex-wrap:wrap; gap:18px; align-items:center; margin-top:12px; }
  .controls label { font-size:13px; color:var(--muted); display:flex; gap:7px; align-items:center; }
  button { font:13px inherit; padding:6px 12px; border:1px solid var(--line); border-radius:6px;
           background:#fff; color:var(--fg); cursor:pointer; }
  button.on { background:#2b6cb0; color:#fff; border-color:#2b6cb0; }
  .meta { font-size:13px; color:var(--muted); }
  .meta b { color:var(--fg); }
  main { position:relative; }
  canvas { display:block; width:100vw; height:calc(100vh - 132px); }
  #legend { position:absolute; top:12px; right:16px; background:#ffffffe6; border:1px solid var(--line);
            border-radius:8px; padding:10px 12px; font-size:12px; }
  #legend div { display:flex; gap:7px; align-items:center; margin:2px 0; }
  .dot { width:11px; height:11px; border-radius:50%; }
  #tip { position:absolute; pointer-events:none; background:#1b2330; color:#fff; padding:5px 8px;
         border-radius:6px; font-size:12px; display:none; max-width:320px; }
</style>
</head>
<body>
<header>
  <h1>Contest-linking graph</h1>
  <div class="sub">Each node is a contest; an edge joins contests sharing &ge;2 team identities &mdash; the
    links that put every contest on one rating scale. Components are computed on <i>all</i> shared teams.
    Toggle the keying to see year-appended keys fragment the scale into per-year islands.</div>
  <div class="controls">
    <span>Keying:</span>
    <button id="btnA" class="on"></button>
    <button id="btnB"></button>
    <label>min shared teams <input id="thr" type="range" min="2" max="20" value="2">
      <span id="thrv">2</span></label>
    <span class="meta" id="meta"></span>
  </div>
</header>
<main>
  <canvas id="cv"></canvas>
  <div id="legend"></div>
  <div id="tip"></div>
</main>
<script>
const DATA = /*__DATA__*/null;
const YEARS = [...new Set(DATA.nodes.map(n=>n.year))].sort();
const YCOL = {}; YEARS.forEach((y,i)=>{ YCOL[y]=`hsl(${210-210*i/Math.max(1,YEARS.length-1)} 65% 50%)`; });

const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
const tip=document.getElementById('tip'), meta=document.getElementById('meta');
let scheme='A', thr=2, DPR=window.devicePixelRatio||1;
let nodes=[], edges=[], W=0, H=0;

function resize(){
  W=cv.clientWidth; H=cv.clientHeight;
  cv.width=W*DPR; cv.height=H*DPR; ctx.setTransform(DPR,0,0,DPR,0,0);
}
window.addEventListener('resize', ()=>{ resize(); });

function init(){
  const s=DATA.schemes[scheme];
  nodes=DATA.nodes.map((n,i)=>({...n, comp:s.comp_of[i],
    x:W/2+(Math.random()-.5)*W*0.6, y:H/2+(Math.random()-.5)*H*0.6, vx:0, vy:0}));
  edges=s.edges;
  document.getElementById('meta').innerHTML=
    `<b>${s.components}</b> components &middot; sizes <b>${s.sizes.slice(0,6).join(', ')}${s.sizes.length>6?'…':''}</b>`;
  legend();
  alpha=1;
}
function legend(){
  const L=document.getElementById('legend');
  L.innerHTML='<div style="font-weight:600;color:#1b2330;margin-bottom:4px">Year</div>'+
    YEARS.map(y=>`<div><span class="dot" style="background:${YCOL[y]}"></span>${y}</div>`).join('');
}

// force layout (velocity Verlet, cooling)
let alpha=1;
function step(){
  const k=alpha, REP=2200, SPRING=0.02, LEN=42, GRAV=0.015;
  for(const n of nodes){ n.fx=(W/2-n.x)*GRAV; n.fy=(H/2-n.y)*GRAV; }
  for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++){
    const a=nodes[i],b=nodes[j]; let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+0.01;
    const f=REP/d2, d=Math.sqrt(d2); dx/=d; dy/=d;
    a.fx+=dx*f; a.fy+=dy*f; b.fx-=dx*f; b.fy-=dy*f;
  }
  for(const e of edges){ if(e[2]<thr) continue;
    const a=nodes[e[0]],b=nodes[e[1]]; let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)+0.01;
    const f=SPRING*(d-LEN)*Math.min(1,e[2]/6); dx/=d; dy/=d;
    a.fx+=dx*f; a.fy+=dy*f; b.fx-=dx*f; b.fy-=dy*f;
  }
  for(const n of nodes){ if(n.drag) continue;
    n.vx=(n.vx+n.fx*k)*0.85; n.vy=(n.vy+n.fy*k)*0.85;
    n.x+=n.vx; n.y+=n.vy;
  }
  alpha*=0.992; if(alpha<0.03) alpha=0.03;
}
function draw(){
  ctx.clearRect(0,0,W,H);
  ctx.lineWidth=1;
  for(const e of edges){ if(e[2]<thr) continue;
    const a=nodes[e[0]],b=nodes[e[1]];
    ctx.strokeStyle=`rgba(120,130,145,${Math.min(.5,0.08+e[2]/40)})`;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }
  for(const n of nodes){
    ctx.beginPath(); ctx.arc(n.x,n.y,5,0,7); ctx.fillStyle=YCOL[n.year];
    ctx.fill(); ctx.strokeStyle='#fff'; ctx.lineWidth=1.2; ctx.stroke();
  }
}
function frame(){ step(); draw(); requestAnimationFrame(frame); }

// interaction
let hover=null;
cv.addEventListener('mousemove', ev=>{
  const r=cv.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
  if(drag){ drag.x=mx; drag.y=my; drag.vx=drag.vy=0; alpha=Math.max(alpha,0.3); }
  hover=null; for(const n of nodes){ if((n.x-mx)**2+(n.y-my)**2<36){ hover=n; break; } }
  if(hover){ tip.style.display='block'; tip.style.left=(ev.clientX+12)+'px'; tip.style.top=(ev.clientY+12)+'px';
    tip.innerHTML=`<b>${hover.name}</b><br>year ${hover.year} · component #${hover.comp+1}`; }
  else tip.style.display='none';
});
let drag=null;
cv.addEventListener('mousedown', ev=>{ if(hover){ drag=hover; drag.drag=true; } });
window.addEventListener('mouseup', ()=>{ if(drag){ drag.drag=false; drag=null; } });

document.getElementById('btnA').textContent=DATA.schemes.A.label;
document.getElementById('btnB').textContent=DATA.schemes.B.label;
function pick(s){ scheme=s;
  document.getElementById('btnA').classList.toggle('on',s==='A');
  document.getElementById('btnB').classList.toggle('on',s==='B'); init(); }
document.getElementById('btnA').onclick=()=>pick('A');
document.getElementById('btnB').onclick=()=>pick('B');
document.getElementById('thr').oninput=e=>{ thr=+e.target.value;
  document.getElementById('thrv').textContent=thr; alpha=Math.max(alpha,0.2); };

resize(); init(); frame();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
