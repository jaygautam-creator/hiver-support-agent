"""
Merges a round-2 label export into golden/labelled.jsonl.

Round 1 produced 40 blind labels. Round 2 relabels the remaining 158 from
scratch (see scripts/make_labeller.py for why the rule-seeded pass was thrown
away). This script joins the two halves and refuses to do so if anything about
the export looks wrong, because a silently malformed golden set would corrupt
every number in the report and would not announce itself.

Usage:
    make merge FILE=~/Downloads/labelled.jsonl

Checks, all fatal:
  * every row parses and carries a complete label (intent, decision, reason)
  * intents and reason codes are drawn from src/taxonomy.py, and the reason
    code matches the decision (E* with escalate, A* with auto)
  * no pair_id collides with a round-1 label, and none is duplicated
  * every pair_id is a real candidate from to_label.jsonl
  * nothing arrived pre-seeded (was_seeded must be false throughout)

Incomplete rows are reported and dropped rather than merged half-labelled; the
merge still proceeds so a partial session is not lost, but the count is printed
so the shortfall cannot pass unnoticed.
"""
import json
import shutil
import sys
from pathlib import Path

from src.config import GOLDEN
from src.taxonomy import INTENTS

ESC_CODES = {"E1", "E2", "E3", "E4", "E5", "E6", "E7"}
AUTO_CODES = {"A1", "A2", "A3", "A4"}
LABELLED = GOLDEN / "labelled.jsonl"


def _rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main(src: Path) -> int:
    if not src.exists():
        sys.exit(f"no such file: {src}")

    new = _rows(src)
    existing = _rows(LABELLED) if LABELLED.exists() else []
    candidates = {r["pair_id"] for r in _rows(GOLDEN / "to_label.jsonl")}
    done = {r["pair_id"] for r in existing}

    errs: list[str] = []
    complete, incomplete = [], []

    for r in new:
        pid = r.get("pair_id", "<missing>")
        if not (r.get("intent") and r.get("decision") and r.get("reason")):
            incomplete.append(pid)
            continue
        if pid not in candidates:
            errs.append(f"{pid}: not a candidate in to_label.jsonl")
        if pid in done:
            errs.append(f"{pid}: already labelled in round 1 -- would overwrite")
        if r["intent"] not in INTENTS:
            errs.append(f"{pid}: unknown intent {r['intent']!r}")
        if r["decision"] not in ("auto", "escalate"):
            errs.append(f"{pid}: unknown decision {r['decision']!r}")
        else:
            ok = ESC_CODES if r["decision"] == "escalate" else AUTO_CODES
            if r["reason"] not in ok:
                errs.append(f"{pid}: reason {r['reason']!r} does not match "
                            f"decision {r['decision']!r}")
        if r.get("was_seeded"):
            errs.append(f"{pid}: was_seeded is true -- this row was anchored")
        complete.append(r)

    seen = set()
    for r in complete:
        if r["pair_id"] in seen:
            errs.append(f"{r['pair_id']}: duplicated in the export")
        seen.add(r["pair_id"])

    if errs:
        print(f"REFUSING TO MERGE -- {len(errs)} problem(s):")
        for e in errs[:25]:
            print(f"  {e}")
        if len(errs) > 25:
            print(f"  ... and {len(errs) - 25} more")
        return 1

    if incomplete:
        print(f"  {len(incomplete)} row(s) incomplete, dropped: "
              f"{', '.join(incomplete[:5])}"
              f"{' ...' if len(incomplete) > 5 else ''}")

    if LABELLED.exists():
        backup = LABELLED.with_suffix(".jsonl.bak")
        shutil.copy(LABELLED, backup)
        print(f"  backed up {len(existing)} round-1 labels -> {backup.name}")

    merged = existing + complete
    LABELLED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n")

    from collections import Counter
    print(f"\n  merged {len(existing)} + {len(complete)} = {len(merged)} labels")
    print(f"  remaining unlabelled: {len(candidates) - len(merged)}")
    print("\n  intent distribution:")
    for k, v in Counter(r["intent"] for r in merged).most_common():
        print(f"    {k:<24} {v:>4}")
    zero = [k for k in INTENTS if k not in {r["intent"] for r in merged}]
    if zero:
        print(f"  STILL ZERO-SUPPORT (unmeasurable): {', '.join(zero)}")
    print("\n  decision distribution:")
    for k, v in Counter(r["decision"] for r in merged).most_common():
        print(f"    {k:<24} {v:>4}")
    print("\nNext: make repro-live   (re-runs the agent on the new messages)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 -m scripts.merge_labels <export.jsonl>")
    sys.exit(main(Path(sys.argv[1]).expanduser()))
