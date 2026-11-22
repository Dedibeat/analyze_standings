# Shared QOJ authentication for downloads

The request was to make browserless QOJ authentication available to the
submission and contest fetchers, save the tools in this repository, and push.

`scripts/qoj_auth.py` now runs the QOJ password login, verifies the signed-in
profile and refreshes a shared per-account cache. It accepts legacy team
caches. The single-contest and TEAM_R3 tools use the same session for all
requests. They reject login and challenge pages before parsing, and surface
rate limits with `Retry-After` when supplied. No contest or submission cache
data changed. Usage is in [the QOJ fetcher guide](../usage/qoj.md).

A standard HTTPS request to live QOJ `/login` returned HTTP 403 with
`cf-mitigated: challenge`. The auth CLI reported the challenge before a
password POST. Live authentication and downloads are blocked in this
environment. A simulated run fetched 2 submission pages, 2 source files, 1
dashboard, 1 attachment, 1 statement via HTML fallback and both standings
variants. The single-contest parser returned 1 problem and 1 standings row
from the fixture.

Seven focused tests passed. A full suite run before adding the redirect test
ran 253 tests with the three known `test_medal_predict` failures documented in
[status](../STATUS.md). Reproduce the focused checks and the public endpoint
probe from the repo root.

```bash
.venv/bin/python -m unittest discover -s tests -p test_qoj_auth.py
curl -sS -D - -o /dev/null https://qoj.ac/login
```
