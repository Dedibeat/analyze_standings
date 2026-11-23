# NUM-R³ against Hong Kong opponents

The November 22 export contains 112 Reviewed and 14 Pending registrations. In the two actual qualifiers the team rose from 32nd to 16th among the same 77 Reviewed entrants, and from 33rd to 16th among the same 87 Reviewed + Pending entrants. At Shenyang the team finished 87/401 official, ahead of 8 of 13 matched Reviewed rivals. Its unassisted Chengdu and Wuhan virtuals beat 5/6 and 12/13 respectively. Xi’an beat all five matched Reviewed rivals, with identities supported only by the school and team names there. Small and repeated opponent samples limit extrapolation.

## Full-field estimates

From the two actual qualifier ranks, approximately 31/112 Reviewed or 32/126 Reviewed + Pending. From the two qualifiers plus Shenyang on the previously computed performance scale, 28/112 or 29/126. From practice alone, 15/112 or 15/126, moving to 20/112 or 21/126 after subtracting 100 CF points. Combining all 18 contests gives 15/112 or 15/126, moving to 20/112 or 21/126 with the virtual deduction.

## Audit of the 29 previously unlinked entries

The final column estimates a rank on the Asia East online qualifier scale. Smaller is stronger. NUM-R³’s actual two-round geometric mean is 436. Each current-board estimate uses the qualifier results of the nearest 21 ranked teams with usable links. The projected HK place sums the fraction of each team's comparison sample ahead of NUM-R³. For historical qualifiers, each round supplies one observation. School estimates use historical HK placements from that university, translated by percentile. Peer estimates use the eleven linked HK entrants closest by log university qualifier rank. Lingnan uses the linked field as its fallback. These are descriptive estimates with sparse evidence. Membership matches require two shared names. The Xi’an board lacks members, so CUHK’s 慶曆四年春 is a provisional same-school, exact-team-name match. Chongqing lists only one member, whose name corresponds to MinJun Chen on the 2024 HK team that finished 116th. Duke Kunshan’s Zhong Feiyang also appears as Feiyang Zhong on its 106th-place 2024 HK team. Each remains a university estimate.

| University | HK team | Status | Basis | Matched boards and ranks, or historical qualifier ranks | Estimated qualifier rank |
|---|---|---|---|---|---:|
| Yango University | Give it up, there’s no future in playing galgames | Reviewed | current board | /ccpc/12th/nanchang-invitational #302 | 1717 |
| Shanghai University of Electric Power | 星垂平野阔 | Reviewed | 2025 qualifier | /2025/nanjing #171, /2025/wuhan #173 | 602 |
| Duke Kunshan University | Anonymous FTP Transfer | Reviewed | university HK history | — | 765 |
| The Chinese University of Hong Kong | 越南河粉、泰式青木瓜沙拉和 C++ | Reviewed | current board | /icpc/51st/shenyang #366 | 1485 |
| The Chinese University of Hong Kong | 慶曆四年春 | Reviewed | current board | /icpc/51st/xian #148 | 615 |
| City University of Macau | 基米斗队 | Reviewed | university HK history | — | 1830 |
| New Mongol Institute of Technology | I-EAT | Reviewed | historical regional | /2025/hongkong #120 | 1746 |
| Lingnan University | LU Team | Reviewed | field prior | — | 806 |
| Shandong University of Science and Technology | 白羊号 | Reviewed | 2025 qualifier | /2025/wuhan #291, /2025/shanghai #199 | 835 |
| Lanzhou University | 兰花草 | Reviewed | peer schools | — | 668 |
| North China University of Science and Technology | 你有这时间是不是能睡一觉 | Reviewed | university HK history | — | 1126 |
| Nanjing Xiaozhuang University | 老登 | Reviewed | 2025 qualifier | /2024/kunming #432, /2025/nanjing #212, /2025/shenyang #233 | 606 |
| Southern University of Science and Technology | SUSTech-Ok | Reviewed | current board | /icpc/51st/chengdu #96 | 306 |
| Nanchang University | MRCWINNER | Reviewed | peer schools | — | 1126 |
| Dalian University of Technology | 中国奶龙大学0队 | Reviewed | current board | /icpc/51st/nanjing #230 | 665 |
| Xinjiang University | 最后一舞 | Reviewed | 2025 qualifier | /2024/shanghai #214, /2025/wuhan #156, /2025/shenyang #335 | 624 |
| Jiangxi Agricultural University | 毕业老登求收留 | Reviewed | current board | /ccpc/12th/qinhuangdao-invitational #53, /2024/chengdu #245, /2025/nanjing #209, /2025/xian #255 | 709 |
| Shenyang University of Chemical Technology | Medal come, come | Pending | 2025 qualifier | /2025/wuhan #434, /2025/xian #333 | 1152 |
| Hebei Normal University | 随便 | Reviewed | peer schools | — | 1089 |
| Henan University | O(1) Team | Reviewed | historical regional | /2025/wuhan #327 | 839 |
| Hubei University of Technology | 八分钱难倒菲比 | Reviewed | 2025 qualifier | /2025/nanjing #98, /2025/wuhan #401 | 510 |
| Hunan University of Technology | 队友说他会 | Reviewed | current board | /ccpc/12th/nanchang-invitational #197 | 1419 |
| Yantai University | 全国硕士研究生统一招生考试已经过去 22 天 | Reviewed | current board | /ccpc/12th/qinhuangdao-invitational #57 | 800 |
| Soochow University (Jiangsu) | leader让我好好打icpc | Reviewed | 2025 qualifier | /2025/chengdu #214 | 862 |
| Chongqing Metropolitan College of Science and Technology | Black Magic | Pending | university HK history | — | 1378 |
| City University of Hong Kong | CityU 0.5 | Reviewed | current board | /ccpc/12th/online-qualification #383 | 556 |
| The University of Hong Kong | 加一蚊即送三個HKU學位 | Reviewed | university HK history | — | 208 |
| The University of Hong Kong | string Team_Name = "void" | Reviewed | current board | /icpc/51st/nanjing #238 | 785 |
| Hong Kong Baptist University | HKBU_Team | Reviewed | university HK history | — | 1746 |

## Reproduce

Run this Python from the repository root in the project environment. The performance scenarios use the averages in [the contest calculation](2026-11-23-team-form-hk.md).

```python
import csv,json,math
from pathlib import Path
from collections import defaultdict
from itertools import combinations
from statistics import median,geometric_mean
from arch_b.online_gold import norm_name,norm_school
def load(file):
    return json.loads(Path(file).read_text(encoding="utf8"))
def rows(file):
    with Path("data/ec_online",file+".csv").open(encoding="utf8") as f:
        return list(csv.DictReader(f))
def names(members):
    return sorted({norm_name(" ".join(sorted(m.lower().split()))) for m in members if m.strip()})
def keys(members):
    return list(combinations(names(members),2))
field=load("output/hk_field_2026.json")
linked=field["teams"]
missing=field["unlinked"]
ours=next(r for r in linked if r["team"]=="NUM-R^3")
rank={(r["season"],r["round"],norm_school(r["school"]),norm_name(r["team"])):int(r["rank"]) for r in rows("online_teams") if r["rank"]}
online=defaultdict(list)
for r in rows("online_rosters"):
    s=norm_school(r["school"])
    k=(r["season"],r["round"],s,norm_name(r["team"]))
    if k in rank:
        for pair in keys(r["members"].split("|")):
            online[pair].append((r["season"],s,rank[k],r["round"]))
def qualifiers(ms,school,year):
    hits=set(v for pair in keys(ms) for v in online[pair] if v[0]==year and (v[1]==school or not school))
    return sorted(hits) if len({h[1] for h in hits})<=1 else []
allteams=linked+missing
team_names={(norm_school(t["school"]),norm_name(t["team"])):i for i,t in enumerate(allteams)}
qual_names=defaultdict(list)
for (yr,rnd,school,team),rk in rank.items():
    if yr=="2026":qual_names[school,team].append(rk)
pairs=defaultdict(set)
for i,t in enumerate(allteams):
    for p in keys(t["members"].split("/")):
        pairs[p].add(i)
evidence=defaultdict(list)
bands=defaultdict(list)
duels=[]
boards=load("data/xcpcio_51st_regionals.json")+load("data/xcpcio_ccpc.json")
history=rows("regional_teams")
earlier=defaultdict(list)
for r in history:
    if r["season"] in {"2024","2025"} and r["official"]=="1" and r["official_rank"]:
        earlier[r["season"],r["site"]].append(dict(rank=int(r["official_rank"]),members=r["members"].split("|"),official=True,affiliation=r["school"],team_name=r["team"]))
boards.extend(dict(board_link="/"+yr+"/"+site,standings=rr) for (yr,site),rr in earlier.items())
for b in boards:
    site=b["board_link"]
    if "/51st/" not in site and "/12th/" not in site and site[1:5] not in ("2024","2025"):continue
    board=[r for r in b["standings"] if r["official"]] or b["standings"]
    anchors=[];matches={}
    for r in board:
        ms=r["members"] or []
        school=norm_school(r.get("affiliation") or "")
        hits=qualifiers(ms,school,site[1:5] if site[1:5] in ("2024","2025") else "2026")
        if not ms and site=="/icpc/51st/xian" and (school,norm_name(r["team_name"])) in qual_names:
            anchors.append((r["rank"],geometric_mean(qual_names[school,norm_name(r["team_name"])])))
        if hits:anchors.append((r["rank"],geometric_mean([h[2] for h in hits])))
        candidates={i for p in keys(ms) for i in pairs[p]}
        if not ms and site=="/icpc/51st/xian" and (school,norm_name(r["team_name"])) in team_names:
            candidates.add(team_names[school,norm_name(r["team_name"])])
        for i in candidates:
            t=allteams[i]
            if school and school not in {norm_school(t["school"]),norm_school(t["school_en"])}:continue
            assert i not in matches
            matches[i]=r
    for i,r in matches.items():
        near=sorted(anchors,key=lambda v:abs(v[0]-r["rank"]))[:21]
        estimate=median(v for _,v in near) if len(near)>=10 else None
        if site in ("/2025/hongkong","/2024/hongkong"):
            ranks=sorted(t["mean_online_rank"] for t in linked)
            estimate=ranks[min(len(ranks)-1,max(0,round(r["rank"]/len(board)*len(ranks))-1))]
        evidence[i].append((site,r["rank"],estimate))
        if estimate and site[1:5] not in ("2024","2025"): bands[i].extend(v for _,v in near)
    # Count only independent two-member matches. Use official score order.
    replay={"xian":(4,536),"chengdu":(6,894),"wuhan":(5,631)}
    name=site.rsplit("/",1)[-1]
    if "/51st/" in site and (name in replay or name=="shenyang"):
        own=next((r for r in board if r["team_name"]=="NUM-R^3"),None)
        def score(r): return (-r["total_solved"],r["penalty_seconds"]//60)
        target=score(own) if own else (-replay[name][0],replay[name][1])
        summary=[]
        for statuses in (["Reviewed"],["Reviewed","Pending"]):
            rivals=[r for i,r in matches.items() if allteams[i]["status"] in statuses and allteams[i]["team"]!="NUM-R^3"]
            summary.append((sum(score(r)>target for r in rivals),sum(score(r)<target for r in rivals),sum(score(r)==target for r in rivals)))
        duels.append((name,1+sum(score(r)<target for r in board),len(board),summary))
print("Direct wins, losses, ties:",duels)
for n in ["1","2"]:
    for statuses in (["Reviewed"],["Reviewed","Pending"]):
        rr=[t["online_ranks"][n] for t in linked if t["status"] in statuses and n in t["online_ranks"]]
        print("Qualifier",n,1+sum(r<ours["online_ranks"][n] for r in rr),len(rr))
history=rows("regional_teams")
hk=defaultdict(list)
for season in ("2024","2025"):
    group=[r for r in history if r["site"]=="hongkong" and r["season"]==season and r["official"]=="1" and r["official_rank"]]
    for r in group:hk[norm_school(r["school"])].append(int(r["official_rank"])/len(group))
ordered=sorted(t["mean_online_rank"] for t in linked)
def equivalent(p):
    return ordered[min(len(ordered)-1,max(0,round(p*len(ordered))-1))]
table=[]
samples={}
for i,t in enumerate(allteams[len(linked):],len(linked)):
    school=norm_school(t["school"]);ms=t["members"].split("/")
    obs=evidence[i]
    modern=[v for s,_,v in obs if v and s[1:5] not in ("2024","2025")]; archival=[v for s,_,v in obs if v and s[1:5] in ("2024","2025")]
    older=[]
    for yr in ("2026","2025","2024","2023","2022"):
        hits=qualifiers(ms,school,yr)
        if hits:
            older=[h[2] for h in hits];break
    schoolhk=[equivalent(q) for k in {school,norm_school(t["school_en"])} for q in hk[k]]
    peers=[r for r in linked if r["school_rank"] and r["school"]!=t["school"]]
    neighbors=sorted(peers,key=lambda r:abs(math.log(r["school_rank"]/t["school_rank"])))[:11] if t["school_rank"] else linked
    peer=[r["mean_online_rank"] for r in neighbors]
    sample=bands[i] or older or archival or schoolhk or peer
    source="current board" if modern else yr+" qualifier" if older else "historical regional" if archival else "university HK history" if schoolhk else "peer schools" if t["school_rank"] else "field prior"
    samples[i]=sample
    table.append("| "+" | ".join([t["school_en"],t["team"],t["status"],source, ", ".join(f"{s} #{r}" for s,r,_ in obs) or (", ".join(map(str,older)) if older else "—"),str(round(median(sample)))])+" |")
    print(t["school_en"],t["team"],source,round(median(sample)),obs,older, "size",len(sample))
for label,cut in (("qualifiers",ours["mean_online_rank"]),):
    for statuses in (["Reviewed"],["Reviewed","Pending"]):
        base=1+sum(t["team"]!=ours["team"] and t["status"] in statuses and t["mean_online_rank"]<cut for t in linked)
        extras=sum(sum(v<cut for v in vals)/len(vals) for i,vals in samples.items() if allteams[i]["status"] in statuses)
        print(label,statuses,base,extras,base+extras)



import numpy as np
html=Path("output/virtual_calc.html").read_text(encoding="utf8")
calc=json.JSONDecoder().raw_decode(html.split("const DATA = ",1)[1])[0]
q=[[t["performance"] for t in b["teams"] if t.get("event")] for b in calc["contests"] if b["contest_id"] in (4071,4113)]
for label,perf in (("officials",2267.333),("virtuals",2462.818),("virtuals less 100",2362.818),("combined",2430.237),("combined discounted",2346.904)):
    cut=geometric_mean(1+sum(x>perf for x in qq) for qq in q)
    ranks=[]
    for statuses in (["Reviewed"],["Reviewed","Pending"]):
        base=1+sum(t["team"]!=ours["team"] and t["status"] in statuses and t["mean_online_rank"]<cut for t in linked)
        extras=sum(sum(v<cut for v in vals)/len(vals) for i,vals in samples.items() if allteams[i]["status"] in statuses)
        ranks.append(round(base+extras,1))
    print(label,round(cut),ranks)


```
