import unittest

from pairwise_tuning import count_url, generate_url


class VertexUrlTest(unittest.TestCase):
    def test_global_publisher_url(self):
        url = generate_url("project-id", "gemini-3.5-flash", "global")
        self.assertTrue(url.startswith("https://aiplatform.googleapis.com/"))
        self.assertIn("/locations/global/", url)

    def test_multi_region_uses_rep_hostname(self):
        for location in ("us", "eu"):
            with self.subTest(location=location):
                expected = f"https://aiplatform.{location}.rep.googleapis.com/"
                self.assertTrue(
                    count_url("project-id", location, "gemini-3.5-flash").startswith(
                        expected
                    )
                )
                self.assertTrue(
                    generate_url(
                        "project-id", "gemini-3.5-flash", location
                    ).startswith(expected)
                )


if __name__ == "__main__":
    unittest.main()
