#!/usr/bin/env python3
"""Collect the evidence that explains *why* a regional team got a quota seat.

Asia East regionals fill most seats from online-qualifier rank bands
(``data/ec_online/slot_rules.json``); the rest ("奖励/贡献/外卡" seats) go to
schools through channels that each notice lists.  This script gathers one
official source per channel:

* World Finals schools (+1 seat, last three WFs): 46th/47th from the XCPCIO
  WF boards (English names, mapped to Chinese below), 48th/49th verbatim from
  the 50th Xi'an notice's lists, 50th from the 51st (2026) Xi'an notice.
* Host schools (+2): 2025 and 2026 verbatim from those Xi'an notices;
  2023-2024 from the site notices' venue or signature (sites whose notice
  names no host are left out rather than guessed).
* Invitational medals (Xi'an 2023: 124 medal schools, Kunming 2024: 98):
  the spring invitational boards on XCPCIO.
* Provincial contests (local/provincial seats): official schools of each
  province's provincial contest board on XCPCIO.
* Ground truth: Shanghai's published per-school allocation (online seats,
  reward seats, total) for 2024 and 2025.

Writes ``data/ec_online/quota_evidence.json``.  Needs network + pdftotext.

    python3 scripts/build_quota_evidence.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_ec_online_data import (CACHE, DOCS, OUT, _text, fetch, medal_counts,  # noqa: E402
                                  nfkc, regional_standings)

XCPCIO = "https://board.xcpcio.com/data/"

# XCPCIO WF boards list teams by English university name; mainland/HK schools
# mapped to the Chinese names the online rankings use.
WF_BOARDS = {46: "icpc/46th/world-finals", 47: "icpc/47th/world-finals"}
EN_TO_CN = {
    "Beihang University": "北京航空航天大学",
    "Beijing Institute of Technology": "北京理工大学",
    "Central South University": "中南大学",
    "Hangzhou Dianzi University": "杭州电子科技大学",
    "Huazhong University of Science and Technology": "华中科技大学",
    "Hunan University": "湖南大学",
    "Jinan University": "暨南大学",
    "Nanjing University": "南京大学",
    "Nanjing University of Posts and Telecommunications": "南京邮电大学",
    "Northwestern Polytechnical University": "西北工业大学",
    "Peking University": "北京大学",
    "Shandong University": "山东大学",
    "Shanghai Jiao Tong University": "上海交通大学",
    "Southern University of Science and Technology": "南方科技大学",
    "The Chinese University of Hong Kong, Shenzhen": "香港中文大学（深圳）",
    "Tianjin University": "天津大学",
    "Tsinghua University": "清华大学",
    "University of Electronic Science and Technology of China": "电子科技大学",
    "University of Hong Kong": "香港大学",
    "University of Science and Technology of China": "中国科学技术大学",
    "Xi'an Jiaotong University": "西安交通大学",
    "Zhejiang Normal University": "浙江师范大学",
    "Zhejiang University": "浙江大学",
    "Zhongshan (Sun Yat-sen) University": "中山大学",
}
XIAN_2025_NOTICE = "https://icpc.pku.edu.cn/tzgg/13fdc9e9f8d54e8fa227f2ee7cfe1b9d.htm"
XIAN_2026_NOTICE = "https://icpc.pku.edu.cn/tzgg/a9259fcfb12d4087b31bc1eef3490e79.htm"
WF_FROM_NOTICE = {  # 晋级 2024 / 2025 / 2026 年世界总决赛的高校 (48th Astana, 49th Baku, 50th Dubai)
    48: "清华大学、电子科技大学、哈尔滨工业大学、东北大学、武汉理工大学、南京邮电大学、南京大学、湖南大学、"
        "北京大学、北京交通大学、上海交通大学、国防科技大学、浙江大学、香港中文大学（深圳）、香港中文大学、"
        "中国科学技术大学、西北工业大学",
    49: "北京大学、清华大学、浙江大学、中国科学技术大学、中山大学、北京航空航天大学、哈尔滨工业大学、上海交通大学、"
        "中南大学、北京交通大学、南京理工大学、南方科技大学、北京邮电大学、南京航空航天大学、上海大学、香港大学",
    50: "北京大学、清华大学、浙江大学、上海交通大学、复旦大学、中山大学、武汉大学、香港中文大学、中国科学技术大学、"
        "哈尔滨工业大学、电子科技大学、吉林大学、东北大学、广东工业大学、西北工业大学、香港中文大学（深圳）",
}
# Which WF editions give a seat in each season, as the notices state.  2023
# notices differ ("2022 and 2023 WF", "45th-47th"); the 45th list is not on
# XCPCIO, so 2023 uses 46th-47th.
WF_EDITIONS = {"2023": [46, 47], "2024": [46, 47, 48], "2025": [47, 48, 49], "2026": [48, 49, 50]}

HOSTS = {
    "2023": {"东北大学": "Shenyang notice: 在东北大学南湖校区举办",
             "中国科学技术大学": "Hefei notice: 在中国科学技术大学中校区体育馆举行",
             "杭州师范大学": "Hangzhou notice signature",
             "南京航空航天大学": "Nanjing notice signature",
             "澳门大学": "Macau notice: 比赛将在澳门大学举办"},
    "2024": {"东北大学": "Shenyang notice venue", "云南大学": "Kunming notice signature",
             "杭州师范大学": "Hangzhou notice signature", "上海大学": "Shanghai notice venue",
             "南京航空航天大学": "Nanjing notice signature",
             "香港理工大学": "Hong Kong notice: 在香港理工大学和香港城市大学举办",
             "香港城市大学": "Hong Kong notice: 在香港理工大学和香港城市大学举办"},
    "2025": {s: "Xi'an 2025 notice: 2025 年亚洲区域赛 EC 承办高校" for s in
             "北京大学、西北工业大学、电子科技大学、武汉大学、南京航空航天大学、东北大学、上海大学、"
             "香港科技大学、杭州师范大学".split("、")},
    "2026": {s: "Xi'an 2026 notice: 2026 年亚洲区域赛 EC 承办高校" for s in
             "北京大学、西北工业大学、东北大学、电子科技大学、武汉大学、南京航空航天大学、江西师范大学、上海大学、"
             "香港大学、杭州师范大学、浙江大学".split("、")},
}
HOST_GAPS = "2023 Xi'an/Jinan and 2024 Chengdu notices name no host school; setter schools are never listed."

INVITATIONALS = {"2023/xian": "48th/xian-invitational", "2024/kunming": "49th/kunming-invitational"}
INVITATIONAL_GAPS = ("2025 Xi'an uses the 2025 Shaanxi invitational (4 May 2025), which is not on XCPCIO; "
                     "2026 Nanchang uses 50th/nanchang-invitational (forecast season only).")

PROVINCIAL = {  # site -> provincial-contest boards of the site's province
    "shenyang": ["2024/liaoning", "2025/liaoning"],
    "nanjing": ["2023/jiangsu", "2024/jiangsu", "2025/jiangsu"],
    "wuhan": ["2023/hubei", "2024/hubei"],
    "xian": ["2024/shaanxi", "2025/shaanxi"],
    "jinan": ["2023/shandong", "2025/shandong"],  # 2024 doubled as a national invitational
    "hangzhou": ["2023/zhejiang", "2024/zhejiang", "2025/zhejiang"],
    "chengdu": ["2024/sichuan", "2025/sichuan"],
    "shanghai": ["2024/shanghai", "2025/shanghai"],
}
PROVINCIAL_GAPS = "No XCPCIO provincial board for Anhui (Hefei) or Yunnan (Kunming)."

SHANGHAI_LISTS = {
    "2024": ("https://icpc.pku.edu.cn/tzgg/1119_icpcbjzb_161517.htm", "20241007084720435160"),
    "2025": ("https://icpc.pku.edu.cn/tzgg/be110dad48534738906910e7410fd026.htm",
             "2025-10/7703198a6b214913a17bd2dc3a1d117c"),
}


def board_teams(path):
    cache = CACHE / "xcpcio" / path.replace("/", "_")
    teams = json.loads(fetch(XCPCIO + path + "/team.json", cache / "team.json").read_text())
    return list(teams.values()) if isinstance(teams, dict) else teams


def is_official(t):
    group = t.get("group")
    return "official" in group if group is not None else bool(t.get("official", True))


def wf_schools():
    out = {}
    for edition, path in WF_BOARDS.items():
        names = {_text(t.get("name")) for t in board_teams(path)}
        out[edition] = sorted(EN_TO_CN[n] for n in names if n in EN_TO_CN)
    for edition, text in WF_FROM_NOTICE.items():
        out[edition] = sorted(text.split("、"))
    return out


def invitational_medals(board):
    config, rows = regional_standings(board)
    gold, silver, bronze, how = medal_counts(0, config, rows)
    medal_ranks = gold + silver + bronze
    schools = sorted({r["school"] for r in rows if r["official"] and r["solved"] > 0
                      and r["official_rank"] <= medal_ranks})
    return {"board": f"https://board.xcpcio.com/icpc/{board}", "medal_source": how,
            "medals": [gold, silver, bronze], "schools": schools}


def provincial_schools(path):
    return sorted({_text(t.get("organization")) for t in board_teams("provincial-contest/" + path)
                   if is_official(t)} - {""})


def shanghai_list(pdf_id):
    pdf = fetch(DOCS + pdf_id + ".pdf", CACHE / "pdf" / (pdf_id.replace("/", "_") + ".pdf"))
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                          text=True, check=True).stdout
    lines = [ln for ln in text.splitlines() if ln.strip()]
    rows = []
    for i, line in enumerate(lines):
        m = re.match(r"\s*(\d+)\s+(\S+\s+)?(\d+)\s+(\d+)\s+(\d+)\s*$", line)
        if not m:
            continue
        name = (m.group(2) or "").strip()
        if not name:  # a wrapped name sits on the lines just above and below the numbers
            name = "".join(lines[j].strip() for j in (i - 1, i + 1) if not re.search(r"\d", lines[j]))
        rows.append({"school": nfkc(name), "online": int(m.group(3)), "reward": int(m.group(4)),
                     "total": int(m.group(5))})
    return rows


def main():
    evidence = {
        "about": __doc__.split("\n\n")[1].strip(),
        "wf_editions_by_season": WF_EDITIONS,
        "wf_schools": wf_schools(),
        "wf_sources": {"46": XCPCIO + WF_BOARDS[46], "47": XCPCIO + WF_BOARDS[47],
                       "48": XIAN_2025_NOTICE, "49": XIAN_2025_NOTICE, "50": XIAN_2026_NOTICE},
        "hosts": HOSTS,
        "invitational_medal_schools": {k: invitational_medals(b) for k, b in INVITATIONALS.items()},
        "provincial_schools": {site: {p: provincial_schools(p) for p in paths}
                               for site, paths in PROVINCIAL.items()},
        "shanghai_allocation": {s: {"source": src, "schools": shanghai_list(pid)}
                                for s, (src, pid) in SHANGHAI_LISTS.items()},
        "gaps": [HOST_GAPS, INVITATIONAL_GAPS, PROVINCIAL_GAPS,
                 "45th WF list (2023 season) not available on XCPCIO."],
    }
    path = OUT / "quota_evidence.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + "\n")
    for k, v in evidence["wf_schools"].items():
        print(f"WF {k}: {len(v)} schools")
    for k, v in evidence["invitational_medal_schools"].items():
        print(f"invitational {k}: {len(v['schools'])} medal schools ({v['medal_source']} {v['medals']})")
    for site, d in evidence["provincial_schools"].items():
        print(f"provincial {site}: " + ", ".join(f"{p} {len(s)}" for p, s in d.items()))
    for s, d in evidence["shanghai_allocation"].items():
        rows = d["schools"]
        print(f"shanghai {s}: {len(rows)} schools, online {sum(r['online'] for r in rows)}, "
              f"reward {sum(r['reward'] for r in rows)}, total {sum(r['total'] for r in rows)}")


if __name__ == "__main__":
    main()
