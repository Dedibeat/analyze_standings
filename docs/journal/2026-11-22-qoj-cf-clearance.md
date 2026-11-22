# A harvested cf_clearance makes the QOJ path browserless again

The request was to make QOJ authentication survive Cloudflare without depending on
the query-suffix trick recorded in
[the earlier entry](2026-11-22-qoj-cloudflare-evasion.md), and Tier 2 of that
entry's options was chosen.

## What was measured

Four routes were tried against the live bare `/login`, which returns `403` with
`cf-mitigated: challenge` to a plain client:

| Route | Result |
|---|---|
| `curl_cffi`, 7 impersonation profiles, direct and Tor | challenged on every one |
| Headless Chrome (`headless=new`) with a spoofed desktop User-Agent | "Just a moment" for 30 s, no clearance |
| Headless Chrome (`headless=new`) without the spoof | challenged |
| **Headful Chrome, no automation flags** (`navigator.webdriver` false) | **cleared in about 6 s and set `cf_clearance`** |

So a managed challenge cannot be answered by HTTP alone, and hiding headlessness
is not enough — the browser has to be real. That browser then hands over a cookie
a plain client can replay:

| Client | Bare `/login` |
|---|---|
| `chrome136` UA, no clearance | `403` challenge |
| Browser User-Agent + `cf_clearance` | `200` |
| Bare `POST /login` (no `?x=1`) | `ok` |
| Profile check | `My Profile` present |

`cf_clearance` is `HttpOnly`, `Secure`, `domain=.qoj.ac`, and QOJ set it to expire
on 2027-11-22. The **User-Agent must match** the one that minted it; the TLS
fingerprint did not have to (a `chrome136` client with a Chrome 153 User-Agent
worked), and the cookie is bound to the IP, so it does not travel between
machines.

## What changed

- `scripts/qoj_clearance.py`: launches a headful Chrome with a throwaway profile
  and a free debugging port, navigates to the login page over the DevTools
  protocol, waits for `cf_clearance`, verifies that a plain client can then reach
  the bare login page, and writes the cookie plus its User-Agent to
  `data/.qoj-clearance.json` (mode 600). It refuses to run without `DISPLAY` or a
  Chrome binary, and names `QOJ_CHROME` when it cannot find one.
- `scripts/qoj_auth.py`: loads that file and replays **only `cf_clearance`**, plus
  the matching User-Agent. A raw `Cookie` header was rejected as a design: it
  would pin the pre-login session and shadow the `UOJSESSID` that a login issues.
  The query suffix is unchanged and still applied, so the two layers compose. The
  challenge error now distinguishes "harvest one" from "the cached one is stale".
- `requirements.txt`: `websocket-client==1.9.0` for the DevTools protocol.
  `.gitignore`: `data/.qoj-clearance*.json`, because the file is a credential.
- Tests: 7 for the new module (roundtrip and 0600 mode, rejected records, corrupt
  JSON, Chrome override, refusing without `DISPLAY`) and 4 for the replay (cookie
  and User-Agent applied, no raw header, both challenge messages).

## Results

Focused tests: **21 passed** (14 auth, 7 clearance). Live, with the harvester's
output: bare `GET /login` `200`, bare `POST /login` `ok`, profile verified, and
the ordinary tagged login still completes in 4.2 s.

No contest data, submission cache or shipped artifact changed.

## Reproduce

```bash
./.venv/bin/python -m unittest tests.test_qoj_auth tests.test_qoj_clearance
./.venv/bin/python -m scripts.qoj_clearance      # needs DISPLAY and Chrome
./.venv/bin/python -m scripts.qoj_auth
```

The middle command prints `cf_clearance harvested and verified` and the last
prints `QOJ signed-in profile verified`. Without the clearance those still work
through the query suffix; the clearance is the fallback for when that stops.
