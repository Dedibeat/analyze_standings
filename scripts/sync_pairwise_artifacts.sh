#!/usr/bin/env bash
# Copy or verify the gitignored Codeforces pairwise experiment artifacts.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REMOTE_REPO=${PAIRWISE_ARTIFACT_REPO:-/home/dedibeat/CompetitiveProgramming/analyze_standings}
SNAPSHOT="$ROOT/data/cf_pairwise/artifact_snapshot.json"
ARTIFACTS=(
  pairwise_tuning_run
  pairwise_phase2_run
  pairwise_phase3_run
  data/cf_pairwise/problems
)

usage() {
  cat <<'EOF'
Usage:
  scripts/sync_pairwise_artifacts.sh pull USER@HOST
  scripts/sync_pairwise_artifacts.sh push USER@HOST
  scripts/sync_pairwise_artifacts.sh verify

Copies the gitignored pairwise experiment artifacts between matching repository
checkouts. Set PAIRWISE_ARTIFACT_REPO when the source checkout is not at
/home/dedibeat/CompetitiveProgramming/analyze_standings.
EOF
}

transfer() {
  local direction=$1 endpoint=$2 rel
  command -v rsync >/dev/null || {
    echo "rsync is required; install it first." >&2
    exit 1
  }
  for rel in "${ARTIFACTS[@]}"; do
    if [[ $direction == pull ]]; then
      mkdir -p "$ROOT/$rel"
      rsync -aP "$endpoint:$REMOTE_REPO/$rel/" "$ROOT/$rel/"
    else
      rsync -aP "$ROOT/$rel/" "$endpoint:$REMOTE_REPO/$rel/"
    fi
  done
}

case ${1:-} in
  pull|push)
    [[ $# == 2 ]] || { usage >&2; exit 2; }
    transfer "$1" "$2"
    ;;
  verify)
    [[ $# == 1 ]] || { usage >&2; exit 2; }
    python3 - "$ROOT" "$SNAPSHOT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
snapshot = json.loads(Path(sys.argv[2]).read_text())
failed = False
for relative, expected in snapshot["artifacts"].items():
    directory = root / relative
    files = sorted(path for path in directory.rglob("*") if path.is_file()) if directory.exists() else []
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    actual = {"files": len(files), "sha256": digest.hexdigest()}
    ok = actual == expected
    print(f"{'OK' if ok else 'MISMATCH'} {relative}: {actual['files']} files {actual['sha256']}")
    failed |= not ok
raise SystemExit(1 if failed else 0)
PY
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
