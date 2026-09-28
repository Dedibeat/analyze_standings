import collections
import csv
import json
import unittest
from pathlib import Path

from arch_b.online_gold import norm_name, norm_school
from scripts.build_ec_online_data import _segment

DATA = Path(__file__).resolve().parent.parent / "data" / "ec_online"


def rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class SegmentTest(unittest.TestCase):
    def test_wrapped_cell_goes_to_the_row_it_is_centred_on(self):
        # rows at y=10, 30, 50; the middle cell wraps onto y=25 and y=35
        lines = [(10, "a"), (25, "b1"), (35, "b2"), (50, "c")]
        blocks = _segment(lines, [10, 30, 50])
        self.assertEqual([[t for _, t in b] for b in blocks], [["a"], ["b1", "b2"], ["c"]])


class OnlineDataTest(unittest.TestCase):
    def test_team_ranks_are_monotone_and_zero_solve_teams_unranked(self):
        by_round = collections.defaultdict(list)
        for r in rows("online_teams.csv"):
            by_round[(r["season"], r["round"])].append(r)
        self.assertEqual(len(by_round), 10)
        for key, rs in by_round.items():
            ranks = [int(r["rank"]) for r in rs if r["rank"]]
            self.assertEqual(ranks, sorted(ranks), key)
            self.assertTrue(all(int(r["solved"]) == 0 for r in rs if not r["rank"]), key)

    def test_2026_team_counts_and_num_combined_rank(self):
        teams = [r for r in rows("online_teams.csv") if r["season"] == "2026"]
        self.assertEqual(sum(r["round"] == "1" for r in teams), 2486)
        self.assertEqual(sum(r["round"] == "2" for r in teams), 2480)
        combined = {r["school"]: int(r["rank"]) for r in rows("online_schools.csv")
                    if r["season"] == "2026" and r["table"] == "combined"}
        num = [s for s in combined if s.startswith("蒙古国立大学")]
        self.assertEqual([combined[s] for s in num], [128])

    def test_every_ranked_school_has_a_combined_rank(self):
        # 2026 PDFs print 西 as U+2EC4 etc.; unfolded, those schools lost their slots
        combined = collections.defaultdict(set)
        for r in rows("online_schools.csv"):
            if r["table"] == "combined":
                combined[r["season"]].add(r["school"])
        for r in rows("online_teams.csv"):
            if r["rank"]:
                self.assertIn(r["school"], combined[r["season"]], (r["season"], r["school"]))

    def test_every_ranked_2025_2026_team_has_a_pta_roster(self):
        def key(r):
            return r["season"], r["round"], norm_school(r["school"]), norm_name(r["team"])
        roster = {key(r) for r in rows("online_rosters.csv")}
        missing = [key(r) for r in rows("online_teams.csv") if r["season"] in ("2025", "2026")
                   and key(r) not in roster]
        self.assertEqual(missing, [])

    def test_rosters_mostly_have_three_members(self):
        rs = rows("online_rosters.csv")
        full = sum(len(r["members"].split("|")) == 3 for r in rs)
        self.assertGreater(full / len(rs), 0.9)


class RegionalDataTest(unittest.TestCase):
    def test_medal_counts_match_board_for_2024_2025(self):
        reg = rows("regional_teams.csv")
        count = collections.Counter((r["season"], r["site"], r["medal"]) for r in reg if r["medal"])
        self.assertEqual(count[("2025", "shanghai", "gold")], 30)
        self.assertEqual(count[("2024", "shenyang", "gold")], 30)
        self.assertEqual(count[("2025", "wuhan", "gold")], 45)

    def test_star_teams_are_unranked(self):
        reg = rows("regional_teams.csv")
        self.assertTrue(all(r["official_rank"] == "" for r in reg if r["official"] == "0"))
        self.assertTrue(all(r["medal"] == "" for r in reg if r["official"] == "0"))


class SlotRulesTest(unittest.TestCase):
    def test_bands_are_ordered_and_disjoint(self):
        for rule in json.loads((DATA / "slot_rules.json").read_text())["rules"]:
            bands = rule.get("online_bands") or []
            for (lo1, hi1, _), (lo2, _, _) in zip(bands, bands[1:]):
                self.assertEqual(lo2, hi1 + 1, rule["site"])
            self.assertTrue(all(lo <= hi for lo, hi, _ in bands))

    def test_every_2026_site_is_encoded(self):
        sites = {r["site"] for r in json.loads((DATA / "slot_rules.json").read_text())["rules"]
                 if r["season"] == 2026}
        self.assertEqual(sites, {"xian", "chengdu", "wuhan", "nanjing", "shenyang",
                                 "shanghai", "nanchang", "hongkong"})


if __name__ == "__main__":
    unittest.main()
