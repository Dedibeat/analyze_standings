"""Shipped identity vs the same identity without two-shared-member links (details.md, 2026-11-17).

Both identities fit the shipped setting (``time_skip``) on the same rows:
- team prediction: the same 20% of standing rows held out (two splits), held-out cell log
  loss, paired by contest;
- CF accuracy: nested-LOCO affine map on the 184 trusted anchors, paired contest bootstrap;
- both hand panels pooled (development data);
- reported only: Jinan 2022 D, the CF 1900-2500 anchor bias, EC model - gym.

    PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 python -m scripts.identity_links [JOBS]
    -> output/identity_links.json
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from arch_a import load as L
from arch_b import hier_binary as hb, hier_time as ht
from arch_b.calibration_ablation import _purged_train
from arch_b.de_release_audit import contest_bootstrap
from arch_b.joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF
from arch_b.run import MIN_SOLVE_HOURS

SETTING = (5, 0.25, True)
SPLITS = (1, 2)
OUT = hb.ROOT / "output/identity_links.json"


def _raw():
    raw = []
    for path in [TAGGED, OLDER_ICPC, PETROZ, WF] + UCUP:
        with open(path, encoding="utf-8") as f:
            raw.extend(json.load(f))
    raw = L.dedupe_contests(raw)
    return [c for c in raw if L._max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]


def no_pair_links(raw):
    """``member_identity`` without the two-shared-member links."""
    trusted = L._trusted_names(raw)
    uf = L._UnionFind()
    for c in raw:
        for s in c["standings"]:
            tid = s["team_id"]
            stable = None if tid.startswith("$DEFAULT") else "id:" + tid
            roster = L._roster_token(s.get("members"))
            if stable is not None:
                uf.find(stable)
            if stable is None and roster is None:
                nm = L._norm_member(s.get("team_name") or "")
                if nm in trusted:
                    uf.union(f"dj:{c['contest_id']}::{tid}", "tn:" + nm)
            if roster is not None:
                uf.find(roster)
                if stable is not None:
                    uf.union(stable, roster)
    L._link_wf_top_team(raw, uf, None)
    return uf


def dataset(identity):
    raw = _raw()
    uf = L.member_identity(raw) if identity == "shipped" else no_pair_links(raw)
    return L.load([TAGGED, OLDER_ICPC, PETROZ, WF] + UCUP, uf=uf, min_solve_hours=MIN_SOLVE_HOURS)


def held_rows(n_rows, split):
    return np.random.default_rng([hb.SEED, 100 + split]).random(n_rows) < hb.FRAC


def _job(job):
    identity, split = job
    ds = dataset(identity)
    if split is None:
        res = ht.fit(ds, SETTING)
        return job, {"b": res["b"].tolist(), "participation": ds.participation_of_row, "teams": len(ds.teams)}
    held = held_rows(len(ds.team_of_row), split)
    res = ht.fit(ds, SETTING, ~held[ds.obs_row])
    sc = hb.team_scores(ds, held, res["theta"], res["b"], "binary")
    return job, {k: v.tolist() for k, v in sc.items()}


def nested_loco(b, ds):
    anchors = ht._anchors()
    idx, _ = ht._anchor_index(ds)
    cf = np.array([a["cf"] for a in anchors])
    used = ht._used(anchors)
    rows = []
    for c in sorted({a["cf_contest"] for a in anchors}):
        held = [i for i in used if anchors[i]["cf_contest"] == c]
        keep = {r["row_id"] for r in _purged_train(anchors, [anchors[i] for i in held])}
        train = [i for i in used if anchors[i]["row_id"] in keep]
        slope, icept = np.polyfit(b[idx][train], cf[train], 1)
        rows += [{"row_id": anchors[i]["row_id"], "cf_contest": c, "cf": anchors[i]["cf"],
                  "pred": float(slope * b[idx][i] + icept)} for i in held]
    return rows


def main(jobs):
    from scripts.problem_rating_audit import FRESH, HAND
    todo = [(i, s) for i in ("shipped", "no_pair_links") for s in (None,) + SPLITS]
    with ProcessPoolExecutor(jobs) as ex:
        res = dict(ex.map(_job, todo))
    if res[("shipped", None)]["participation"] != res[("no_pair_links", None)]["participation"]:
        raise RuntimeError("the two identities fit different rows")
    hb._init()
    ds = hb._G["ds"]
    pi = {(c, lab): p for p, (c, lab, _, _) in enumerate(ds.problems)}
    anchors = ht._anchors()
    idx, _ = ht._anchor_index(ds)
    gym = json.loads((hb.ROOT / "output/gym_difficulty.json").read_text(encoding="utf-8"))
    panels = {**HAND, **{k: v for k, v in FRESH.items() if k not in ht.WRONG_HAND}}
    out = {"setting": list(SETTING), "identities": {}}
    loco = {}
    for identity in ("shipped", "no_pair_links"):
        b = np.array(res[(identity, None)]["b"])
        loco[identity] = nested_loco(b, ds)
        slope, icept = ht._cf_map(b[idx], anchors)
        cf = slope * b + icept
        lab = np.array([anchors[i]["cf"] for i in ht._used(anchors)])
        pred = cf[idx][ht._used(anchors)]
        band = (lab >= 1900) & (lab < 2500)
        err = np.array([r["pred"] - r["cf"] for r in loco[identity]])
        out["identities"][identity] = {
            "teams": res[(identity, None)]["teams"],
            "nested_loco_rmse": float(np.sqrt(np.mean(err ** 2))),
            "hand_both_rmse": float(np.sqrt(np.mean([(cf[pi[k]] - v[0]) ** 2 for k, v in panels.items()]))),
            "cf_1900_2500_bias": float(np.mean(pred[band] - lab[band])),
            "ec_minus_gym_median": float(np.median([cf[pi[(g["contest_id"], g["problem_label"])]] - g["difficulty"]
                                                    for g in gym if g["region"] == "Asia East Continent"
                                                    and (g["contest_id"], g["problem_label"]) in pi
                                                    and 0.03 < g["n_solved"] / g["n_teams"] < 0.97])),
            "jinan_2022_d": float(cf[pi[(1053, "D")]]),
            "held_out": {str(s): hb.summarize(hb._np(res[(identity, s)])) for s in SPLITS},
        }
    a, b = loco["no_pair_links"], loco["shipped"]
    out["cf_rmse_no_pair_links_minus_shipped"] = contest_bootstrap(
        a, np.array([r["pred"] for r in a]), np.array([r["pred"] for r in b]), n=hb.BOOT)
    # [difference, 2.5%, 97.5%] over contests
    out["log_loss_no_pair_links_minus_shipped"] = {
        str(s): hb.paired_bootstrap(hb._np(res[("no_pair_links", s)]), hb._np(res[("shipped", s)]))["log_loss"]
        for s in SPLITS}
    i = out["identities"]
    out["adopt_no_pair_links"] = bool(
        i["no_pair_links"]["nested_loco_rmse"] < i["shipped"]["nested_loco_rmse"]
        and all(out["log_loss_no_pair_links_minus_shipped"][str(s)][1] <= 0 for s in SPLITS)
        and i["no_pair_links"]["hand_both_rmse"] <= i["shipped"]["hand_both_rmse"] + 10)
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
