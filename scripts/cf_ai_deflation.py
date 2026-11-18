#!/usr/bin/env python3
"""Codeforces rating deflation and AI use (report: cf_ai_deflation.md).

    ./.venv/bin/python scripts/cf_ai_deflation.py --fetch-rc   # contest.ratingChanges, every contest since 2018
    ./.venv/bin/python scripts/cf_ai_deflation.py --fetch-st   # contest.standings, rated rounds since 2021
    ./.venv/bin/python scripts/cf_ai_deflation.py --analyze    # tables on stdout, output/cf_ai_deflation.json

--analyze replays the published rating formula on every contest since 2019-06 (about 25 min the first
time) and caches the replayed deltas per contest in data/cf_ai/replay.npz.

Public API only, anonymous GET, no cookie. Calls start at least 2.1 s apart (the API limit is one
call per 2 s); downloads overlap on up to 4 threads. Each response is reduced and cached as gzip
JSON in data/cf_ai/ (gitignored), so the fetch resumes where it stopped.

rc/<cid>.json.gz  {"cid", "rows": [[handle, rank, oldRating, newRating], ...]}  (empty rows = unrated)
st/<cid>.json.gz  {"cid", "problems": [[index, rating|null], ...],
                   "rows": [[handle, rank, [solve second | -1 per problem]], ...]}  (CONTESTANT rows only)
"""
import concurrent.futures
import gzip
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "cf_ai"
RC, ST = D / "rc", D / "st"
API = "https://codeforces.com/api/"
RC_FROM = datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp()
ST_FROM = datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()

_lock = threading.Lock()
_next = [0.0]


def call(method):
    """GET API method; spaces call starts 2.1 s apart across threads; retries the call limit."""
    for attempt in range(8):
        with _lock:
            wait = _next[0] - time.time()
            if wait > 0:
                time.sleep(wait)
            _next[0] = time.time() + 2.1
        req = urllib.request.Request(API + method, headers={"Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            data = json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            try:
                data = json.loads(body)
            except ValueError:
                data = {"status": "FAILED", "comment": f"HTTP {e.code}"}
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            data = {"status": "FAILED", "comment": f"network: {e}"}
        if data["status"] == "OK":
            return data["result"]
        comment = data.get("comment", "")
        if "limit exceeded" in comment or comment.startswith(("HTTP 5", "network")):
            time.sleep(5 * (attempt + 1))
            continue
        return {"failed": comment}
    raise RuntimeError(f"{method}: gave up")


def contests():
    f = D / "contest_list.json"
    if not f.exists():
        D.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(call("contest.list?gym=false")))
    return [c for c in json.loads(f.read_text()) if c["phase"] == "FINISHED"]


def save(path, obj):
    path.write_bytes(gzip.compress(json.dumps(obj, separators=(",", ":")).encode()))


def fetch_rc(c):
    res = call(f"contest.ratingChanges?contestId={c['id']}")
    rows = [] if isinstance(res, dict) else [[x["handle"], x["rank"], x["oldRating"], x["newRating"]] for x in res]
    save(RC / f"{c['id']}.json.gz", {"cid": c["id"], "rows": rows, "failed": res.get("failed") if isinstance(res, dict) else None})
    return c["id"], len(rows)


def fetch_st(c):
    res = call(f"contest.standings?contestId={c['id']}")
    if "failed" in res:
        save(ST / f"{c['id']}.json.gz", {"cid": c["id"], "problems": [], "rows": [], "failed": res["failed"]})
        return c["id"], 0
    rows = []
    for row in res["rows"]:
        p = row["party"]
        if p["participantType"] != "CONTESTANT" or p.get("ghost") or len(p["members"]) != 1:
            continue
        rows.append([p["members"][0]["handle"], row["rank"],
                     [pr.get("bestSubmissionTimeSeconds", -1) if pr["points"] > 0 else -1 for pr in row["problemResults"]]])
    save(ST / f"{c['id']}.json.gz", {"cid": c["id"], "problems": [[q["index"], q.get("rating")] for q in res["problems"]],
                                     "rows": rows})
    return c["id"], len(rows)


def run(todo, fn):
    done = 0
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for cid, n in ex.map(fn, todo):
            done += 1
            print(f"{done}/{len(todo)} {cid} rows={n}", flush=True)


# ---------------------------------------------------------------- analysis

CUM_PROMO = [0, 500, 850, 1100, 1250, 1350, 1400]  # displayed bonus after k contests (new accounts since 2020)
BANDS = [0, 1200, 1400, 1600, 1900, 2100, 2400, 9999]
BAND_NAMES = ["<1200", "1200-1399", "1400-1599", "1600-1899", "1900-2099", "2100-2399", "2400+"]
VET = 10  # prior rated contests that make a veteran


def month(t):
    d = datetime.fromtimestamp(t, timezone.utc)
    return (d.year - 2018) * 12 + d.month - 1


def month_name(m):
    return f"{2018 + m // 12}-{m % 12 + 1:02d}"


def build():
    """Rows of every rated contest since 2018 in time order, with internal ratings.

    New accounts since the 2020 change show 0 and get displayed bonuses 500/350/250/150/100/50 over
    six contests on top of an internal 1400 start: internal = displayed + 1400 - CUM_PROMO[k].
    Returns numpy columns and a consistency count (old rating != previous new rating)."""
    import numpy as np
    cl = {c["id"]: c for c in contests()}
    cs = []
    for p in RC.glob("*.json.gz"):
        d = json.loads(gzip.decompress(p.read_bytes()))
        if d["rows"]:
            c = cl[d["cid"]]
            cs.append((c["startTimeSeconds"], d["cid"], d["rows"]))
    cs.sort(key=lambda x: (x[0], x[1]))
    hid, st = {}, {}  # handle -> id; id -> [k, 0-start flag, last displayed new, fresh account flag]
    cols = {k: [] for k in ("t", "cid", "h", "k", "new0", "fresh", "old", "new", "rank", "n")}
    bad = 0
    for t, cid, rows in cs:
        n = len(rows)
        for h, rank, old, new in rows:
            i = hid.setdefault(h, len(hid))
            s = st.get(i)
            if s is None:
                s = st[i] = [0, old == 0, None, old in (0, 1500)]  # 1500 = new account before May 2020
            elif s[2] != old:
                bad += 1
            k = s[0]
            io = old + (1400 - CUM_PROMO[min(k, 6)] if s[1] else 0)
            inn = new + (1400 - CUM_PROMO[min(k + 1, 6)] if s[1] else 0)
            for key, v in (("t", t), ("cid", cid), ("h", i), ("k", k), ("new0", s[1]), ("fresh", s[3]), ("old", io), ("new", inn),
                           ("rank", rank), ("n", n)):
                cols[key].append(v)
            s[0], s[2] = k + 1, new
    arr = {k: np.array(v, dtype=np.int64 if k == "t" else np.int32) for k, v in cols.items()}
    arr["new0"], arr["fresh"] = arr["new0"].astype(bool), arr["fresh"].astype(bool)
    names = {c[1]: cl[c[1]]["name"] for c in cs}
    return arr, names, bad, len(cs), hid


def step(y, w=None, lo=0, hi=None):
    """Least-squares change point: y = mean_before for months < tau, mean_after from tau on.
    Returns (tau, mean before, mean after) for the best tau in [lo, hi)."""
    import numpy as np
    y = np.asarray(y, dtype=float)
    w = np.ones_like(y) if w is None else np.asarray(w, dtype=float)
    ok = ~np.isnan(y) & (w > 0)
    best = None
    for tau in range(max(lo, 1), (hi or len(y)) - 1):
        a, b = ok & (np.arange(len(y)) < tau), ok & (np.arange(len(y)) >= tau)
        if not a.any() or not b.any():
            continue
        ma, mb = np.average(y[a], weights=w[a]), np.average(y[b], weights=w[b])
        sse = (w[a] * (y[a] - ma) ** 2).sum() + (w[b] * (y[b] - mb) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, tau, float(ma), float(mb))
    return best[1:]


def replay(r, rank):
    """Codeforces rating change by the published algorithm (blog entry 20762) for internal old ratings r
    and API ranks (ties share the first place). Returns integer deltas in the input order."""
    import numpy as np
    n = len(r)
    order = np.argsort(rank, kind="stable")
    r, rank = r[order], rank[order]
    _, first, cnt = np.unique(rank, return_index=True, return_counts=True)
    place = np.repeat(first + cnt, cnt).astype(float)  # a tie group gets the place of its last member
    vals, vc = np.unique(r, return_counts=True)
    grid = np.arange(0, 8001)
    S = np.ones(len(grid))  # S[R] = 1 + sum over everyone of P(they beat rating R)
    for chunk in np.array_split(np.arange(len(vals)), max(1, len(vals) // 200)):
        S += (vc[chunk][None, :] / (1 + 10 ** ((grid[:, None] - vals[chunk][None, :]) / 400))).sum(1)
    seed = S[r] - 0.5  # others only
    mid = np.sqrt(place * seed)
    left, right = np.ones(n, int), np.full(n, 8000)
    while (right - left > 1).any():
        mm = (left + right) // 2
        go = S[mm] < mid
        open_ = right - left > 1
        right = np.where(go & open_, mm, right)
        left = np.where(~go & open_, mm, left)
    delta = np.trunc((left - r) / 2).astype(int)
    delta += int(np.trunc(-delta.sum() / n)) - 1
    z = min(int(4 * round(np.sqrt(n))), n)
    top = np.argsort(-r, kind="stable")[:z]
    delta += min(max(int(np.trunc(-delta[top].sum() / z)), -10), 0)
    out = np.empty(n, int)
    out[order] = delta
    return out


def analyze():
    import numpy as np
    a, names, bad, ncont, hid = build()
    N = len(a["t"])
    ut, inv = np.unique(a["t"], return_inverse=True)
    m = np.array([month(int(t)) for t in ut])[inv]  # month of each row
    M = int(m.max()) + 1
    d = a["new"] - a["old"]
    vet = a["k"] >= VET
    band = np.digitize(a["old"], BANDS) - 1
    out = {"rows": int(N), "contests": ncont, "handles": int(a["h"].max()) + 1, "old_mismatch": int(bad),
           "months": [month_name(i) for i in range(M)]}

    # 1. volume: participations, first contests of new accounts (0-start, or 1500 before May 2020)
    first = a["fresh"] & (a["k"] == 0)
    out["participations"] = np.bincount(m, minlength=M).tolist()
    out["new_accounts"] = np.bincount(m[first], minlength=M).tolist()

    # 2. veterans' mean internal change per contest, by band; flow by experience group
    vb = {}
    for b, nm in enumerate(BAND_NAMES):
        sel = vet & (band == b)
        cnt = np.bincount(m[sel], minlength=M)
        s = np.bincount(m[sel], weights=d[sel], minlength=M)
        vb[nm] = {"n": cnt.tolist(), "mean": np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan).round(2).tolist()}
    cnt = np.bincount(m[vet], minlength=M)
    vb["all"] = {"n": cnt.tolist(), "mean": (np.bincount(m[vet], weights=d[vet], minlength=M) / np.maximum(cnt, 1)).round(2).tolist()}
    out["veteran_delta"] = vb
    groups = {"new account, k<6": a["fresh"] & (a["k"] < 6), "new account, 6<=k<10": a["fresh"] & (a["k"] >= 6) & (a["k"] < VET),
              "veteran (k>=10)": vet, "older account, k<10": ~a["fresh"] & (a["k"] < VET)}
    out["flow_per_participation"] = {}
    for g, sel in groups.items():
        cnt = np.bincount(m[sel], minlength=M)
        out["flow_per_participation"][g] = {"n": cnt.tolist(), "sum": np.bincount(m[sel], weights=d[sel], minlength=M).round(0).tolist()}

    # 3. jumps: veteran below 1600 gaining >= +150 in one contest, per 1000 such participations
    low = vet & (a["old"] < 1600)
    for thr in (100, 150, 200):
        j = low & (d >= thr)
        out[f"jump{thr}_per_1000"] = (1000 * np.bincount(m[j], minlength=M) / np.maximum(np.bincount(m[low], minlength=M), 1)).round(2).tolist()

    # 4. fast climbers: new accounts reaching internal >= 1900 (or 2100) within their first 10 contests
    order = np.lexsort((a["t"], a["h"]))
    h_s, k_s, new_s, m_s, n0_s = a["h"][order], a["k"][order], a["new"][order], m[order], a["fresh"][order]
    newacc = n0_s & (k_s < VET)
    for thr in (1900, 2100):
        hit = newacc & (new_s >= thr)
        hits = np.unique(h_s[hit])
        sel = n0_s & (k_s == 0)
        fm = dict(zip(h_s[sel].tolist(), m_s[sel].tolist()))  # first month per new account
        c = np.zeros(M)
        for h in hits.tolist():
            c[fm[h]] += 1
        out[f"climb{thr}_within{VET}"] = c.tolist()
    out["climb_share_per_1000_new"] = {thr: (1000 * np.array(out[f"climb{thr}_within{VET}"]) / np.maximum(np.array(out["new_accounts"]), 1)).round(2).tolist() for thr in (1900, 2100)}

    # 5. cohort 12-month change of active veterans, by band at the anchor (quarters)
    out["cohort12"] = cohort(a, h_s, order, 12)
    out["cohort22"] = cohort(a, h_s, order, 22)

    # 6. published formula replayed on every contest since mid-2019: veterans' formula delta (what ranks
    # and ratings give) and the residual actual - formula, for two seedings of new accounts (A: internal =
    # displayed + 1400 - promotions so far; B: one promotion step lower in contests 2-6)
    pred = formula(a)
    out["formula"] = {}
    for key in ("A", "B"):
        ok = vet & (pred[key] > -99999)
        res = {}
        for b, nm in enumerate(BAND_NAMES):
            sel = ok & (band == b)
            cnt = np.bincount(m[sel], minlength=M)
            res[nm] = {"n": cnt.tolist(),
                       "formula": (np.bincount(m[sel], weights=pred[key][sel], minlength=M) / np.maximum(cnt, 1)).round(2).tolist(),
                       "residual": (np.bincount(m[sel], weights=(d - pred[key])[sel], minlength=M) / np.maximum(cnt, 1)).round(2).tolist()}
        cnt = np.bincount(m[ok], minlength=M)
        res["exact_share"] = (np.bincount(m[ok], weights=(d == pred[key])[ok], minlength=M) / np.maximum(cnt, 1)).round(3).tolist()
        out["formula"][key] = res
    out["solves"] = solves(a, m, M, names, hid)
    return out, a, m, names


def formula(a):
    """Replayed deltas for every row of a contest since 2019-06 under seedings A and B (-99999 before);
    cached per contest in data/cf_ai/replay.npz."""
    import numpy as np
    f = D / "replay.npz"
    cache = dict(np.load(f)) if f.exists() else {}
    cid = a["cid"]
    starts = np.r_[0, np.flatnonzero(cid[1:] != cid[:-1]) + 1]
    ends = np.r_[starts[1:], len(cid)]
    out = {"A": np.full(len(cid), -99999, np.int32), "B": np.full(len(cid), -99999, np.int32)}
    cum = np.array(CUM_PROMO)
    since = datetime(2019, 6, 1, tzinfo=timezone.utc).timestamp()
    new = False
    for s, e in zip(starts, ends):
        if a["t"][s] < since:
            continue
        c = int(cid[s])
        if f"A{c}" not in cache or len(cache[f"A{c}"]) != e - s:
            r, k, n0 = a["old"][s:e].astype(int), a["k"][s:e], a["new0"][s:e]
            kk = np.minimum(k, 6)
            disp = r - np.where(n0, 1400 - cum[kk], 0)
            ramp = n0 & (k >= 1) & (k < 6)
            cache[f"A{c}"] = replay(r, a["rank"][s:e])
            cache[f"B{c}"] = replay(np.where(ramp, disp + 1400 - cum[np.minimum(kk + 1, 6)], r).astype(int), a["rank"][s:e])
            new = True
        out["A"][s:e], out["B"][s:e] = cache[f"A{c}"], cache[f"B{c}"]
    if new:
        np.savez_compressed(f, **cache)
    return out


def cohort(a, h_s, order, months):
    """For each quarter anchor A: veterans (>= VET contests before A) active in the half-year before A
    and in the half-year before A + `months`; change of internal rating between the two dates."""
    import numpy as np
    t_s, new_s, k_s = a["t"][order], a["new"][order], a["k"][order]
    HALF = 182 * 86400
    res = {}

    def state_at(T):
        sel = t_s < T
        hh, tt, rr, kk = h_s[sel], t_s[sel], new_s[sel], k_s[sel]
        # last row per handle (rows are sorted by handle then time)
        last = np.r_[hh[1:] != hh[:-1], True]
        return hh[last], tt[last], rr[last], kk[last] + 1

    for y in range(2019, 2027):
        for q in range(4):
            A = datetime(y, 1 + 3 * q, 1, tzinfo=timezone.utc).timestamp()
            e = 3 * q + months
            END = datetime(y + e // 12, 1 + e % 12, 1, tzinfo=timezone.utc).timestamp()
            if END > a["t"].max() + 86400:
                continue
            h0, t0, r0, k0 = state_at(A)
            ok0 = (t0 >= A - HALF) & (k0 >= VET)
            h1, t1, r1, _ = state_at(END)
            ok1 = t1 >= END - HALF
            common, i0, i1 = np.intersect1d(h0[ok0], h1[ok1], return_indices=True)
            ra, rb = r0[ok0][i0], r1[ok1][i1]
            band = np.digitize(ra, BANDS) - 1
            key = f"{y}Q{q + 1}"
            res[key] = {"n_start": int(ok0.sum()), "n_both": int(len(common)), "bands": {}}
            for b, nm in enumerate(BAND_NAMES):
                s = band == b
                if s.sum() >= 30:
                    ch = rb[s] - ra[s]
                    res[key]["bands"][nm] = {"n": int(s.sum()), "mean": round(float(ch.mean()), 1),
                                             "se": round(float(ch.std(ddof=1) / np.sqrt(s.sum())), 1)}
            res[key]["all"] = {"n": int(len(common)), "mean": round(float((rb - ra).mean()), 1)}
    return res


def solves(a, m, M, names, hid):
    """From the standings: (1) veterans rated 1000-1599 on problems rated >= 600 above them, observed
    solves vs Codeforces' expected 1 / (1 + 10^((R - r) / 400)), per month; (2) the same ratio on a
    grid of rating band x gap, per half-year; (3) median problem rating by position in Div. 2 rounds."""
    import numpy as np
    cid = a["cid"]
    starts = np.r_[0, np.flatnonzero(cid[1:] != cid[:-1]) + 1]
    block = {int(cid[s]): (s, e) for s, e in zip(starts, np.r_[starts[1:], len(cid)])}
    obs, exp_, cnt = np.zeros(M), np.zeros(M), np.zeros(M)
    GAPS = [-9999, 0, 200, 400, 600, 800, 9999]
    RB = [0, 1000, 1200, 1400, 1600, 1900, 2100, 9999]
    grid = {}  # half-year -> [obs, exp, cells] over RB x GAPS
    pos = {}  # half-year -> position -> [ratings]
    for f in sorted(ST.glob("*.json.gz")):
        d = json.loads(gzip.decompress(f.read_bytes()))
        c = d["cid"]
        if not d["rows"] or c not in block:
            continue
        R = np.array([q[1] if q[1] is not None else np.nan for q in d["problems"]], dtype=float)
        s, e = block[c]
        local = {int(h): j for j, h in zip(range(s, e), a["h"][s:e])}
        idx, Y = [], []
        for h, rank, times in d["rows"]:
            j = local.get(hid.get(h, -1))
            if j is not None and a["k"][j] >= VET:
                idx.append(j)
                Y.append(times)
        mm = int(m[s])
        hy = f"{2018 + mm // 12}H{1 + (mm % 12) // 6}"
        name = names[c]
        if "Div. 2" in name and "Div. 1" not in name:
            for i, r in enumerate(R):
                if not np.isnan(r):
                    pos.setdefault(hy, {}).setdefault(min(i, 5), []).append(r)
        if not idx:
            continue
        r = a["old"][np.array(idx)].astype(float)
        Y = (np.array(Y) >= 0).astype(float)
        ok = ~np.isnan(R)
        Y, Rr = Y[:, ok], R[ok]
        gap = Rr[None, :] - r[:, None]
        P = 1 / (1 + 10 ** (gap / 400))
        sel = (r[:, None] >= 1000) & (r[:, None] < 1600) & (gap >= 600)
        obs[mm] += Y[sel].sum()
        exp_[mm] += P[sel].sum()
        cnt[mm] += sel.sum()
        g = grid.setdefault(hy, np.zeros((3, len(RB) - 1, len(GAPS) - 1)))
        bi = np.digitize(r, RB) - 1
        gi = np.digitize(gap, GAPS) - 1
        bi2 = np.broadcast_to(bi[:, None], gap.shape)
        np.add.at(g[0], (bi2.ravel(), gi.ravel()), Y.ravel())
        np.add.at(g[1], (bi2.ravel(), gi.ravel()), P.ravel())
        np.add.at(g[2], (bi2.ravel(), gi.ravel()), 1)
    res = {"low_vs_hard": {"obs": obs.round(1).tolist(), "exp": exp_.round(1).tolist(), "cells": cnt.tolist(),
                           "ratio": np.where(exp_ > 0, obs / np.maximum(exp_, 1e-9), np.nan).round(3).tolist()},
           "grid_bands": [f"{RB[i]}-{RB[i + 1] - 1}" for i in range(len(RB) - 1)],
           "grid_gaps": [f"{GAPS[i]}..{GAPS[i + 1]}" for i in range(len(GAPS) - 1)],
           "grid_ratio": {hy: np.where(g[1] > 0, g[0] / np.maximum(g[1], 1e-9), np.nan).round(2).tolist() for hy, g in sorted(grid.items())},
           "grid_cells": {hy: g[2].astype(int).tolist() for hy, g in sorted(grid.items())},
           "div2_median_rating_by_position": {hy: {"ABCDEF"[p]: float(np.median(v)) for p, v in sorted(ps.items())}
                                              for hy, ps in sorted(pos.items())}}
    return res


BASE = [f"{y}Q{q}" for y in (2021, 2022, 2023) for q in (1, 2, 3, 4)][:10]  # anchors 2021Q1-2023Q2, end by 2024-06


def half(series, months, weights=None):
    """Half-year means of a monthly series (weighted by `weights` when given)."""
    import numpy as np
    acc = {}
    for i, v in enumerate(series):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        y, mo = months[i].split("-")
        key = f"{y}H{1 + (int(mo) - 1) // 6}"
        w = 1 if weights is None else weights[i]
        s = acc.setdefault(key, [0.0, 0.0])
        s[0] += v * w
        s[1] += w
    return {k: s[0] / s[1] for k, s in acc.items() if s[1] > 0}


def report(out):
    import numpy as np
    mo = out["months"]
    hy = sorted(half(out["participations"], mo))
    print("\n== volume per half-year (monthly mean): rated participations, new accounts")
    p, n = half(out["participations"], mo), half(out["new_accounts"], mo)
    for k in hy:
        print(f"{k}  {p[k]:9.0f}  {n[k]:8.0f}")
    print("\n== veterans (>=10 contests): mean internal rating change per contest, by band")
    vd = out["veteran_delta"]
    print("half    " + "".join(f"{b:>11}" for b in BAND_NAMES + ["all"]))
    tab = {b: half(vd[b]["mean"], mo, weights=vd[b]["n"]) for b in BAND_NAMES + ["all"]}
    for k in hy:
        print(f"{k}  " + "".join(f"{tab[b].get(k, np.nan):11.2f}" for b in BAND_NAMES + ["all"]))
    print("\n== rating flow: mean internal change per participation, by account group")
    fl = out["flow_per_participation"]
    print("half    " + "".join(f"{g:>23}" for g in fl))
    ft = {g: half([x / max(c, 1) for x, c in zip(fl[g]["sum"], fl[g]["n"])], mo, weights=fl[g]["n"]) for g in fl}
    for k in hy:
        print(f"{k}  " + "".join(f"{ft[g].get(k, np.nan):23.1f}" for g in fl))
    print("\n== veterans below 1600: one-contest gains per 1000 participations; new accounts reaching 1900/2100 within 10 contests per 1000")
    j = {t: half(out[f"jump{t}_per_1000"], mo) for t in (100, 150, 200)}
    c = {t: half(out["climb_share_per_1000_new"][t], mo, weights=out["new_accounts"]) for t in (1900, 2100)}
    for k in hy:
        print(f"{k}  +100:{j[100][k]:7.1f}  +150:{j[150][k]:6.1f}  +200:{j[200][k]:6.1f}   1900:{c[1900].get(k, np.nan):6.1f}  2100:{c[2100].get(k, np.nan):6.1f}")
    print("\n== 12-month change of active veterans, by band at the anchor; excess vs the 2021Q1-2023Q2 baseline")
    co = out["cohort12"]
    base = {b: np.mean([co[q]["bands"][b]["mean"] for q in BASE if b in co.get(q, {}).get("bands", {})]) for b in BAND_NAMES}
    print("anchor  " + "".join(f"{b:>11}" for b in BAND_NAMES) + "      n")
    print("base    " + "".join(f"{base[b]:11.1f}" for b in BAND_NAMES))
    for q, v in co.items():
        print(f"{q}  " + "".join(f"{v['bands'][b]['mean'] - base[b]:+11.1f}" if b in v["bands"] else f"{'':11}" for b in BAND_NAMES)
              + f"  {v['n_both']:6d}")
    print("\n== 22-month change of active veterans by band: baseline windows (start 2021Q1-2022Q3) and the AI-era window")
    c22 = out["cohort22"]
    b22 = [q for q in c22 if "2021Q1" <= q <= "2022Q3"]
    print("anchor  " + "".join(f"{b:>11}" for b in BAND_NAMES) + "      n")
    for q in b22 + [q for q in c22 if q >= "2024Q4"]:
        v = c22[q]
        print(f"{q}  " + "".join(f"{v['bands'][b]['mean']:11.1f}" if b in v["bands"] else f"{'':11}" for b in BAND_NAMES) + f"  {v['n_both']:6d}")
    if "2025Q1" in c22:
        print("2025Q1 minus baseline mean (range of baseline excess):")
        for b in BAND_NAMES:
            base_vals = [c22[q]["bands"][b]["mean"] for q in b22 if b in c22[q]["bands"]]
            bm = np.mean(base_vals)
            if b in c22["2025Q1"]["bands"]:
                print(f"   {b:>10}: {c22['2025Q1']['bands'][b]['mean'] - bm:+7.1f}   baseline {min(base_vals) - bm:+.1f}..{max(base_vals) - bm:+.1f}")
    s = out.get("solves", {})
    if s and any(s["low_vs_hard"]["cells"]):
        print("\n== veterans 1000-1599 on problems >= 600 above them: observed / expected solves")
        lh = s["low_vs_hard"]
        o, e = half(lh["obs"], mo), half(lh["exp"], mo)
        for k in sorted(o):
            if e[k] > 0:
                print(f"{k}  obs {o[k]:8.1f}  exp {e[k]:8.1f}  ratio {o[k] / e[k]:5.2f}")
        print("\n== Div. 2 median problem rating by position")
        for k, v in s["div2_median_rating_by_position"].items():
            print(k, "  ".join(f"{p}:{r:.0f}" for p, r in v.items()))
    fo = out["formula"]
    for key in ("A", "B"):
        print(f"\n== published formula replayed, seeding {key}: veterans' residual (actual - formula) per contest, exact share")
        print("half    " + "".join(f"{b:>11}" for b in BAND_NAMES) + "   exact")
        rt = {b: half(fo[key][b]["residual"], mo, weights=fo[key][b]["n"]) for b in BAND_NAMES}
        ex = half(fo[key]["exact_share"], mo, weights=fo[key]["1600-1899"]["n"])
        for k in hy:
            if k in rt["1600-1899"]:
                print(f"{k}  " + "".join(f"{rt[b].get(k, np.nan):11.2f}" for b in BAND_NAMES) + f"   {ex.get(k, np.nan):.2f}")
    print("\n== formula delta (seeding B) of veterans: mean per contest, by band")
    ftb = {b: half(fo["B"][b]["formula"], mo, weights=fo["B"][b]["n"]) for b in BAND_NAMES}
    for k in hy:
        if k in ftb["1600-1899"]:
            print(f"{k}  " + "".join(f"{ftb[b].get(k, np.nan):11.2f}" for b in BAND_NAMES))
    # change points, monthly from 2022-01 to the last full month
    last = len(mo) - 1
    lo = mo.index("2022-01")
    hiB = ["1900-2099", "2100-2399", "2400+"]
    bidx = [i for i, x in enumerate(mo) if "2021-01" <= x <= "2023-12"]
    fbase = {b: np.average([fo["B"][b]["formula"][i] for i in bidx], weights=[fo["B"][b]["n"][i] for i in bidx]) for b in hiB}
    exc, wexc = [], []
    for i in range(len(mo)):
        n_ = sum(fo["B"][b]["n"][i] for b in hiB)
        exc.append(sum((fo["B"][b]["formula"][i] - fbase[b]) * fo["B"][b]["n"][i] for b in hiB) / max(n_, 1))
        wexc.append(n_)
    g69 = fl["new account, 6<=k<10"]
    series = {"veterans 1900+: formula delta minus 2021-23 mean": (exc, wexc),
              "new accounts, contests 7-10: delta per contest": ([x / max(c, 1) for x, c in zip(g69["sum"], g69["n"])], g69["n"]),
              "veterans <1600: +200 jumps per 1000": (out["jump200_per_1000"], None)}
    if s and any(s["low_vs_hard"]["cells"]):
        series["veterans 1000-1599 on problems >=600 above: obs/exp"] = (s["low_vs_hard"]["ratio"], s["low_vs_hard"]["exp"])
    print("\n== change points (two means, monthly from 2022-01)")
    out["change_points"] = {}
    for nm, (y, w) in series.items():
        y = [np.nan if v is None else v for v in y[lo:last]]
        tau, before, after = step(y, None if w is None else w[lo:last], lo=3, hi=len(y) - 3)
        out["change_points"][nm] = {"month": mo[lo + tau], "before": round(before, 3), "after": round(after, 3)}
        print(f"{nm:52s} {mo[lo + tau]}  before {before:+8.3f}  after {after:+8.3f}")


def main():
    cs = contests()
    if "--analyze" in sys.argv:
        out, *_ = analyze()
        report(out)
        f = ROOT / "output" / "cf_ai_deflation.json"
        f.write_text(json.dumps(out, indent=0))
        print(f"wrote {f}: {out['rows']} rows, {out['contests']} contests, {out['handles']} handles, "
              f"old!=previous new: {out['old_mismatch']}")
    if "--fetch-rc" in sys.argv:
        RC.mkdir(parents=True, exist_ok=True)
        todo = [c for c in cs if c["startTimeSeconds"] >= RC_FROM and not (RC / f"{c['id']}.json.gz").exists()]
        run(sorted(todo, key=lambda c: c["startTimeSeconds"]), fetch_rc)
    if "--fetch-st" in sys.argv:
        ST.mkdir(parents=True, exist_ok=True)
        rated = {int(p.name.split(".")[0]) for p in RC.glob("*.json.gz")
                 if json.loads(gzip.decompress(p.read_bytes()))["rows"]}
        todo = [c for c in cs if c["startTimeSeconds"] >= ST_FROM and c["id"] in rated
                and not (ST / f"{c['id']}.json.gz").exists()]
        run(sorted(todo, key=lambda c: c["startTimeSeconds"]), fetch_st)


if __name__ == "__main__":
    main()
