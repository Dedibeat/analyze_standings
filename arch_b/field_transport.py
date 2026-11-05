"""Experiment 2 of rating_rethink.md: does calibration survive a change of field?

Research only: writes ``output/field_transport.json``; no shipped output changes.

A problem's calibrated difficulty should not depend on who attempted it. Each
board is re-measured from different subsets of its own rows, with every
team's ability fixed from fits that exclude the board's fold of contests
(5 contest folds, binary and survival). Only linked rows (teams seen in other
folds) can be used, since the rest have no outside ability. Samples are drawn
by team identity, so a team's repeated rows on a board stay together. Per
board, 30% of linked teams are a fixed target; the rest is the pool. The
survival window of the board is its latest solve outside the target rows, so
target outcomes never change training exposures. Training fields:

* ``full`` (the pool), ``strong`` / ``weak`` halves by outside binary ability,
  five pairs of disjoint ``random`` halves, five random ``quarter`` samples;
* on mixed boards (``context_fit``), equal-size ``event`` and ``mirror`` samples
  (teams whose board rows are all event or all mirror rows);
* ``independent``: strong/weak halves selected by abilities from half of the
  other contests and measured with abilities from the other half, so the
  regression to the mean of a noisy selection does not bias the refit.

Each sample refits binary and survival difficulties with abilities fixed and
recomputes every DE feature (solve rate, field size and conditional SE on the
sample). Frozen calibrators, trained on the 185 shipped dev anchors: shipped DE
(clipped), survival affine, binary affine, the survival/binary blend without
evidence terms, and ``DE_reference``: raw b + disagreement + the solve rate a
fixed external reference population, N(MU0, SIGMA_THETA^2) (the fit's own
ability prior, learned from no data), would have at the binary difficulty.

A deployed-like check refits the whole joint model with the 15 anchor boards
cut to random halves, event rows only, or a mirror-heavy versus an equal-size
event-only field (``joint_refit_check``).

Reported: strong-minus-weak, event-minus-mirror and full-minus-quarter
differences in calibrated CF (with the random-half difference as the noise
floor), DE's difference split by feature, latent log loss on the unchanged
target rows, CF RMSE of anchor problems under each field with
contest-held-out calibrators, and every calibrator's nested LOCO on the anchors.

    python -m arch_b.field_transport
"""

import json
import os
import sys

import numpy as np

from arch_a import elo
from . import model, survival
from .calibration_ablation import _purged_train
from .calibration_experiment import build_anchor_table
from .context_fit import mixed_boards, raw_by_contest, row_context, solve_decreasing
from .de_release_audit import DE, contest_bootstrap, loco, method, nested, rmse, with_binary
from .joint import load_joint_dataset
from .model import MU0, SIGMA_B, SIGMA_THETA
from .run import MIN_SOLVE_HOURS

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output", "field_transport.json")
ROOT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
FOLDS = 5
SEEDS = 5
MIN_LINKED = 60
MIN_CONTEXT = 20
TARGET = 0.3
SEED = 20261104
DE_REFERENCE = ("raw_b", "binary_minus_survival", "ref_solve_rate")
CALIBRATORS = {"DE_clip": ("clip", DE), "survival_affine": ("affine", "raw_b"),
               "binary_affine": ("affine", "b_bin"), "blend": ("blend", DE),
               "DE_reference": ("clip", DE_REFERENCE)}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


_NODES, _WEIGHTS = np.polynomial.hermite_e.hermegauss(60)


def reference_rate(b):
    """Solve probability at difficulty ``b`` averaged over the external N(MU0, SIGMA_THETA^2) population."""
    theta = MU0 + SIGMA_THETA * _NODES
    return elo.pi(theta[None, :], np.asarray(b, float)[:, None]) @ _WEIGHTS / _WEIGHTS.sum()


def refit_b(prob, y, theta, rho=None, n_problems=None):
    """Per-problem MAP difficulty with abilities fixed: binary, or survival when ``rho`` is given.

    Returns (b, conditional SE) over ``n_problems`` problem slots.
    """
    def resid_info(b):
        if rho is None:
            p = elo.pi(theta, b[prob])
            return y - p, p * (1 - p)
        lam = survival.LN2 * np.exp((theta - b[prob]) / elo.S) * rho
        return y - lam, lam

    b = solve_decreasing(lambda b: -np.bincount(prob, resid_info(b)[0], n_problems) / elo.S
                         - (b - MU0) / SIGMA_B ** 2, n_problems)
    info = resid_info(b)[1]
    se = 1 / np.sqrt(np.bincount(prob, info, n_problems) / elo.S ** 2 + 1 / SIGMA_B ** 2)
    return b, se


def calibrator(kind, feats, anchors):
    """predict(train, rows, setting), plus the setting chosen on all anchors' inner contest folds."""
    if kind == "affine":
        def f(tr, te, _p):
            slope, icept = np.polyfit([r[feats] for r in tr], [r["cf"] for r in tr], 1)
            return slope * np.array([r[feats] for r in te]) + icept
        return f, None, [None]
    grid, f = method(kind, feats)
    held = [[r for r in anchors if r["cf_contest"] == c] for c in sorted({r["cf_contest"] for r in anchors})]
    score = {p: sum(float(np.sum((f(_purged_train(anchors, h), h, p) - [r["cf"] for r in h]) ** 2))
                    for h in held) for p in grid}
    return f, min(grid, key=lambda p: (score[p], grid.index(p))), grid


def anchor_loco(anchors, kind, feats):
    if kind == "affine":
        f, _, _ = calibrator(kind, feats, anchors)
        pred = np.zeros(len(anchors))
        for c in sorted({r["cf_contest"] for r in anchors}):
            idx = [i for i, r in enumerate(anchors) if r["cf_contest"] == c]
            held = [anchors[i] for i in idx]
            pred[idx] = f(_purged_train(anchors, held), held, None)
        return pred
    return loco(anchors, kind, feats)[0]


class Experiment:
    def __init__(self):
        self.ds, _uf, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
        ds = self.ds
        _t, _p, _y, self.rho = survival._survival_observations(ds)
        self.tau = np.nan_to_num(ds.obs_tau).astype(float)
        self.ctx = row_context(ds, raw_by_contest())
        self.mixed = set(mixed_boards(ds, self.ctx).tolist())
        records = json.load(open(os.path.join(ROOT, "problem_ratings_survival.json"), encoding="utf-8"))
        binary = json.load(open(os.path.join(ROOT, "problem_ratings_b.json"), encoding="utf-8"))
        self.anchors = with_binary(build_anchor_table(records, binary), binary)
        for r in self.anchors:
            r["ref_solve_rate"] = float(reference_rate([r["b_bin"]])[0])
        self.anchor_by_key = {(r["contest_id"], r["problem_label"]): r for r in self.anchors}

    def outside_abilities(self):
        """Per fold: the fold's contests and ability fits on the other contests.

        ``all``: binary and survival abilities and seen-teams from every other
        contest. ``A``/``B``: the other contests split in two; selection uses
        binary A, fixed abilities come from B, so selection noise is independent
        of the abilities used to measure the field.
        """
        ds = self.ds
        order = np.random.default_rng(SEED).permutation(len(ds.contests))
        cell_contest = ds.contest_of_row[ds.obs_row]
        team = ds.team_of_row[ds.obs_row]
        y = ds.obs_y.astype(float)

        def fits(mask, with_survival=True):
            th_b, _b, _ = model.fit(ds, verbose=False, obs=(team[mask], ds.obs_prob[mask], y[mask]))
            th_s = (survival.fit(ds, verbose=False, obs=(team[mask], ds.obs_prob[mask], y[mask],
                                                          self.rho[mask]))[0] if with_survival else None)
            seen = np.zeros(len(ds.teams), bool)
            seen[team[mask]] = True
            return th_b, th_s, seen

        for f in range(FOLDS):
            contests = order[f::FOLDS]
            others = order[np.isin(order, contests, invert=True)]
            train = ~np.isin(cell_contest, contests)
            in_a = np.isin(cell_contest, others[0::2])
            out = {"all": fits(train), "A": fits(in_a, False), "B": fits(train & ~in_a)}
            log(f"fold {f}: outside fits done")
            yield contests, out

    def split_teams(self, rows, rng):
        """(target rows, pool teams, rows-of-teams function): 30% of the board's teams are the target."""
        team = self.ds.team_of_row[rows]
        teams = rng.permutation(np.unique(team))
        n_target = int(round(TARGET * len(teams)))

        def rows_of(ts):
            return rows[np.isin(team, ts)]
        return rows_of(teams[:n_target]), teams[n_target:], rows_of

    def samples(self, rows, th_b, rng):
        """Named training row sets from one board's linked rows, drawn by team; the target is fixed per board."""
        target, pool, rows_of = self.split_teams(rows, rng)
        order = pool[np.argsort(th_b[pool], kind="stable")]
        half = len(pool) // 2
        out = {"full": rows_of(pool), "weak": rows_of(order[:half]), "strong": rows_of(order[-half:])}
        for s in range(SEEDS):
            perm = rng.permutation(pool)
            out[f"random_a{s}"], out[f"random_b{s}"] = rows_of(perm[:half]), rows_of(perm[half:2 * half])
            out[f"quarter{s}"] = rows_of(rng.permutation(pool)[:max(len(pool) // 4, 1)])
        if self.ds.contest_of_row[rows[0]] in self.mixed:
            event_row = (self.ctx == 0) & self.ds.official_of_row
            kinds = {}
            for r in rows_of(pool):
                kinds.setdefault(self.ds.team_of_row[r], set()).add(
                    "event" if event_row[r] else "mirror" if self.ctx[r] > 0 else "other")
            event = np.array([t for t, k in kinds.items() if k == {"event"}])
            mirror = np.array([t for t, k in kinds.items() if k == {"mirror"}])
            n = min(len(event), len(mirror))
            if n >= MIN_CONTEXT:
                out["event"] = rows_of(rng.permutation(event)[:n])
                out["mirror"] = rows_of(rng.permutation(mirror)[:n])
        return target, out

    def board_rho(self, board_cells, target):
        """Survival exposure of the board's cells, its window set by the latest solve outside ``target``."""
        ds = self.ds
        solved = ds.obs_y[board_cells]
        window = solved & ~np.isin(ds.obs_row[board_cells], target)
        tc = self.tau[board_cells][window].max() if window.any() else survival.DEFAULT_TC
        return np.where(solved, self.tau[board_cells] / tc, 1.0)

    def board_rows(self, contest, board_cells, rho, sample_rows, th_b, th_s):
        """DE feature rows for every problem of ``contest`` measured on ``sample_rows``.

        ``rho`` is the survival exposure aligned with ``board_cells``.
        """
        ds = self.ds
        keep = np.isin(ds.obs_row[board_cells], sample_rows)
        cells, rho = board_cells[keep], rho[keep]
        prob, y = ds.obs_prob[cells], ds.obs_y[cells].astype(float)
        team = ds.team_of_row[ds.obs_row[cells]]
        b_bin, _ = refit_b(prob, y, th_b[team], n_problems=len(ds.problems))
        b_sur, se_sur = refit_b(prob, y, th_s[team], rho=rho, n_problems=len(ds.problems))
        solved = np.bincount(prob, y, len(ds.problems))
        probs = np.flatnonzero(ds.contest_of_problem == contest)
        ref = reference_rate(b_bin[probs])
        out = []
        for p, rr in zip(probs, ref):
            cid, label, pid, _name = ds.problems[p]
            row = {"problem": int(p), "contest_id": int(cid), "problem_label": label,
                   "canonical_task": f"qoj:{pid}", "raw_b": float(b_sur[p]), "b_bin": float(b_bin[p]),
                   "binary_minus_survival": float(b_bin[p] - b_sur[p]),
                   "conditional_fit_se": float(se_sur[p]), "solve_rate": float(solved[p] / len(sample_rows)),
                   "log_field_size": float(np.log1p(len(sample_rows))), "ref_solve_rate": float(rr),
                   "solved": int(solved[p]), "field": int(len(sample_rows))}
            anchor = self.anchor_by_key.get((int(cid), label))
            if anchor:
                row.update(cf=anchor["cf"], cf_contest=anchor["cf_contest"], row_id=anchor["row_id"])
            out.append(row)
        return out, b_bin, b_sur

    def target_loss(self, board_cells, target, b_bin, b_sur, th_b, th_s):
        ds = self.ds
        cells = board_cells[np.isin(ds.obs_row[board_cells], target)]
        y = ds.obs_y[cells].astype(float)
        team, prob = ds.team_of_row[ds.obs_row[cells]], ds.obs_prob[cells]
        p_bin = elo.pi(th_b[team], b_bin[prob])
        p_sur = 1 - np.exp(-survival.LN2 * np.exp((th_s[team] - b_sur[prob]) / elo.S))
        out = {}
        for name, p in (("binary", p_bin), ("survival", p_sur)):
            p = np.clip(p, 1e-9, 1 - 1e-9)
            out[name] = float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        out["cells"] = int(len(cells))
        return out

    def independent(self, c, board_cells, rows, sel_b, th_b, th_s):
        """Strong/weak halves of teams chosen by ``sel_b``, measured with independent abilities ``th_b``/``th_s``."""
        rng = np.random.default_rng([SEED, int(c), 1])
        target, pool, rows_of = self.split_teams(rows, rng)
        rho = self.board_rho(board_cells, target)
        order = pool[np.argsort(sel_b[pool], kind="stable")]
        half = len(pool) // 2
        samples = {"weak": rows_of(order[:half]), "strong": rows_of(order[-half:])}
        for s in range(SEEDS):
            perm = rng.permutation(pool)
            samples[f"random_a{s}"], samples[f"random_b{s}"] = rows_of(perm[:half]), rows_of(perm[half:2 * half])
        out = {"features": {}, "target": {}, "rows": int(len(rows))}
        for name, sample in samples.items():
            feats, b_bin, b_sur = self.board_rows(c, board_cells, rho, sample, th_b, th_s)
            out["features"][name] = feats
            out["target"][name] = self.target_loss(board_cells, target, b_bin, b_sur, th_b, th_s)
        return out

    def measure(self):
        ds = self.ds
        boards = []
        for contests, fits in self.outside_abilities():
            th_b, th_s, seen = fits["all"]
            sel_a, _none, seen_a = fits["A"]
            th_bb, th_sb, seen_b = fits["B"]
            for c in contests:
                rows = np.flatnonzero((ds.contest_of_row == c) & seen[ds.team_of_row])
                if len(rows) < MIN_LINKED:
                    continue
                board_cells = np.flatnonzero(ds.contest_of_row[ds.obs_row] == c)
                rng = np.random.default_rng([SEED, int(c)])
                target, samples = self.samples(rows, th_b, rng)
                rho = self.board_rho(board_cells, target)
                entry = {"contest": int(c), "contest_id": int(ds.contests[c]), "linked_rows": int(len(rows)),
                         "mixed": int(c) in self.mixed, "features": {}, "target": {}}
                for name, sample in samples.items():
                    feats, b_bin, b_sur = self.board_rows(c, board_cells, rho, sample, th_b, th_s)
                    entry["features"][name] = feats
                    entry["target"][name] = self.target_loss(board_cells, target, b_bin, b_sur, th_b, th_s)
                both = np.flatnonzero((ds.contest_of_row == c) & (seen_a & seen_b)[ds.team_of_row])
                if len(both) >= MIN_LINKED:
                    entry["independent"] = self.independent(c, board_cells, both, sel_a, th_bb, th_sb)
                boards.append(entry)
        return boards

    def calibrate(self, boards):
        """Add every calibrator's CF to every feature row (frozen on all anchors and contest-held-out)."""
        rows = [r for e in boards for feats in e["features"].values() for r in feats]
        rows += [r for e in boards if "independent" in e for feats in e["independent"]["features"].values()
                 for r in feats]
        for name, (kind, feats) in CALIBRATORS.items():
            f, setting, grid = calibrator(kind, feats, self.anchors)
            pred = f(self.anchors, rows, setting)
            for r, v in zip(rows, pred):
                r[name] = float(np.clip(v, elo.LO, elo.HI))
            for c in sorted({r["cf_contest"] for r in self.anchors}):
                held = [r for r in self.anchors if r["cf_contest"] == c]
                train = _purged_train(self.anchors, held)
                if kind == "affine":
                    p = None
                else:
                    p = nested(self.anchors, held, grid, f)[1]
                targets = [r for r in rows if r.get("cf_contest") == c]
                if targets:
                    for r, v in zip(targets, f(train, targets, p)):
                        r[name + "_held_out"] = float(np.clip(v, elo.LO, elo.HI))


def de_decomposition(anchors, boards):
    """Mean DE change per feature for each contrast: DE(b with feature f taken from a) - DE(b).

    The frozen DE map is linear in each (separately clipped) feature, so the
    contributions add up to the whole DE difference.
    """
    f, setting, _grid = calibrator("clip", DE, anchors)
    out = {}
    for label, a, b, key in (("strong_minus_weak", "strong", "weak", None),
                             ("strong_minus_weak_independent_selection", "strong", "weak", "independent"),
                             ("full_minus_quarter", "full", "quarter{s}", None),
                             ("mirror_minus_event", "mirror", "event", None)):
        pairs = []
        for e in boards:
            feats = e["features"] if key is None else e.get(key, {}).get("features", {})
            for s in range(SEEDS):
                ka, kb = a.format(s=s), b.format(s=s)
                if ka in feats and kb in feats:
                    pairs += [(x, z) for x, z in zip(feats[ka], feats[kb])
                              if 0 < x["solved"] < x["field"] and 0 < z["solved"] < z["field"]]
                if "{s}" not in a + b:
                    break
        if not pairs:
            continue
        xs, zs = [x for x, _ in pairs], [z for _, z in pairs]
        base = f(anchors, zs, setting)
        res = {"total": float(np.mean(f(anchors, xs, setting) - base)), "problems": len(pairs)}
        for feat in DE:
            moved = [dict(z, **{feat: x[feat]}) for x, z in pairs]
            res[feat] = float(np.mean(f(anchors, moved, setting) - base))
        res["mean_feature_change"] = {feat: float(np.mean([x[feat] - z[feat] for x, z in pairs])) for feat in DE}
        out[label] = res
    return out


JOINT_CONDITIONS = ("full", "half_a", "half_b", "event_only", "mirror_heavy", "event_small")


def joint_condition_rows(ds, ctx, boards, rng):
    """Rows kept on the anchor boards under each condition (by team, ID-based composition only)."""
    keep = {name: [] for name in JOINT_CONDITIONS}
    for c in boards:
        rows = np.flatnonzero(ds.contest_of_row == c)
        team = ds.team_of_row[rows]
        teams = rng.permutation(np.unique(team))
        half = set(teams[: len(teams) // 2].tolist())
        in_a = np.array([t in half for t in team])
        event = (ctx[rows] == 0) & ds.official_of_row[rows]
        mirror = ctx[rows] > 0
        n = int(mirror.sum())
        heavy = np.r_[rows[mirror], rng.permutation(rows[event])[:n]]
        keep["full"].append(rows)
        keep["half_a"].append(rows[in_a])
        keep["half_b"].append(rows[~in_a])
        keep["event_only"].append(rows[event])
        keep["mirror_heavy"].append(heavy)
        keep["event_small"].append(rng.permutation(rows[event])[:len(heavy)])
    return {k: np.concatenate(v) for k, v in keep.items()}


def joint_refit_check(ex):
    """Deployed-like check: refit the whole joint model with the anchor boards cut down, then calibrate.

    Unlike the fixed-ability experiment, the board's unlinked teams are estimated
    jointly (with the shipped prior), as in the shipped fit. Conditions change
    every anchor board at once; DE features come from the refit, exactly as the
    shipped feature builder defines them. Calibrators are contest-held-out.
    """
    ds = ex.ds
    pids = {(int(cid), label): p for p, (cid, label, _pid, _n) in enumerate(ds.problems)}
    cidx = {cid: i for i, cid in enumerate(ds.contests)}
    boards = sorted({cidx[r["contest_id"]] for r in ex.anchors})
    on_board = np.isin(ds.contest_of_row, boards)
    kept = joint_condition_rows(ds, ex.ctx, boards, np.random.default_rng(SEED))
    team, y = ds.team_of_row[ds.obs_row], ds.obs_y.astype(float)
    fitted = {}
    for name, rows in kept.items():
        row_kept = ~on_board.copy()
        row_kept[rows] = True
        cells = row_kept[ds.obs_row]
        _t, _p, _y, rho = survival._survival_observations(ds, duration_mask=cells)
        th_b, b_bin, _ = model.fit(ds, verbose=False, obs=(team[cells], ds.obs_prob[cells], y[cells]))
        th_s, b_sur, _ = survival.fit(ds, verbose=False,
                                      obs=(team[cells], ds.obs_prob[cells], y[cells], rho[cells]))
        lam = survival.LN2 * np.exp((th_s[team[cells]] - b_sur[ds.obs_prob[cells]]) / elo.S) * rho[cells]
        se = 1 / np.sqrt(np.bincount(ds.obs_prob[cells], lam, len(b_sur)) / elo.S ** 2 + 1 / SIGMA_B ** 2)
        solved = np.bincount(ds.obs_prob[cells], y[cells], len(b_sur))
        field = np.bincount(ds.contest_of_row[row_kept], None, len(ds.contests))
        out = []
        for c in boards:
            for p in np.flatnonzero(ds.contest_of_problem == c):
                cid, label, pid, _n = ds.problems[p]
                f = int(field[c])
                row = {"problem": int(p), "contest_id": int(cid), "problem_label": label,
                       "canonical_task": f"qoj:{pid}", "raw_b": float(b_sur[p]), "b_bin": float(b_bin[p]),
                       "binary_minus_survival": float(b_bin[p] - b_sur[p]), "conditional_fit_se": float(se[p]),
                       "solve_rate": float(solved[p] / f), "log_field_size": float(np.log1p(f)),
                       "ref_solve_rate": float(reference_rate([b_bin[p]])[0]), "solved": int(solved[p]), "field": f}
                anchor = ex.anchor_by_key.get((int(cid), label))
                if anchor:
                    row.update(cf=anchor["cf"], cf_contest=anchor["cf_contest"], row_id=anchor["row_id"])
                out.append(row)
        fitted[name] = out
        log(f"joint refit {name} done")
    ex.calibrate([{"features": fitted}])
    full = fitted["full"]
    shipped = {(r["contest_id"], r["problem_label"]): r for r in ex.anchors}
    check = max(abs(r[f] - shipped[(r["contest_id"], r["problem_label"])][f]) for r in full if "cf" in r
                for f in ("raw_b", "binary_minus_survival", "conditional_fit_se", "solve_rate", "log_field_size"))
    res = {"anchor_boards": len(boards), "rows_kept": {k: int(len(v)) for k, v in kept.items()},
           "full_refit_max_feature_difference_from_shipped": float(check), "conditions": {}}
    for name, rows in fitted.items():
        anchors = [r for r in rows if "cf" in r]
        err = {n: np.array([r[n + "_held_out"] - r["cf"] for r in anchors]) for n in CALIBRATORS}
        group = np.array([r["cf_contest"] for r in anchors])
        entry = {}
        for n in CALIBRATORS:
            entry[n] = {"rmse": float(np.sqrt(np.mean(err[n] ** 2))), "mean_error": float(np.mean(err[n])),
                        "mean_shift_vs_full_all_board_problems": float(np.mean([x[n] - z[n] for x, z in zip(rows, full)]))}
            if n != "DE_clip":
                entry[n]["rmse_minus_DE_clip"] = _contest_bootstrap(err[n], err["DE_clip"], group)
        entry["mean_solve_rate"] = float(np.mean([r["solve_rate"] for r in rows]))
        res["conditions"][name] = entry
    return res


def _contest_bootstrap(ea, eb, group, n=5000):
    """RMSE(a) - RMSE(b) with a paired 95% interval over resampled CF contests."""
    contests = sorted(set(group))
    idx = [np.flatnonzero(group == c) for c in contests]
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(n):
        k = np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])
        draws.append(np.sqrt(np.mean(ea[k] ** 2)) - np.sqrt(np.mean(eb[k] ** 2)))
    return [float(np.sqrt(np.mean(ea ** 2)) - np.sqrt(np.mean(eb ** 2))),
            *map(float, np.percentile(draws, [2.5, 97.5]))]


def _diff_stats(pairs):
    d = np.array(pairs)
    if not len(d):
        return None
    return {"mean": float(d.mean()), "median": float(np.median(d)), "rms": float(np.sqrt(np.mean(d ** 2))),
            "problems": int(len(d))}


def summarize(boards):
    names = list(CALIBRATORS) + ["latent_binary_b", "latent_survival_b"]

    def value(r, name):
        return r["b_bin"] if name == "latent_binary_b" else r["raw_b"] if name == "latent_survival_b" else r[name]

    def interior(r):
        return 0 < r["solved"] < r["field"]

    def keys(name):
        return [name.format(s=s) for s in range(SEEDS)] if "{s}" in name else [name] * SEEDS

    def contrast(a, b, feature_sets):
        """a minus b per problem (both fields solved some but not all); seeded names pair by seed."""
        out = {}
        for name in names:
            pairs = []
            for feats in feature_sets:
                for ka, kb in sorted(set(zip(keys(a), keys(b)))):
                    pairs += [value(x, name) - value(z, name)
                              for x, z in zip(feats[ka], feats[kb]) if interior(x) and interior(z)]
            out[name] = _diff_stats(pairs)
        return out

    mixed = [e for e in boards if "event" in e["features"]]
    main = [e["features"] for e in boards]
    indep = [e["independent"]["features"] for e in boards if "independent" in e]
    out = {"boards": len(boards), "mixed_boards_with_context_samples": len(mixed),
           "boards_with_independent_selection": len(indep),
           "linked_rows": int(sum(e["linked_rows"] for e in boards)),
           "strong_minus_weak": contrast("strong", "weak", main),
           "random_half_a_minus_b (noise floor)": contrast("random_a{s}", "random_b{s}", main),
           "strong_minus_weak_independent_selection": contrast("strong", "weak", indep),
           "independent_random_half_a_minus_b": contrast("random_a{s}", "random_b{s}", indep),
           "full_minus_quarter": contrast("full", "quarter{s}", main),
           "mirror_minus_event": contrast("mirror", "event", [e["features"] for e in mixed]),
           "solve_rate_strong_minus_weak": _diff_stats(
               [x["solve_rate"] - z["solve_rate"] for e in boards
                for x, z in zip(e["features"]["strong"], e["features"]["weak"])])}
    # latent log loss on each board's fixed target rows; seeded fields are averaged over seeds
    tl = {}
    for kind in ("full", "strong", "weak", "random_a{s}", "quarter{s}", "event", "mirror"):
        sums = np.zeros(3)
        for e in boards:
            if kind in e["target"] or "{s}" in kind:
                ks = sorted(set(keys(kind)))
                sums += np.mean([[e["target"][k]["binary"], e["target"][k]["survival"], e["target"][k]["cells"]]
                                 for k in ks], 0)
        tl[kind.replace("{s}", "")] = {"binary": sums[0] / sums[2], "survival": sums[1] / sums[2],
                                       "cells": int(round(sums[2]))}
    out["target_log_loss"] = tl
    # event and mirror fields exist only on mixed boards: compare them with the full and random fields there
    tlm = {}
    for kind in ("full", "random_a{s}", "event", "mirror"):
        sums = np.zeros(3)
        for e in mixed:
            ks = sorted(set(keys(kind)))
            sums += np.mean([[e["target"][k]["binary"], e["target"][k]["survival"], e["target"][k]["cells"]]
                             for k in ks], 0)
        tlm[kind.replace("{s}", "")] = {"binary": sums[0] / sums[2], "survival": sums[1] / sums[2],
                                        "cells": int(round(sums[2]))} if sums[2] else None
    out["target_log_loss_mixed_boards"] = tlm
    # anchor CF RMSE by field, contest-held-out calibrators; differences vs DE by paired CF-contest bootstrap
    anchor = {}
    for label, feature_sets, kind in (
            [(k.replace("{s}", ""), main, k) for k in
             ("full", "strong", "weak", "random_a{s}", "quarter{s}", "event", "mirror")]
            + [("independent_" + k.replace("{s}", ""), indep, k) for k in ("strong", "weak", "random_a{s}")]):
        rows = [r for feats in feature_sets for key in sorted(set(keys(kind))) if key in feats
                for r in feats[key] if "cf" in r]
        if not rows:
            continue
        err = {n: np.array([r[n + "_held_out"] - r["cf"] for r in rows]) for n in CALIBRATORS}
        group = np.array([r["cf_contest"] for r in rows])
        res = {"anchors": len({r["row_id"] for r in rows}), "cf_contests": len(set(group))}
        for n in CALIBRATORS:
            res[n] = {"rmse": float(np.sqrt(np.mean(err[n] ** 2))), "mean_error": float(np.mean(err[n]))}
            if n != "DE_clip":
                res[n]["rmse_minus_DE_clip"] = _contest_bootstrap(err[n], err["DE_clip"], group)
        anchor[label] = res
    out["anchor_cf_by_field_held_out_calibrators"] = anchor
    return out


def run():
    ex = Experiment()
    from .context_fit import provenance
    out = {"scope": "Research only; abilities from contest folds that exclude the board; dev anchors",
           "sha256": provenance(["arch_b/field_transport.py", "arch_b/context_fit.py", "arch_b/model.py",
                                 "arch_b/survival.py", "arch_b/de_release_audit.py",
                                 "output/problem_ratings_survival.json", "output/problem_ratings_b.json",
                                 "data/cf_problemset.json", "data/cf_team_contests.txt"]),
           "anchor_nested_loco": {}}
    preds = {}
    for name, (kind, feats) in CALIBRATORS.items():
        preds[name] = anchor_loco(ex.anchors, kind, feats)
        out["anchor_nested_loco"][name] = rmse(preds[name], ex.anchors)
    out["anchor_nested_loco"]["DE_reference_minus_DE_clip"] = contest_bootstrap(
        ex.anchors, preds["DE_reference"], preds["DE_clip"])
    log(f"anchor LOCO {out['anchor_nested_loco']}")
    boards = ex.measure()
    ex.calibrate(boards)
    out.update(summarize(boards))
    out["DE_drift_by_feature"] = de_decomposition(ex.anchors, boards)
    out["joint_refit_anchor_boards"] = joint_refit_check(ex)
    out["per_board"] = [{"contest_id": e["contest_id"], "linked_rows": e["linked_rows"], "mixed": e["mixed"],
                         "strong_minus_weak_mean": {n: float(np.mean([x[n] - z[n] for x, z in zip(
                             e["features"]["strong"], e["features"]["weak"])])) for n in CALIBRATORS}}
                        for e in boards]
    return out


def main():
    out = run()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({k: v for k, v in out.items() if k != "per_board"}, indent=2))


if __name__ == "__main__":
    main()
