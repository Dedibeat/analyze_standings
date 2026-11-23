# How far the 2026 Hong Kong EC-Final seats reach

As of November 23, the tenth seat reaches **29th in the 112-team Reviewed field** or **30th if all 126 attend** in the full-registration simulation. The middle 80% of simulated cutoffs are 24th–34th and 25th–35th. A 10% first-round vacancy assumption brings both medians to 23rd. These calculations use the current season for the cutoff, the five finished mainland sites, and the November 22 HK roster. No historical HK cutoff enters the calculation.

## What determines the cutoff

Mainland awards 230 competition seats across seven regional sites, walking the boards by rank and then by number of official solving teams. Repeated teams are skipped and each school can earn three competition seats. For the replay, a shared member at one school identifies a repeated lineup, consistent with the tracker and the repository's prior replay. The final mainland notice calls it the same team. Hong Kong then walks official medalists until ten eligible teams have been found. A team sharing even one member with a completed first-round registration is skipped. School capacity is three minus first-round registrations, or four minus registrations for a rewarded school. An HK invitation declined after selection does not roll down. [Official season allocation, pp. 1–3](https://icpc.pku.edu.cn/docs/2026-09/a49a6af14b9542fd8f7eccd9a22a0779.pdf)

The five available boards include Xi’an, Chengdu, Wuhan, Nanjing and Shenyang. Across every subset and site order implied by valid field sizes, at depth 78 the first through fifth sites add an average 76.2, 46.0, 33.8, 26.8 and 21.2 distinct seats after caps. Extending the last marginal-yield ratio two more sites first reaches 230 at tier 78 (234 projected at 78). A check extrapolating from the first three to five projects 199 seats at that depth versus the 204 actually produced. Holding the latest marginal gain flat gives a shallower estimate, roughly 74th. Ignoring both unfinished sites would extend the mainland cutoff to 90th. Different geographic fields and overlap at the remaining two sites can change the result. [Versioned 2026 standings and rosters](https://github.com/JunjieCharles/xcpc-sight/blob/202f1ff7353ba6f85e695374ebd80c717d112f8b/static/data/qualification/2026-2027.json)

At tier 78 the five actual boards already generate 204 places. Among 112 Reviewed HK entrants, 29 belong to schools at three competition seats and eight have a member overlap, with five in both groups: 32 distinct provisional skips. For the 126-team scenario the corresponding figures are 30, nine and five, or 34 provisional skips. These are awards under the replay. The future registration list determines the actual skips.

To model Shanghai and Nanchang, withhold every pair of completed sites in turn. Use the observed distribution of school seat gains conditional on earlier school seats. Estimate additional member overlaps from the remaining uncapped rosters at comparable strength. This borrows the two-site patterns of 2026 and does not assume the unpublished results are known. Sample 10,000 HK standings per scenario, place NUM-R³ at Shenyang form (2327), and apply the eligibility walk in each standing. The 105 measured entrant means come from the [current team-strength table](https://github.com/Dedibeat/analyze_standings/blob/78ad57f272dd304829c096e0dad5e48abb4f8e50/output/hk_shenyang_rank.md). Missing strengths use their qualifier ranks or the [team and university audit](2026-11-23-hk-opponent-replay.md), converted using the two official qualifier boards. This explains the modest difference from the earlier simulation that drew missing strengths randomly. The medal cap uses the approximate 60% line; the ten seats filled within it in every draw. All probabilities condition on NUM-R³ attending and still being eligible.

| Registration assumptions | Tenth place, Reviewed / all | NUM seat chance, Reviewed / all |
|---|---|---|
| Five finished-site skips alone at tier 78 | 24 / 25 | 49% / 48% |
| Seven sites, competition seats taken, reward slots filled by other teams | 29 / 30 | 61% / 59% |
| Seven sites, 10% of projected school seats remain unfilled | 23 / 23 | 46% / 44% |
| Seven sites, 20% remain unfilled | 19 / 19 | 35% / 34% |
| Full competition-seat uptake, identified host/WF reward schools all retain an unused fourth slot | 20 / 21 | 39% / 39% |

The percentage vacancy scenarios describe unfilled seats after any substitutions. No measured uptake rate is available. Reward slots used by other teams leave the ordinary three competition-seat capacity unchanged. A reward given to an HK lineup could create another member skip. The identities of reward or incentive recipients, substitutions, and final signups are unresolved. The reward sensitivity covers the eight hosts and the repository’s mapped WF schools; setter schools are not fully identified. The probability ranges across assumptions carry more decision value than simulation rounding. Varying the mainland tier from 70 to 82 changes the Reviewed central estimate by one place.

## Difficulty relative to the mainland

| Site | Approx. gold rank | Performance near gold | Rank near mainland qualification | Performance there |
|---|---:|---:|---:|---:|
| Shenyang | 41 | 2551 | 78 | 2359 |
| Xi’an | 41 | 2567 | 78 | 2429 |
| Wuhan | 37 | 2581 | 78 | 2350 |
| Nanjing | 34 | 2603 | 78 | 2335 |
| Chengdu | 32 | 2612 | 78 | 2338 |
| HK Reviewed, simulated | 11 | 2577 | 29 | 2282 |
| HK Reviewed + Pending, simulated | 13 | 2543 | 30 | 2291 |

Mainland gold comparisons use approximately the top tenth of official rows (rounded upward), and the median shipped performance of teams within two places of each line. All five nearby rows were matched at all ten mainland thresholds. The mainland seat comparison is a tier reached in a round-robin walk: an individual team at that rank still has to clear its team/school checks. HK figures are simulated median day performances at the marginal places under full registration. If 10% of first-round places remain vacant, the HK seat line is about 2361–2367, comparable to most mainland sites. At Shenyang form, estimated HK gold is 13% Reviewed or 17% with everybody attending. In the full-registration Reviewed case, conditional on NUM finishing within one place of 20th/25th/30th/35th, the estimated seat chances are about 100%/94%/53%/10%. Aiming at 20th–25th offers more protection than relying on 30th.

## Reproduce

From the repository root, fetch the pinned team-strength commit if missing and download the pinned snapshot. The Python checks its SHA-256. Save the block below as a Python file and run it with the repository on PYTHONPATH and the downloaded JSON path as its only argument, using the project environment.

```powershell
git fetch origin claude/peaceful-brahmagupta-ix7p5m
$board = Join-Path $env:TEMP 'static-data-qualification-2026-2027.json'
Invoke-WebRequest 'https://raw.githubusercontent.com/JunjieCharles/xcpc-sight/202f1ff7353ba6f85e695374ebd80c717d112f8b/static/data/qualification/2026-2027.json' -OutFile $board
$env:PYTHONPATH = (Get-Location).Path
$env:PYTHONUTF8 = '1'
```

```python
"""Run from the repository root, passing the November 16 five-site JSON."""
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import numpy as np
from arch_b.online_gold import norm_name, norm_school

def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))

import hashlib
source = Path(sys.argv[1])
assert hashlib.sha256(source.read_bytes()).hexdigest() == "1843c425c91dc0ac06d9a9874c62e1e76a2a11f2b8b0450f390011741f258411"
raw = read(source)
field = read("output/hk_field_2026.json")
teams = field["teams"] + field["unlinked"]
me = next(i for i,t in enumerate(teams) if t["team"] == "NUM-R^3")
def person(name):
    return norm_name(" ".join(sorted(name.lower().split())))
aliases = {norm_school(t["school_en"]):norm_school(t["school"]) for t in teams}
def school(s):
    return aliases.get(norm_school(s), norm_school(s))

stations = sorted((s for s in raw["stations"] if s["status"]=="finished"),key=lambda s:-s["effectiveCount"])
all_sites = tuple(range(len(stations)))
schools = [school(t["school"]) for t in teams]
sid = np.unique(schools,return_inverse=True)[1]
members = [set(map(person,t["members"].split("/"))) for t in teams]
boards = [[(school(r["school"]),frozenset(map(person,r["members"])),norm_name(r["name"])) for r in s["teams"] if r["solved"]] for s in stations]

@lru_cache(None)
def allocation(sites,depth):
    seats=Counter()
    used=defaultdict(set)
    names=defaultdict(set)
    for k in range(depth):
        for j in sites:
            sc, ms, name=boards[j][k]
            if seats[sc]>=3 or ms & used[sc] or (not ms and name in names[sc]):
                continue
            seats[sc]+=1
            used[sc].update(ms)
            names[sc].add(name)
    caps=np.array([seats[sc] for sc in schools])
    dup=np.array([bool(used[sc] & ms) for sc,ms in zip(schools,members)])
    return sum(seats.values()),caps,dup

# For each pair of held-out 2026 sites, add their measured net seat yield to the five sites.
subsets=list(combinations(all_sites,3))
def reach(sites,prior):
    return next(k for k in range(25,130) if 2*allocation(sites,k)[0]-allocation(prior,k)[0]>=230)
depths=[reach(all_sites,sub) for sub in subsets]
def diminishing_yield(k, n):
    means=[0]+[np.mean([allocation(s,k)[0] for s in combinations(all_sites,j)]) for j in range(1,n+1)]
    additions=np.diff(means)
    ratio=additions[-1]/additions[-2]
    return means[-1]+additions[-1]*(ratio+ratio**2)

depth=next(k for k in range(45,95) if diminishing_yield(k,5)>=230)
print("diminishing projection",depth,diminishing_yield(depth,5),"five-site hindcast",diminishing_yield(depth,3),allocation(all_sites,depth)[0])
print("last additions at depth",np.diff([0]+[np.mean([allocation(s,depth)[0] for s in combinations(all_sites,j)]) for j in range(1,6)]))
print("Fixed-increment alternative depths",depths)
print("current only 230",next(k for k in range(25,130) if allocation(all_sites,k)[0]>=230))
# Check extrapolation by forecasting the known five-site seat yield from three sites at the same depth.
errors=[]
for sub in subsets:
    estimates=[2*allocation(sub,depth)[0]-allocation((j,),depth)[0] for j in sub]
    errors.append(np.median(estimates)-allocation(all_sites,depth)[0])
print("five-site hindcast error in seats",np.median(errors),min(errors),max(errors))
# A second projection extrapolates the most recent site's marginal contribution twice.
late=[next(k for k in range(25,130) if 3*allocation(all_sites,k)[0]-2*allocation(sub,k)[0]>=230)
      for sub in combinations(all_sites,4)]
print("four-to-five marginal depth",late)

rev="78ad57f272dd304829c096e0dad5e48abb4f8e50"
doc=subprocess.check_output(["git","show",rev+":output/hk_shenyang_rank.md"]).decode()
rows=[l.strip("| ").split(" | ") for l in doc.split("## Registrants by strength",1)[1].split("\n## ")[0].splitlines()
      if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
rated={(r[1],r[2]):(int(r[5]), len(r[7].split("; "))) for r in rows}
html=Path("output/virtual_calc.html").read_text(encoding="utf8")
calc=json.JSONDecoder().raw_decode(html.split("const DATA = ",1)[1])[0]["contests"]
qboards=[sorted([t["performance"] for t in b["teams"] if t.get("event")],reverse=True) for b in calc if b["contest_id"] in (4071,4113)]
audit=Path("docs/journal/2026-11-23-hk-opponent-replay.md").read_text(encoding="utf8")
prior={parts[1]:float(parts[-1]) for l in audit.split("## Reproduce")[0].splitlines()
       if l.startswith("| ") and (parts:=l.strip("| ").split(" | "))[-1].isdigit()}
mu=[]; count=[]
for t in teams:
    a=rated.get((t["school"],t["team"]))
    if a is None:
        rk=t.get("mean_online_rank") or prior[t["team"]]
        a=(np.mean([q[min(len(q)-1,round(rk)-1)] for q in qboards]),1)
    mu.append(a[0]);count.append(a[1])
mu=np.array(mu); mu[me]=2327
sd=182*np.sqrt(1+1/np.array(count))
skillbin=np.digitize(mu,[2050,2300,2500])
rng=np.random.default_rng(20261123)
draws=10000
day=rng.normal(mu,sd,(draws,len(mu)))
print("Shenyang roster appearance",[(s['title'],r['rank']) for s in stations for r in s['teams'] if r['name']=='NUM-R^3'])
# Estimate future skips from the actual transitions from three sites to five,
# stratified by HK strength and existing school seats. Capped and member skips are both counted.
def forecast(k,reviewed,scenario):
    ids=np.array([i for i,t in enumerate(teams) if not reviewed or t["status"]=="Reviewed"])
    _,cap,dup=allocation(all_sites,k)
    remaining=3-cap
    confirmed=dup | (remaining==0)
    if scenario=="base" and k==depth: print("school/roster/both",sum(remaining[ids]==0),sum(dup[ids]),sum(dup[ids] & (remaining[ids]==0)))
    blocked=np.tile(dup,(draws,1))
    # Estimate future school seat gains conditional on existing school count.
    # Use one observation per school per split, not one per entrant.
    _,first=np.unique(sid,return_index=True)
    future=np.zeros((draws,len(first)),dtype=int)
    history=[allocation(sub,k)[1:] for sub in subsets]
    if scenario!="five only":
        for j,idx in enumerate(first):
            old=cap[idx]
            if old==3:continue
            changes=[np.maximum(0,cap[first]-c[first])[c[first]==old] for c,_ in history]
            choices=np.concatenate(changes)
            if len(choices):future[:,j]=rng.choice(choices,draws)
        # Conditional roster-overlap rate for schools that remain below their cap.
        for i in range(len(teams)):
            if confirmed[i] or i==me:continue
            similar=(skillbin==skillbin[i]) & (cap<3)
            match=np.concatenate([dup[similar & ~prevdup] for _,prevdup in history])
            if len(match):blocked[:,i]|=rng.random(draws)<match.mean()
    room=remaining-future[:,sid]
    if scenario in ("10% unfilled","20% unfilled"):
        # Withdrawals release school capacity and may release a matching lineup.
        before=3-room[:,first]
        released=rng.binomial(before,.1 if scenario.startswith("10") else .2)
        room+=released[:,sid]
        release_share=released/np.maximum(before,1)
        blocked &= rng.random(blocked.shape)>=release_share[:,sid]
    if scenario=="known rewards unused":
        hosts={school(s["hostSchool"]) for s in raw["stations"] if s.get("hostSchool")}
        reward_data=read("data/ec_online/quota_evidence.json")
        wf={school(s) for yr in reward_data["wf_editions_by_season"]["2026"] for s in reward_data["wf_schools"][str(yr)]}
        room+=np.isin(schools,list(hosts|wf))
    # NUM's forecast is conditional on arriving at HK still eligible.
    room[:,sid==sid[me]]=np.maximum(room[:,sid==sid[me]],1)
    blocked[:,me]=False
    order=ids[np.argsort(-day[:,ids],axis=1)]
    report=[]
    for ix,finish in enumerate(order):
        left=room[ix,first].copy()
        got=[]; myseat=False
        for place,i in enumerate(finish[:round(.60*len(ids))],1):
            if blocked[ix,i] or left[sid[i]]<=0:continue
            left[sid[i]]-=1; got.append(place)
            if i==me:myseat=True
            if len(got)==10:break
        assert len(got)==10
        mine=1+np.flatnonzero(finish==me)[0]
        gold=round(.10*len(ids))
        report.append([got[-1],myseat,mine,mine<=gold,day[ix,finish[gold-1]],day[ix,finish[got[-1]-1]],day[ix,finish[got[7]-1]],got[7]])
    a=np.array(report)
    print(k,len(ids),scenario,"blocked",confirmed[ids].sum(),"depth10 p10/50/90",np.percentile(a[:,0],[10,50,90]),"seat,place,gold",a[:,1].mean(),np.median(a[:,2]),a[:,3].mean(),"gold/seat scores",np.median(a[:,4:6],axis=0),"8seat depth",np.median(a[:,7]))
    if k==depth and scenario in ("base","10% unfilled","20% unfilled"):
        print("tenth seat by rank 20/25/30/35",np.round([(a[:,0]<=x).mean() for x in (20,25,30,35)],3))
    if k==depth and reviewed and scenario=="base":
        print("blocked among 25 strongest",[(teams[i]["team"],int(cap[i]),bool(dup[i])) for i in ids[np.argsort(-mu[ids])[:25]] if confirmed[i]])
        for pos in (15,20,25,30,35):
            band=np.abs(a[:,2]-pos)<=1
            print("seat given rank",pos,round(a[band,1].mean(),3))
for size in (True,False):
    for scenario in ("five only","base","10% unfilled","20% unfilled","known rewards unused"):
        forecast(depth,size,scenario)
for k in sorted({min(depths),max(depths),int(np.median(late)),82}-{depth}): forecast(k,True,"base")
board_ids=[-162528714534630,4593,4694,-216770522111721,4607]
for st,cid in zip(stations,board_ids):
    board=next(b for b in calc if b["contest_id"]==cid)
    has_event=any(t.get("event") for t in board["teams"])
    rating={(norm_name(t["name"]),t["solved"]):t["performance"] for t in board["teams"] if t.get("event") or not has_event}
    for line in (math.ceil(st["officialCount"]/10),depth):
        near=st["teams"][line-3:line+2]
        perf=[rating[(norm_name(r["name"]),r["solved"])] for r in near if (norm_name(r["name"]),r["solved"]) in rating]
        print("mainland line",st["title"],line,round(np.median(perf)) if perf else None,len(perf))





```
