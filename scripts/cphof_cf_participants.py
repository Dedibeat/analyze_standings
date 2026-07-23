"""Collect high-confidence CPHoF -> Codeforces participant identities.

CPHoF supplies World Finals rosters and explicit external-profile links.  Once
an explicit Codeforces handle is known, the official ``user.rating`` API is the
authoritative source for its rating history.

This collector deliberately does not guess handles from names.  It:

* caches CPHoF standings/profile HTML and Codeforces API responses;
* keeps only exact normalized-name overlaps with ``data/tagged.json``;
* accepts an identity only when the CPHoF profile explicitly links Codeforces;
* retains all rating changes so callers can select the last rating known before
  a contest; and
* records rejected/ambiguous candidates for audit.

The cache is resumable and gitignored.  Rebuild the committed artifact with:

    ./.venv/bin/python scripts/cphof_cf_participants.py --refresh
"""

import argparse
import hashlib
import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser


ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DATA = os.path.join(ROOT, "data")
TAGGED = os.path.join(DATA, "tagged.json")
OUTPUT = os.path.join(DATA, "cphof_cf_participants.json")
CACHE = os.path.join(DATA, "cphof_cache")

CPHOF_STANDINGS = "https://cphof.org/standings/icpc/{year}"
CPHOF_ORIGIN = "https://cphof.org"
CF_RATING = "https://codeforces.com/api/user.rating?handle={handle}"
DEFAULT_YEARS = tuple(range(2021, 2026))
UA = (
    "analyze_standings/1.0 participant-identity collector "
    "(https://github.com/dedibeat/analyze_standings)"
)


class Node:
    def __init__(self, tag="", attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or ())
        self.parent = parent
        self.children = []

    def text(self):
        return html.unescape("".join(
            child.text() if isinstance(child, Node) else child
            for child in self.children
        ))

    def descendants(self, tag=None):
        for child in self.children:
            if not isinstance(child, Node):
                continue
            if tag is None or child.tag == tag:
                yield child
            yield from child.descendants(tag)


class _TreeParser(HTMLParser):
    _VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self._VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, attrs, self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def parse_html(source):
    parser = _TreeParser()
    parser.feed(source)
    return parser.root


def normalize_name(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(value.split())


def _normalized_roster(values):
    return {normalize_name(value) for value in values if normalize_name(value)}


def _annotate_appearances(appearances, cphof_rosters):
    """Mark target rows as trusted only when a second roster member agrees."""
    annotated = []
    for appearance in appearances:
        target_roster = _normalized_roster(appearance["roster"])
        best = None
        for source_roster in cphof_rosters:
            overlap = sorted(
                target_roster & _normalized_roster(source_roster["roster"]))
            candidate = {
                "cphof_year": source_roster["year"],
                "roster_overlap_count": len(overlap),
                "normalized_roster_overlap": overlap,
            }
            if best is None or candidate["roster_overlap_count"] > best[
                    "roster_overlap_count"]:
                best = candidate
        best = best or {
            "cphof_year": None,
            "roster_overlap_count": 0,
            "normalized_roster_overlap": [],
        }
        annotated.append({
            **appearance,
            "identity_evidence": {
                **best,
                "status": (
                    "roster_corroborated"
                    if best["roster_overlap_count"] >= 2
                    else "name_only_candidate"
                ),
                "policy": (
                    "at least two exact normalized roster members, including "
                    "the participant, must overlap a CPHoF World Finals roster"
                ),
            },
        })
    return annotated


def _clean_text(node):
    return " ".join(node.text().split())


def _direct_children(node, tag):
    return [
        child for child in node.children
        if isinstance(child, Node) and child.tag == tag
    ]


def parse_cphof_standings(source, year, source_url):
    """Parse one CPHoF ICPC World Finals standings page."""
    root = parse_html(source)
    contest_date = None
    for table in root.descendants("table"):
        for row in _direct_children(table, "tr"):
            cells = _direct_children(row, "td")
            if len(cells) >= 2 and _clean_text(cells[0]).rstrip(":") == "Date":
                contest_date = _clean_text(cells[1])
                break
        if contest_date:
            break

    standings_table = None
    for table in root.descendants("table"):
        headers = [_clean_text(node) for node in table.descendants("th")]
        if headers[:3] == ["Rank", "Country", "Team"]:
            standings_table = table
            break
    if standings_table is None:
        raise ValueError(f"CPHoF standings table not found for {year}")

    teams = []
    for row in standings_table.descendants("tr"):
        cells = _direct_children(row, "td")
        if len(cells) < 5:
            continue
        rank_match = re.search(r"\d+", _clean_text(cells[0]))
        if not rank_match:
            continue
        country_links = [
            node for node in cells[1].descendants("a")
            if node.attrs.get("href", "").startswith("/country/")
            and _clean_text(node)
        ]
        university_links = [
            node for node in cells[2].descendants("a")
            if node.attrs.get("href", "").startswith("/university/")
        ]
        profile_links = [
            node for node in cells[2].descendants("a")
            if node.attrs.get("href", "").startswith("/profile/")
        ]
        team_spans = [
            _clean_text(node) for node in cells[2].descendants("span")
            if _clean_text(node).startswith("(")
        ]
        members = []
        for profile in profile_links:
            profile_path = profile.attrs["href"]
            members.append({
                "name": _clean_text(profile),
                "profile_url": urllib.parse.urljoin(CPHOF_ORIGIN, profile_path),
            })
        teams.append({
            "rank": int(rank_match.group()),
            "country": _clean_text(country_links[-1]) if country_links else None,
            "institution": (
                _clean_text(university_links[0]) if university_links else None
            ),
            "team_name": (
                team_spans[0].strip().removeprefix("(").removesuffix(":")
                .removesuffix(")").strip()
                if team_spans else None
            ),
            "members": members,
        })

    return {
        "year": year,
        "date": contest_date,
        "date_cutoff_timestamp": _parse_cphof_date(contest_date),
        "source_url": source_url,
        "teams": teams,
    }


def _parse_cphof_date(value):
    if not value:
        return None
    cleaned = value.replace("Sept.", "Sep.").replace(".", "")
    parsed = None
    for date_format in ("%b %d, %Y", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(cleaned, date_format).replace(
                tzinfo=timezone.utc)
            break
        except ValueError:
            pass
    if parsed is None:
        return None
    return int(parsed.timestamp())


def parse_codeforces_handle(source):
    """Return the one explicit Codeforces profile handle, or ``None``."""
    root = parse_html(source)
    handles = set()
    for link in root.descendants("a"):
        href = link.attrs.get("href", "")
        parsed = urllib.parse.urlparse(href)
        if parsed.netloc.casefold() not in {"codeforces.com", "www.codeforces.com"}:
            continue
        match = re.fullmatch(r"/profile/([^/]+)", parsed.path)
        if match:
            handles.add(urllib.parse.unquote(match.group(1)))
    return next(iter(handles)) if len(handles) == 1 else None


def rating_before(history, timestamp):
    """Return rating/count from the last Codeforces update at ``timestamp``."""
    prior = [
        row for row in history
        if int(row["ratingUpdateTimeSeconds"]) <= int(timestamp)
    ]
    if not prior:
        return None
    latest = max(prior, key=lambda row: int(row["ratingUpdateTimeSeconds"]))
    return {
        "rating": int(latest["newRating"]),
        "rated_contest_count": len(prior),
        "rating_update_time_seconds": int(latest["ratingUpdateTimeSeconds"]),
    }


class Fetcher:
    def __init__(self, cache_dir=CACHE, force=False, cphof_delay=0.5,
                 codeforces_delay=2.1):
        self.cache_dir = cache_dir
        self.force = force
        self.delays = {
            "cphof": cphof_delay,
            "codeforces": codeforces_delay,
        }
        self.last_request = defaultdict(float)

    def _path(self, source, url, suffix):
        digest = hashlib.sha256(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, source, digest + suffix)

    def get(self, source, url, suffix):
        path = self._path(source, url, suffix)
        if os.path.exists(path) and not self.force:
            with open(path, "rb") as cached:
                return cached.read()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        wait = self.delays[source] - (time.monotonic() - self.last_request[source])
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    payload = response.read()
                self.last_request[source] = time.monotonic()
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 4:
                    raise
                time.sleep(max(2 ** attempt, self.delays[source]))
            except (TimeoutError, urllib.error.URLError):
                if attempt == 4:
                    raise
                time.sleep(max(2 ** attempt, self.delays[source]))
        temporary = path + ".tmp"
        with open(temporary, "wb") as destination:
            destination.write(payload)
        os.replace(temporary, path)
        return payload

    def retrieved_at(self, source, url, suffix):
        timestamp = os.path.getmtime(self._path(source, url, suffix))
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(
            timespec="seconds")


def _tagged_member_index(contests):
    members = defaultdict(list)
    for contest in contests:
        for row in contest["standings"]:
            for name in row.get("members", []):
                members[normalize_name(name)].append({
                    "member_name": name,
                    "contest_id": contest["contest_id"],
                    "contest_name": contest["contest_name"],
                    "year": contest.get("year"),
                    "region": contest.get("region"),
                    "team_id": row.get("team_id"),
                    "team_name": row.get("team_name"),
                    "affiliation": row.get("affiliation"),
                    "roster": row.get("members", []),
                })
    return members


def _fetch_history(fetcher, handle):
    url = CF_RATING.format(handle=urllib.parse.quote(handle, safe=""))
    response = json.loads(
        fetcher.get("codeforces", url, ".json").decode("utf-8"))
    if response.get("status") != "OK":
        raise ValueError(
            f"Codeforces user.rating failed for {handle}: "
            f"{response.get('comment', 'unknown error')}")
    return response["result"], url


def build_artifact(contests, cphof_contests, profiles, histories, built_at,
                   profile_retrieved_at=None, history_retrieved_at=None):
    """Build the provenance-rich identity/history artifact from parsed inputs."""
    profile_retrieved_at = profile_retrieved_at or {}
    history_retrieved_at = history_retrieved_at or {}
    tagged_members = _tagged_member_index(contests)
    people = defaultdict(lambda: {
        "names": set(), "profile_urls": set(), "cphof_rosters": [],
    })
    for contest in cphof_contests:
        for team in contest["teams"]:
            for member in team["members"]:
                key = normalize_name(member["name"])
                if key not in tagged_members:
                    continue
                person = people[key]
                person["names"].add(member["name"])
                person["profile_urls"].add(member["profile_url"])
                person["cphof_rosters"].append({
                    "year": contest["year"],
                    "contest_date": contest["date"],
                    "date_cutoff_timestamp": contest["date_cutoff_timestamp"],
                    "rank": team["rank"],
                    "country": team["country"],
                    "institution": team["institution"],
                    "team_name": team["team_name"],
                    "roster": [item["name"] for item in team["members"]],
                    "source_url": contest["source_url"],
                    "source_retrieved_at": contest.get("retrieved_at"),
                })

    accepted, rejected = [], []
    for normalized_name, person in sorted(people.items()):
        profile_urls = sorted(person["profile_urls"])
        handles = {
            profiles[url] for url in profile_urls if profiles.get(url)
        }
        tagged_appearances = _annotate_appearances(
            tagged_members[normalized_name], person["cphof_rosters"])
        base = {
            "normalized_name": normalized_name,
            "cphof_names": sorted(person["names"]),
            "cphof_profile_urls": profile_urls,
            "cphof_profile_retrieved_at": {
                url: profile_retrieved_at.get(url) for url in profile_urls
            },
            "cphof_rosters": person["cphof_rosters"],
            "tagged_appearances": tagged_appearances,
        }
        if len(handles) != 1:
            base["rejection_reason"] = (
                "no_explicit_codeforces_profile"
                if not handles else "conflicting_codeforces_profiles"
            )
            rejected.append(base)
            continue
        handle = next(iter(handles))
        history = histories.get(handle)
        if history is None:
            base["cf_handle"] = handle
            base["rejection_reason"] = "codeforces_rating_history_unavailable"
            rejected.append(base)
            continue
        pre_wf = []
        for roster in person["cphof_rosters"]:
            timestamp = roster["date_cutoff_timestamp"]
            value = rating_before(history, timestamp) if timestamp else None
            pre_wf.append({
                "year": roster["year"],
                "rating_cutoff_timestamp": timestamp,
                "rating_before_world_finals": value,
            })
        accepted.append({
            **base,
            "cf_handle": handle,
            "identity_confidence": "verified_external_profile",
            "match_method": (
                "unique_normalized_exact_name_and_explicit_cphof_cf_profile"
            ),
            "rating_history_retrieved_at": history_retrieved_at.get(handle),
            "rating_history": history,
            "pre_world_finals_ratings": pre_wf,
        })

    accepted_names = {item["normalized_name"] for item in accepted}
    roster_corroborated_appearances = [
        appearance
        for participant in accepted
        for appearance in participant["tagged_appearances"]
        if appearance["identity_evidence"]["status"] == "roster_corroborated"
    ]
    full_handle_roster_rows = {
        (
            appearance["contest_id"],
            str(appearance["team_id"]),
            tuple(sorted(_normalized_roster(appearance["roster"]))),
        )
        for appearance in roster_corroborated_appearances
        if all(
            normalize_name(member) in accepted_names
            for member in appearance["roster"]
        )
    }
    return {
        "schema_version": 1,
        "built_at": built_at,
        "role": (
            "identity_and_rating_history_input; not consumed by the fit"
        ),
        "sources": {
            "cphof": {
                "name": "Competitive Programming Hall of Fame",
                "years": [contest["year"] for contest in cphof_contests],
                "standings_urls": [
                    contest["source_url"] for contest in cphof_contests
                ],
                "profile_policy": "explicit Codeforces external link only",
            },
            "codeforces": {
                "name": "official Codeforces API",
                "method": "user.rating",
                "time_policy": (
                    "last newRating with ratingUpdateTimeSeconds <= contest start"
                ),
            },
            "target": {
                "path": "data/tagged.json",
                "contest_time_limitation": (
                    "target rows have year but no exact start timestamp; histories "
                    "are collected but regional priors are not derived"
                ),
            },
        },
        "matching": {
            "name_normalization": "Unicode NFKC, casefold, whitespace collapse",
            "candidate_people": len(people),
            "explicit_profile_identities": len(accepted),
            "roster_corroborated_people": len({
                normalize_name(appearance["member_name"])
                for appearance in roster_corroborated_appearances
            }),
            "rejected_people": len(rejected),
            "name_only_tagged_appearances": (
                sum(len(row["tagged_appearances"]) for row in accepted)
                - len(roster_corroborated_appearances)
            ),
            "roster_corroborated_tagged_appearances": len(
                roster_corroborated_appearances),
            "corroborated_full_handle_roster_rows": len(
                full_handle_roster_rows),
        },
        "world_finals_time_policy": {
            "source_granularity": "CPHoF calendar date, without start time",
            "rating_cutoff": (
                "00:00 UTC at the start of the published calendar date"
            ),
            "effect": (
                "conservative: same-date rating changes are excluded rather "
                "than risk using a post-start update"
            ),
        },
        "participants": accepted,
        "rejected_candidates": rejected,
    }


def refresh(output_path=OUTPUT, years=DEFAULT_YEARS, force=False):
    fetcher = Fetcher(force=force)
    with open(TAGGED) as source:
        contests = json.load(source)
    tagged_names = set(_tagged_member_index(contests))

    cphof_contests = []
    profile_urls = set()
    for year in years:
        url = CPHOF_STANDINGS.format(year=year)
        source = fetcher.get("cphof", url, ".html").decode("utf-8")
        contest = parse_cphof_standings(source, year, url)
        contest["retrieved_at"] = fetcher.retrieved_at(
            "cphof", url, ".html")
        cphof_contests.append(contest)
        for team in contest["teams"]:
            for member in team["members"]:
                if normalize_name(member["name"]) in tagged_names:
                    profile_urls.add(member["profile_url"])

    profiles = {}
    profile_retrieved_at = {}
    for index, url in enumerate(sorted(profile_urls), start=1):
        source = fetcher.get("cphof", url, ".html").decode("utf-8")
        profiles[url] = parse_codeforces_handle(source)
        profile_retrieved_at[url] = fetcher.retrieved_at(
            "cphof", url, ".html")
        if index % 100 == 0:
            print(f"CPHoF profiles: {index}/{len(profile_urls)}")

    handles = sorted({handle for handle in profiles.values() if handle})
    histories = {}
    history_retrieved_at = {}
    failed_histories = {}
    for index, handle in enumerate(handles, start=1):
        try:
            histories[handle], rating_url = _fetch_history(fetcher, handle)
            history_retrieved_at[handle] = fetcher.retrieved_at(
                "codeforces", rating_url, ".json")
        except (OSError, urllib.error.HTTPError, ValueError) as error:
            failed_histories[handle] = str(error)
        if index % 25 == 0:
            print(f"Codeforces histories: {index}/{len(handles)}")

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    artifact = build_artifact(
        contests, cphof_contests, profiles, histories, built_at,
        profile_retrieved_at, history_retrieved_at)
    artifact["collection"] = {
        "cphof_profile_pages_considered": len(profile_urls),
        "explicit_codeforces_handles": len(handles),
        "rating_histories_fetched": len(histories),
        "rating_history_failures": failed_histories,
        "cache_path": "data/cphof_cache/",
        "cache_policy": "resumable, local, gitignored",
    }
    with open(output_path, "w") as destination:
        json.dump(artifact, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    return artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh", action="store_true",
        help="fetch/update cached sources and rebuild the artifact")
    parser.add_argument(
        "--force", action="store_true",
        help="ignore cached responses and redownload every source")
    parser.add_argument(
        "--years", default="2021-2025",
        help="inclusive CPHoF World Finals year range (default: 2021-2025)")
    args = parser.parse_args()
    first, last = (int(value) for value in args.years.split("-", 1))
    if args.refresh:
        artifact = refresh(years=range(first, last + 1), force=args.force)
    else:
        with open(OUTPUT) as source:
            artifact = json.load(source)
    matching = artifact["matching"]
    print(
        f"CPHoF candidates={matching['candidate_people']}, "
        f"explicit CF identities={matching['explicit_profile_identities']}, "
        f"roster-corroborated people={matching['roster_corroborated_people']}, "
        f"corroborated tagged appearances="
        f"{matching['roster_corroborated_tagged_appearances']}, "
        f"corroborated full-handle roster rows="
        f"{matching['corroborated_full_handle_roster_rows']}"
    )
    limitation = artifact["sources"]["target"]["contest_time_limitation"]
    print(f"Fit status: {artifact['role']}. Limitation: {limitation}")


if __name__ == "__main__":
    main()
