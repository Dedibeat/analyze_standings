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

`fetch_team_r3` writes the TEAM_R3 submission list and visible source files,
plus dashboards, statements, attachments and standings under `data/team_r3/`.
Use an account that can view those files. TEAM_R3's Training Mode hides
standings, so use a personal account when fetching boards. The fetcher
rechecks the submission list on each run and reuses downloaded files.

`add_qoj_contest` writes a contest's problems and standings to `data/tagged.json`.
Pass `--refresh` to replace an existing contest or `--output` to use a different
contest-array JSON file.
