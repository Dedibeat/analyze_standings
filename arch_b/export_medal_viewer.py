"""Build the EA medal-badge viewer from output/medal_badges.json.

    python -m arch_b.export_medal_viewer

Reads the ``arch_b.medals`` analysis output (run that module first) and injects
it into ``medal_viewer_template.html`` -> ``output/medal_viewer.html``.
Self-contained: opens from disk, no server, no external assets.
"""

import json
import os
import re

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "output")
TEMPLATE = os.path.join(os.path.dirname(__file__), "medal_viewer_template.html")
SRC = os.path.join(OUT_DIR, "medal_badges.json")


def _short_name(name):
    n = name.strip()
    n = re.sub(r"^The \d{4} ICPC Asia ", "", n)
    n = re.sub(r" Regional Contest$", "", n)
    n = re.sub(r"^Grand Prix of ", "", n)
    return n


def _strip_tags(s):
    return re.sub(r"<[^>]+>", "", s) if isinstance(s, str) else s


def main():
    with open(SRC) as f:
        data = json.load(f)

    probs = {}
    for p in data["problems"]:
        probs.setdefault(p["contest_id"], []).append(p)

    contests = []
    for c in data["contests"]:
        for tier in ["gold", "silver", "bronze"]:
            t = c["cutoff_teams"][tier]
            t["team_name"] = _strip_tags(t["team_name"])
            t["affiliation"] = _strip_tags(t.get("affiliation"))
        contests.append({
            **c,
            "short": _short_name(c["contest_name"]),
            "url": f"https://qoj.ac/contest/{c['contest_id']}",
            "problems": sorted(probs[c["contest_id"]], key=lambda p: p["difficulty"]),
        })

    with open(TEMPLATE) as f:
        html = f.read()
    html = html.replace("/*__DATA__*/null", json.dumps({"contests": contests},
                                                       ensure_ascii=False))
    out = os.path.join(OUT_DIR, "medal_viewer.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {os.path.normpath(out)} ({len(contests)} contests, "
          f"{sum(len(c['problems']) for c in contests)} problems)")


if __name__ == "__main__":
    main()
