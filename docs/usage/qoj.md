# QOJ fetchers

Run from the repository root. Install `requirements.txt` in `.venv`. The team
fetcher also needs the sibling `../qoj-intergration` checkout and `pdftotext`.

In Bash, enter the password without echoing it or adding it to shell history.

```bash
export QOJ_USERNAME=Dedibeat
read -rsp 'QOJ password: ' QOJ_PASSWORD
printf '\n'
export QOJ_PASSWORD

.venv/bin/python -m scripts.qoj_auth
.venv/bin/python -m scripts.fetch_team_r3 4071 4113
.venv/bin/python -m scripts.add_qoj_contest 4071 --name 'EC Online (I)' --region 'Asia East Continent' --refresh

unset QOJ_PASSWORD
```

The first command checks that QOJ returns the signed-in profile. The tools
reuse session cookies from the gitignored `data/.cookies-<username>.json`.
Supply `QOJ_PASSWORD` when a fresh password-only login is needed.

All QOJ requests go through `scripts/qoj_auth.py`, which impersonates Chrome and
appends a query suffix. Cloudflare challenges the bare auth paths (`/login`,
`/register`), so both are required; see [the journal entry](../journal/2026-11-22-qoj-cloudflare-evasion.md).
Do not bypass the helper or strip the suffix. A challenge that still arrives
stops the fetcher, and a rate-limit response stops it and reports `Retry-After`
when QOJ supplies it.

### If Cloudflare challenges anyway

There are two layers and the second is only needed when the first fails.

1. The query suffix plus Chrome impersonation. This needs no browser and works
   today.
2. A `cf_clearance` cookie harvested once from a real browser:

   ```bash
   ./.venv/bin/python -m scripts.qoj_clearance
   ```

   The command launches a headful Chrome, waits for the challenge to clear,
   checks that a plain HTTP client can then reach the login page, and only then
   writes the cookie and the User-Agent that minted it to the gitignored
   `data/.qoj-clearance.json` (mode 600). `qoj_auth.py` replays it from then on,
   which lifts the challenge on the bare URLs as well. Re-run the command when
   `qoj_auth` reports that the cached clearance has expired.

It needs `DISPLAY` and a Chrome binary; set `QOJ_CHROME` to point at one. A
**headless** browser does not work — Cloudflare detects it — and neither does a
plain HTTP client, which cannot answer a managed challenge. Headful Chrome
without automation flags clears it in a few seconds.

### Running this from another machine

Without a harvested clearance the transport carries no IP or cookie state. No
`cf_clearance` is fetched or sent, so a different machine, network or country
gets the same result provided two things hold:

- `curl_cffi` resolves to the pinned `0.16.0` (or newer, with `chrome136`). An
  older version raises when the session is built rather than failing silently.
  Login needs only stdlib plus `curl_cffi`; the other requirements are for the
  analysis code, and only the team fetcher additionally needs the sibling
  `../qoj-intergration` checkout and `pdftotext`.
- The network is not an ASN Cloudflare treats as hostile. A datacenter or cloud
  IP can still be challenged even with the correct fingerprint and suffix. If
  that happens the error says the evasion was already applied; harvesting a
  clearance is the next thing to try.

A harvested `cf_clearance` is the exception to the portability above: it is bound
to the IP and User-Agent that minted it, so copying `data/.qoj-clearance.json` to
another machine does not work. Harvest again on that machine.

Check a new machine with `.venv/bin/python -m scripts.qoj_auth`: it prints `QOJ
signed-in profile verified` or stops with the reason.

`fetch_team_r3` writes the TEAM_R3 submission list and visible source files,
plus dashboards, statements, attachments and standings under `data/team_r3/`.
Use an account that can view those files. TEAM_R3's Training Mode hides
standings, so use a personal account when fetching boards. The fetcher
rechecks the submission list on each run and reuses downloaded files.

`add_qoj_contest` writes a contest's problems and standings to `data/tagged.json`.
Pass `--refresh` to replace an existing contest or `--output` to use a different
contest-array JSON file.
