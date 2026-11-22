"""Harvest a QOJ ``cf_clearance`` cookie with a real browser, for reuse by ``qoj_auth``.

QOJ sits behind Cloudflare. A headless browser is detected and a plain HTTP client
cannot answer the managed challenge, but a headful Chrome without automation flags
clears it in a few seconds and receives ``cf_clearance``. That cookie can then be
replayed by ``qoj_auth`` against the bare URLs, which keeps every later fetch
browserless.

This tool is the only part of the QOJ path that needs a browser, and it is only
needed when ``qoj_auth`` reports a challenge it cannot get past with the query
suffix. The cookie is written to the gitignored ``data/.qoj-clearance.json``
together with the exact User-Agent that minted it; both must be replayed together.

    ./.venv/bin/python -m scripts.qoj_clearance

Requires a display (``DISPLAY``) and a Chrome binary; override with ``QOJ_CHROME``.
"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import websocket

BASE = "https://qoj.ac"
DATA = Path(__file__).resolve().parents[1] / "data"
CLEARANCE = DATA / ".qoj-clearance.json"
CLEARANCE_COOKIE = "cf_clearance"
CHROME_CANDIDATES = ("/opt/google/chrome/chrome", "/usr/bin/google-chrome",
                     "/usr/bin/chromium", "/usr/bin/chromium-browser")


class ClearanceError(Exception):
    """A clearance cookie could not be harvested or saved."""


def chrome_binary():
    """Path to a Chrome binary, or raise with what to do about it."""
    override = os.environ.get("QOJ_CHROME")
    if override:
        if Path(override).exists() or shutil.which(override):
            return override
        raise ClearanceError(f"QOJ_CHROME={override} does not exist")
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    raise ClearanceError("no Chrome found; set QOJ_CHROME to its path")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _CDP:
    """Minimal Chrome DevTools Protocol client over a page WebSocket."""

    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=25, suppress_origin=True)
        self._id = 0

    def call(self, method, params=None):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self._id:
                return message.get("result", message.get("error"))
            if message.get("method") == "Inspector.targetCrashed":
                raise ClearanceError("the browser tab crashed while loading QOJ")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def _page_ws_url(port, deadline):
    """Wait for Chrome's DevTools endpoint and return the first page target."""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                pages = [t for t in json.load(response) if t["type"] == "page"]
            if pages:
                return pages[0]["webSocketDebuggerUrl"]
        except (urllib.error.URLError, ValueError, KeyError):
            pass
        time.sleep(0.5)
    raise ClearanceError("Chrome's DevTools endpoint never came up")


def harvest(timeout=60):
    """Launch a headful Chrome, clear Cloudflare's challenge, return the jar and UA."""
    if not os.environ.get("DISPLAY"):
        raise ClearanceError("no DISPLAY; Cloudflare needs a headful browser")
    port = _free_port()
    profile = tempfile.mkdtemp(prefix="qoj-clearance-")
    process = subprocess.Popen(
        [chrome_binary(), f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
         "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
         "--window-size=1280,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    cdp = None
    try:
        deadline = time.time() + timeout
        cdp = _CDP(_page_ws_url(port, deadline))
        cdp.call("Network.enable")
        cdp.call("Page.enable")
        cdp.call("Page.navigate", {"url": f"{BASE}/login"})
        while time.time() < deadline:
            time.sleep(2)
            cookies = (cdp.call("Network.getAllCookies", {}) or {}).get("cookies", [])
            clearance = next((c for c in cookies if c["name"] == CLEARANCE_COOKIE), None)
            if clearance:
                jar = {c["name"]: c["value"] for c in cookies
                       if c.get("domain", "").endswith("qoj.ac")}
                agent = (cdp.call("Runtime.evaluate", {
                    "expression": "navigator.userAgent", "returnByValue": True,
                }) or {}).get("result", {}).get("value")
                return {"user_agent": agent, "cookies": jar, "harvested_at": int(time.time())}
        raise ClearanceError(
            f"no {CLEARANCE_COOKIE} after {timeout}s; QOJ may be challenging this "
            "network regardless of the browser")
    finally:
        if cdp is not None:
            cdp.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(profile, ignore_errors=True)


def save(clearance, path=CLEARANCE):
    """Write the clearance atomically, owner-readable only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(clearance, stream, indent=2)
    temporary.replace(path)
    return path


def load(path=CLEARANCE):
    """Read a saved clearance, or None when there is not one."""
    try:
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    if not isinstance(saved, dict) or CLEARANCE_COOKIE not in saved.get("cookies", {}):
        return None
    return saved


def verify(clearance):
    """Check that a plain HTTP client can reach the bare login page with it."""
    from curl_cffi.requests import Session

    session = Session(impersonate="chrome136", timeout=40)
    if clearance.get("user_agent"):
        session.headers["User-Agent"] = clearance["user_agent"]
    session.headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in clearance["cookies"].items())
    response = session.get(f"{BASE}/login")
    challenged = (response.headers.get("cf-mitigated") == "challenge"
                  or "Just a moment" in response.text[:4000])
    return not challenged and response.status_code == 200


def main():
    try:
        clearance = harvest()
        if not verify(clearance):
            raise ClearanceError(
                "harvested a cookie but a plain client still gets challenged; "
                "the User-Agent or the network may not match")
        path = save(clearance)
    except ClearanceError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"cf_clearance harvested and verified -> {path}")
    print("qoj_auth will replay it automatically.")


if __name__ == "__main__":
    main()
