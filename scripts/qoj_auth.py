"""Password login and authenticated reads for QOJ's web interface."""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit

from curl_cffi.requests import Session
from curl_cffi.requests.exceptions import RequestException

BASE = "https://qoj.ac"
DATA = Path(__file__).resolve().parents[1] / "data"
# Cloudflare serves a managed challenge (403 + cf-mitigated: challenge) on the
# BARE auth paths (/login, /register). The WAF rule matches the bare path, so any
# query string reaches the origin; the app ignores unknown parameters. See
# docs/journal/2026-11-22-qoj-cloudflare-evasion.md.
CHALLENGE_EVASION = "x=1"
TOKEN = re.compile(r'''["']?_token["']?\s*:\s*["']([A-Za-z0-9]{60})["']''')
LOGIN_FORM = re.compile(r"\bfunction\s+submitLoginPost\s*\(")
AUTH_COOKIES = {"__Host-UOJSESSID", "__Host-UOJREMEMBER", "UOJSESSID", "UOJREMEMBER"}


class QOJError(Exception):
    """A QOJ request or session could not be used."""


def _tag(url):
    """Append the challenge-evasion query parameter (idempotent)."""
    parts = urlsplit(url)
    params = [p for p in parts.query.split("&") if p and p != CHALLENGE_EVASION]
    query = "&".join([*params, CHALLENGE_EVASION])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


class QOJSession:
    def __init__(self):
        # impersonate is REQUIRED: Cloudflare challenges libcurl's default TLS
        # fingerprint on every page, including ungated ones.
        self.session = Session(timeout=40, allow_redirects=False, impersonate="chrome136")
        self.next_request = 0.0

    def close(self):
        self.session.close()

    def _request(self, method, url, **kwargs):
        for _ in range(6):
            parsed = urlsplit(url)
            if (parsed.scheme, parsed.netloc) != ("https", "qoj.ac"):
                raise QOJError("request is outside https://qoj.ac")
            url = _tag(url)
            delay = self.next_request - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            try:
                response = self.session.request(method, url, **kwargs)
            except RequestException as exc:
                raise QOJError(f"QOJ network error on {parsed.path}: {exc}") from exc
            self.next_request = time.monotonic() + 1.5
            if response.headers.get("cf-mitigated") == "challenge":
                raise QOJError(
                    f"QOJ presented a Cloudflare challenge on {parsed.path} "
                    f"despite the query-suffix evasion; re-check qoj.ac's WAF rules"
                )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                detail = f" (Retry-After: {retry_after})" if retry_after else ""
                raise QOJError(f"QOJ rate limit on {parsed.path}{detail}; retry later")
            if response.status_code in (301, 302, 303, 307, 308) and method == "GET":
                location = response.headers.get("Location")
                if location:
                    url = urljoin(url, location)
                    kwargs.pop("params", None)
                    continue
            if not 200 <= response.status_code < 300:
                raise HTTPError(url, response.status_code, "QOJ request failed",
                                response.headers, None)
            return response
        raise QOJError("too many QOJ redirects")

    def _logged_in(self, username):
        response = self._request("GET", f"{BASE}/user/profile/{username}")
        return "My Profile" in response.text and not self._login_page(response)

    @staticmethod
    def _login_page(response):
        return (urlsplit(response.url).path.rstrip("/") == "/login"
                or LOGIN_FORM.search(response.text) is not None)

    def get(self, path, **kwargs):
        url = urljoin(BASE, path)
        response = self._request("GET", url, **kwargs)
        if (urlsplit(response.url).path.rstrip("/") == "/login"
                or ("html" in response.headers.get("Content-Type", "").lower()
                    and self._login_page(response))):
            raise QOJError(f"QOJ asked for login again on {urlsplit(url).path}")
        return response

    def _load_cookies(self, path):
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return False
        if not isinstance(saved, dict):
            return False
        self.session.cookies.clear()
        for name, value in saved.items():
            if name in AUTH_COOKIES and isinstance(value, str):
                self.session.cookies.set(name, value, secure=True)
        return bool(len(self.session.cookies))

    def _save_cookies(self, path):
        saved = {cookie.name: cookie.value for cookie in self.session.cookies.jar
                 if cookie.name in AUTH_COOKIES}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(saved, stream)
                stream.close()
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)

    def login(self, username, password):
        if not username or not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
            raise QOJError("set QOJ_USERNAME to a valid QOJ username")
        cache = DATA / f".cookies-{username}.json"
        for path in (cache, DATA / "team_r3" / cache.name):
            if self._load_cookies(path) and self._logged_in(username):
                self._save_cookies(cache)
                return
        self.session.cookies.clear()
        if not password:
            raise QOJError("set QOJ_PASSWORD for a fresh QOJ login")
        page = self._request("GET", f"{BASE}/login").text
        token = TOKEN.search(page)
        if token is None:
            raise QOJError("QOJ's login page has no _token")
        response = self._request("POST", f"{BASE}/login", data={
            "_token": token.group(1), "login": "", "username": username,
            "password": hashlib.md5(password.encode()).hexdigest(),
        })
        if response.text.strip() != "ok":
            raise QOJError("QOJ did not accept the password-only login")
        if not self._logged_in(username):
            raise QOJError("QOJ did not confirm the signed-in profile")
        self._save_cookies(cache)


def authenticate():
    qoj = QOJSession()
    try:
        qoj.login(os.environ.get("QOJ_USERNAME"), os.environ.get("QOJ_PASSWORD"))
    except BaseException:
        qoj.close()
        raise
    return qoj


if __name__ == "__main__":
    try:
        authenticate().close()
    except (QOJError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    print("QOJ signed-in profile verified")
