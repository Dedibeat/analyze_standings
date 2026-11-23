# Simulated finishing rank at Shenyang form

Checked Claude’s branch at 78ad57f. Its 19th is a strength ordering among 105 measured teams. Replayed its simulation from published rounded means and spread (182), using the November 22 statuses. Across 20,000 draws per field the Reviewed median is 27th (middle half 17–40), with 33.7% top 20 and 10.3% gold. For all 126, the median is 28th (18–42), with 30.7% top 20 and 13.2% gold. These round to the published gold estimates. They describe results under the simulation assumptions.

The pre-Shenyang appearance filter is retrospective: the global fit and Changchun calibration use the later regional boards. The 150-point adjustment is estimated on Shenyang; the nearly identical Wuhan and previous weighted virtual performances make the adjusted forecasts agree by construction. The older 1794 virtual still counts its assisted solve.

Run this Python from the repository root with the referenced Git object available.
```python
import json,subprocess,numpy as np
from pathlib import Path
rev="78ad57f272dd304829c096e0dad5e48abb4f8e50"
doc=subprocess.check_output(["git","show",rev+":output/hk_shenyang_rank.md"]).decode()
rows=[line.strip("| ").split(" | ") for line in doc.split("## Registrants by strength",1)[1].split("\n## ")[0].splitlines() if line.startswith("| ") and line.split("|")[1].strip().isdigit()]
f=json.loads(Path("output/hk_field_2026.json").read_text(encoding="utf8"))
teams=f["teams"]+f["unlinked"]
for reviewed in (True,False):
    field=[t for t in teams if t["team"]!="NUM-R^3" and (not reviewed or t["status"]=="Reviewed")]
    keys={(t["school"],t["team"]) for t in field}
    known=[r for r in rows if (r[1],r[2]) in keys]
    mu=np.array([int(r[5]) for r in known]); n=np.array([len(r[7].split("; ")) for r in known])
    rng=np.random.default_rng(0);ranks=[]
    for _ in range(20000):
        rivals=rng.normal(mu,182/np.sqrt(n))+rng.normal(0,182,len(mu))
        u=len(field)-len(mu)
        unknown=rng.choice(mu,u)+rng.normal(0,182,u)
        me=rng.normal(2327,182/np.sqrt(3))+rng.normal(0,182)
        ranks.append(1+(rivals>me).sum()+(unknown>me).sum())
    a=np.array(ranks); print(len(field)+1,len(mu),np.quantile(a,[.25,.5,.75]),(a<=20).mean(),(a<=round((len(field)+1)*.1)).mean())
```
