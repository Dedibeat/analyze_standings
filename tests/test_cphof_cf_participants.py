import unittest

from scripts.cphof_cf_participants import (
    _parse_cphof_date,
    build_artifact,
    parse_codeforces_handle,
    parse_cphof_standings,
    rating_before,
)


class CphofCfParticipantsTest(unittest.TestCase):
    def test_parses_roster_and_explicit_profile(self):
        standings = """
        <table><tr><td><span>Date:</span></td><td>Sept. 4, 2025</td></tr></table>
        <table><thead><tr><th>Rank</th><th>Country</th><th>Team</th>
        <th>Score</th><th>Penalty</th><th>Prize</th></tr></thead>
        <tr><td>2</td><td><a href="/country/JPN">Japan</a></td>
        <td><div><a href="/university/Tokyo">The University of Tokyo</a>
        <span>(Screenwalkers):</span></div>
        <div><a href="/profile/icpc:Daiki%20Kodama">Daiki Kodama</a>,
        <a href="/profile/icpc:Hirotaka%20Yoneda">Hirotaka Yoneda</a></div></td>
        <td>10</td><td>1116</td><td></td></tr></table>
        """
        contest = parse_cphof_standings(
            standings, 2025, "https://cphof.org/standings/icpc/2025")
        self.assertEqual(contest["date"], "Sept. 4, 2025")
        self.assertEqual(contest["date_cutoff_timestamp"], 1756944000)
        self.assertEqual(contest["teams"][0]["team_name"], "Screenwalkers")
        self.assertEqual(
            contest["teams"][0]["members"][0]["name"], "Daiki Kodama")

        profile = """
        <a href="https://atcoder.jp/users/KoD">KoD at AtCoder</a>
        <a href="https://codeforces.com/profile/Kodaman">Kodaman at Codeforces</a>
        """
        self.assertEqual(parse_codeforces_handle(profile), "Kodaman")
        self.assertEqual(_parse_cphof_date("April 18, 2024"), 1713398400)

    def test_rating_before_is_time_causal(self):
        history = [
            {"newRating": 1200, "ratingUpdateTimeSeconds": 100},
            {"newRating": 1400, "ratingUpdateTimeSeconds": 200},
            {"newRating": 1800, "ratingUpdateTimeSeconds": 300},
        ]
        self.assertIsNone(rating_before(history, 99))
        self.assertEqual(
            rating_before(history, 250),
            {
                "rating": 1400,
                "rated_contest_count": 2,
                "rating_update_time_seconds": 200,
            },
        )

    def test_requires_explicit_cphof_codeforces_link(self):
        contests = [{
            "contest_id": 1,
            "contest_name": "Regional",
            "year": 2024,
            "region": "Test",
            "standings": [{
                "team_id": "one",
                "team_name": "Team",
                "affiliation": "University",
                "members": ["Daiki Kodama", "Hirotaka Yoneda"],
            }],
        }]
        cphof = [{
            "year": 2025,
            "date": "Sept. 4, 2025",
            "date_cutoff_timestamp": 1756944000,
            "source_url": "https://cphof.org/standings/icpc/2025",
            "teams": [{
                "rank": 2,
                "country": "Japan",
                "institution": "University",
                "team_name": "Screenwalkers",
                "members": [{
                    "name": "Daiki Kodama",
                    "profile_url": "https://cphof.org/profile/daiki",
                }, {
                    "name": "Hirotaka Yoneda",
                    "profile_url": "https://cphof.org/profile/hirotaka",
                }],
            }],
        }]
        history = [{"newRating": 3000, "ratingUpdateTimeSeconds": 100}]
        accepted = build_artifact(
            contests, cphof,
            {"https://cphof.org/profile/daiki": "Kodaman"},
            {"Kodaman": history}, "2026-01-01T00:00:00+00:00")
        self.assertEqual(accepted["matching"]["explicit_profile_identities"], 1)
        self.assertEqual(
            accepted["matching"]["roster_corroborated_tagged_appearances"], 1)

        rejected = build_artifact(
            contests, cphof,
            {"https://cphof.org/profile/daiki": None},
            {}, "2026-01-01T00:00:00+00:00")
        self.assertEqual(rejected["matching"]["explicit_profile_identities"], 0)
        self.assertEqual(
            rejected["rejected_candidates"][0]["rejection_reason"],
            "no_explicit_codeforces_profile")


if __name__ == "__main__":
    unittest.main()
