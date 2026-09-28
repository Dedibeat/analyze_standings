import csv
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from arch_b import tabfm_gold as tg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_tabfm_gold_data as build  # noqa: E402


class TableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.meta = tg.load()

    def test_within_ai_predict_limits_and_one_row_per_team(self):
        self.assertLessEqual(len(self.meta["features"]), 50)
        with open(ROOT / "output" / "quota_teams.csv", encoding="utf-8") as f:
            self.assertEqual(len(self.rows), sum(1 for _ in csv.DictReader(f)))
        self.assertEqual(len({r["row_id"] for r in self.rows}), len(self.rows))
        self.assertEqual({r["gold"] for r in self.rows}, {"true", "false"})

    def test_training_queries_select_only_features_and_the_label(self):
        sql = (tg.DATA / "predict.sql").read_text()
        names = {f["name"] for f in self.meta["features"]}
        pre = names - set(self.meta["tiers"]["registration"])
        blocks = re.findall(r"\(SELECT\n([^()]*?)\n\s+FROM `PROJECT\.DATASET\.teams` WHERE season IN", sql, re.S)
        self.assertEqual(len(blocks), 4)
        for block in blocks:
            cols = {c.strip() for c in block.split(",")}
            self.assertIn("gold", cols)
            self.assertIn(cols - {"gold"}, (names, pre))
        schema = {c["name"] for c in json.loads((tg.DATA / "schema.json").read_text())}
        self.assertLessEqual(names, schema)

    def test_history_uses_only_earlier_contests_and_previous_season(self):
        entry = dict(school="s", team="t", members={"a", "b", "c"}, level=3, rank_pct=0.01)
        by_school = {("2025", "s"): [dict(entry, date="2025-10-01"), dict(entry, date="2025-11-01", level=1)],
                     ("2024", "s"): [dict(entry, date="2024-11-01")]}
        team = dict(school="s", team="t", members={"a", "b", "x"})
        h = build.history(team, by_school, "2025", "2025-11-01")
        self.assertEqual(h["earlier_regionals"], 1)  # the same-day contest is not "earlier"
        self.assertEqual(h["members_prev_golds"], 2)
        self.assertEqual(h["school_prev_golds"], 1)

    def test_scoring_requires_every_held_out_row(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("row_id,p_gold\n")
            for r in self.rows[:10]:
                f.write(f"{r['row_id']},0.1\n")
        with self.assertRaises(ValueError):
            tg.read_predictions(f.name, self.rows, self.meta)

    def test_evaluate_ranks_an_informative_prediction_above_the_reference(self):
        preds = {}
        for split, s in self.meta["splits"].items():
            test = [r for r in self.rows if r["season"] == s["test"]]
            rate = np.mean([r["gold"] == "true" for r in test])
            preds[split] = {"online_only": {r["row_id"]: rate for r in test},
                            "tabfm": {r["row_id"]: 0.6 if r["gold"] == "true" else 0.05 for r in test}}
        res = tg.evaluate(self.rows, self.meta, preds)
        for v in res.values():
            self.assertLess(v["models"]["tabfm"]["delta_vs_online_only"], 0)


if __name__ == "__main__":
    unittest.main()
