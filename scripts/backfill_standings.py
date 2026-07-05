import qoj

# Backfill an older dump that predates a field (resumable; re-run to retry failures)
import json
dir = "data/tagged.json"
contests = json.load(open(dir))
qoj.backfill_standings(contests, dir, process_unofficial=True, checkpoint_every=5, workers=20) # include unofficial