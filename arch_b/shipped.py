"""Shared production hierarchical binary fit with solve-time slices.

Regenerate problem artifacts with ``python -m arch_b.hier_time release`` before
running the viewers. All product exports use this fit and the same affine map.
"""
from functools import lru_cache
import json

import numpy as np

from arch_a import elo
from .hier_time import RELEASE_META, fit
from .joint import load_joint_dataset
from .run import MIN_SOLVE_HOURS


@lru_cache(maxsize=1)
def release_metadata():
    return json.loads(RELEASE_META.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def shipped_fit():
    ds, uf, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    meta = release_metadata()
    setting = meta["setting"]
    res = fit(ds, (setting["bins"], setting["time_weight"], setting["skip_partial"]))
    return ds, res["theta"], res["b"], res, uf


def to_cf(x):
    meta = release_metadata()
    return float(np.clip(meta["map"]["slope"] * x + meta["map"]["intercept"], elo.LO, elo.HI))
