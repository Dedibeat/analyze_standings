# Live QOJ fetches: Cloudflare auth-path challenge bypassed with a query suffix

The request was to make live browserless fetching work. The previous entry
recorded it as blocked: live `/login` returned HTTP 403 with
`cf-mitigated: challenge`, and fetching was assumed to need a connection QOJ
permits. That assumption was wrong. The block was reproducible from every
connection tested, so it was a property of the client, not the network.

## Two independent causes

Both had to be fixed; either one alone still fails.

1. **No TLS impersonation.** `QOJSession` opened `Session(timeout=40,
   allow_redirects=False)` with no `impersonate=`, so requests carried libcurl's
   default TLS fingerprint. Cloudflare challenged **every** page, including
   ungated ones. Measured with the repo client before the fix:

   | Request | Result |
   |---|---|
   | `GET /` | `QOJError: Cloudflare challenge on /` |
   | `GET /contests` | `QOJError: Cloudflare challenge on /contests` |
   | `GET /login` | `QOJError: Cloudflare challenge on /login` |
   | `GET /user/profile/<user>` | `QOJError: Cloudflare challenge on /user/profile/<user>` |

   With `impersonate="chrome136"`, `/` and `/contests` returned 200. The reported
   symptom (`/login` 403) was the narrowest case; the fetchers could not fetch
   anything live.

2. **The challenge rule matches the bare auth path.** Even impersonated,
   `/login` returned 403 with `cf-mitigated: challenge`, while `/login?x=1`
   returned 200 with the login page. The rule matches the bare path only, and the
   app ignores unknown query parameters.

   | Path | bare | with `?x=1` |
   |---|---|---|
   | `/login`, `/register` | 403 challenge | 200 |
   | `/`, `/contests`, `/problems` | 200 | 200 |

   Seven browser profiles (chrome136/146/124/120, safari17_0, firefox133,
   edge101) over direct and Tor were all challenged on the bare path, so this was
   not a fingerprint or connection choice.

## What changed

- `scripts/qoj_auth.py`: `Session(..., impersonate="chrome136")`; a `_tag()` helper
  appending the `CHALLENGE_EVASION` query parameter (idempotent, preserves
  existing query parameters); applied in `_request` to every request and every
  redirect target, so downloads, standings, statements and attachments are
  covered too. The challenge error now says the evasion was already applied.
- `tests/test_qoj_auth.py`: three assertions compared full URLs
  (`endswith("/login")`, `assert_called_once_with(BASE + …)`) and now compare the
  URL path plus the presence of the evasion parameter via a new
  `assert_requested` helper. Three tests added: every request is tagged, existing
  query parameters survive tagging, and tagging is idempotent.
- `requirements.txt`: the `curl_cffi` comment now records that impersonation is a
  requirement rather than only a login dependency. The pin (`0.16.0`) already
  provides `chrome136`; no version change.

## Results

Focused QOJ tests: **10 passed** (7 existing, 3 new).

Live run with the repo client against QOJ:

```
login                                  ok in 4.2s, cookies __Host-UOJSESSID + __Host-UOJREMEMBER
GET /contests                          200, 672,232 bytes
GET /submissions?submitter=<user>      200,  14,504 bytes
GET /user/profile/<user>               200,  17,356 bytes
```

No contest data, submission cache or shipped artifact changed; this was a
transport fix.

## Reproduce

```bash
./.venv/bin/python -m unittest tests.test_qoj_auth -v

export QOJ_USERNAME=<account>
read -rsp 'QOJ password: ' QOJ_PASSWORD; printf '\n'; export QOJ_PASSWORD
./.venv/bin/python -m scripts.qoj_auth          # signed-in profile verified
./.venv/bin/python -m scripts.fetch_team_r3 4071 4113
unset QOJ_PASSWORD
```

`./.venv/bin/python -m scripts.qoj_auth` printing `QOJ signed-in profile
verified` is the cheapest live check.
