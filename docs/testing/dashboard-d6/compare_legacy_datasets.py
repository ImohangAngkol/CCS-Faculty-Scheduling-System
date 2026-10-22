"""Read-only local comparison: emits counts, hashes and source row references, never academic records."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from services.external_schedule_legacy_service import HEADERS, parse_schedule


def compare():
    names = ["BSIT_GEC.csv", "BSIT_Consolidated_Subject_Schedules.csv", "BSIT_Consolidated_Subject_Schedules_test.csv"]
    sources, summaries = {}, []
    for name in names:
        raw = (ROOT / "backend/data" / name).read_bytes()
        with (ROOT / "backend/data" / name).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == list(HEADERS), "Current dataset columns differ; stop for review"
            rows = list(reader)
        exact = Counter(tuple(row[k] for k in HEADERS) for row in rows)
        groups = defaultdict(set)
        states = Counter(); findings = []; days = Counter()
        for index, row in enumerate(rows, 2):
            groups[tuple(row[k] for k in HEADERS[:3])].add(row["Schedule"])
            parsed, start, end, state, issues = parse_schedule(row["Schedule"])
            states[state] += 1
            if state == "parsed": days.update(parsed)
            else: findings.append({"source_row": index, "state": state, "codes": [d.code for d in issues]})
        sources[name] = (exact, groups)
        summaries.append({"file": name, "sha256": hashlib.sha256(raw).hexdigest(), "columns": list(HEADERS),
            "rows": len(rows), "exact_duplicate_rows": sum(exact.values())-len(exact),
            "parse_states": dict(states), "nonparsed_source_rows": findings,
            "parsed_day_meeting_occurrences": sum(days.values()), "term": "unresolved; absent from file",
            "active_fixed_section_input": name == names[1]})
    pairs = []
    for index, left in enumerate(names):
        for right in names[index+1:]:
            a, ga = sources[left]; b, gb = sources[right]
            common = ga.keys() & gb.keys()
            pairs.append({"left": left, "right": right, "exact_matching_rows": sum((a & b).values()),
                "left_only_rows": sum((a-b).values()), "right_only_rows": sum((b-a).values()),
                "shared_year_section_course_keys": len(common),
                "keys_with_differing_schedule_sets": sum(ga[k] != gb[k] for k in common),
                "left_only_keys": len(ga.keys()-gb.keys()), "right_only_keys": len(gb.keys()-ga.keys())})
    return {"observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "scope": "Read-only byte/exact-row and Year Level/Section/Course Number key comparison; no raw academic records exported, no merging, approval or activation implied.",
        "sources": summaries, "comparisons": pairs}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
