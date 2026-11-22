import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from scripts import qoj_auth


class QOJAuthTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.data = Path(directory)
        self.enterContext(patch.object(qoj_auth, "DATA", self.data))
        self.client = qoj_auth.QOJSession()
        self.addCleanup(self.client.close)
        self.request = self.enterContext(patch.object(self.client.session, "request"))
        self.enterContext(patch.object(qoj_auth.time, "sleep"))

    def reply(self, path, body="", status=200, **headers):
        return SimpleNamespace(url=qoj_auth.BASE + path, status_code=status, text=body,
                               headers={"Content-Type": "text/html", **headers})

    def test_expired_cache_is_cleared_before_password_login(self):
        path = self.data / ".cookies-example.json"
        path.write_text(json.dumps({"__Host-UOJSESSID": "expired"}))
        token = "x" * 60
        profile = "/user/profile/example"
        responses = iter([
            self.reply(profile, "function submitLoginPost() {}"),
            self.reply("/login", f'_token : "{token}"'),
            self.reply("/login", "ok"),
            self.reply(profile, "My Profile"),
        ])

        def respond(method, url, **kwargs):
            if url.endswith("/login"):
                self.assertNotIn("__Host-UOJSESSID", self.client.session.cookies)
            if method == "POST":
                self.assertEqual(kwargs["data"], {
                    "_token": token, "login": "", "username": "example",
                    "password": "5f4dcc3b5aa765d61d8327deb882cf99",
                })
                self.client.session.cookies.set("__Host-UOJSESSID", "fresh", secure=True)
            return next(responses)

        self.request.side_effect = respond
        self.client.login("example", "password")
        self.assertEqual(json.loads(path.read_text()), {"__Host-UOJSESSID": "fresh"})
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_legacy_session_can_be_reused_without_a_password(self):
        legacy = self.data / "team_r3" / ".cookies-example.json"
        legacy.parent.mkdir()
        legacy.write_text(json.dumps({"__Host-UOJSESSID": "active"}))
        self.request.return_value = self.reply("/user/profile/example", "My Profile")
        self.client.login("example", None)
        self.request.assert_called_once_with("GET", qoj_auth.BASE + "/user/profile/example")
        self.assertTrue((self.data / legacy.name).exists())

    def test_login_rejects_ok_without_signed_in_profile(self):
        self.request.side_effect = [
            self.reply("/login", f"_token : '{'x' * 60}'"),
            self.reply("/login", "ok"),
            self.reply("/user/profile/example", "function submitLoginPost() {}"),
        ]
        with self.assertRaisesRegex(qoj_auth.QOJError, "did not confirm"):
            self.client.login("example", "password")
        self.assertEqual(list(self.data.iterdir()), [])

    def test_login_html_instead_of_submissions_is_an_error(self):
        self.request.return_value = self.reply("/submissions", "function submitLoginPost() {}")
        with self.assertRaisesRegex(qoj_auth.QOJError, "asked for login again"):
            self.client.get("/submissions")

    def test_cloudflare_challenge_stops_before_posting_credentials(self):
        self.request.return_value = self.reply("/login", status=403, **{"cf-mitigated": "challenge"})
        with self.assertRaisesRegex(qoj_auth.QOJError, "Cloudflare challenge"):
            self.client.login("example", "password")
        self.request.assert_called_once_with("GET", qoj_auth.BASE + "/login")

    def test_rate_limit_stops_download_and_reports_retry_after(self):
        self.request.return_value = self.reply("/submissions", status=429, **{"Retry-After": "20"})
        with self.assertRaisesRegex(qoj_auth.QOJError, "Retry-After: 20"):
            self.client.get("/submissions")
        self.request.assert_called_once()

    def test_redirect_outside_qoj_is_not_followed(self):
        self.request.return_value = self.reply("/download.php", status=302,
                                               Location="https://example.com/download")
        with self.assertRaisesRegex(qoj_auth.QOJError, "outside https://qoj.ac"):
            self.client.get("/download.php")
        self.request.assert_called_once()
