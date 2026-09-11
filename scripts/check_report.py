"""
Does the README still agree with the numbers it is reporting?

Every result in this repo is generated into results/*.md, and then quoted by hand
in README.md. That hand-copy is the weakest link in the whole chain: re-running
an experiment updates the generated file and leaves the prose asserting the old
value, silently. It has already happened twice here -- a generated report quoted
a hardcoded judge score that a re-run had made stale, and the README claimed a
"+63 point" anchoring effect against a measured +62.4.

So the claims are pinned. Each entry below names a number the README states, and
where the ground truth for it lives. A mismatch is a hard failure.

This is deliberately a small, explicit list rather than a general parser: the
point is to pin the numbers a reader would actually quote back at me, not to
prove the whole document is machine-checkable.

    make check-report
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score, f1_score

from src.config import GOLDEN, RESULTS, ROOT

README = ROOT / "README.md"


def agent_frame() -> pd.DataFrame:
    rows = [json.loads(l) for l in (RESULTS / "predictions.jsonl").read_text().splitlines()]
    df = pd.DataFrame(rows)
    return df[df.system == "agent"]


def truths() -> dict[str, float]:
    """Recompute, from the committed artifacts, every number the README quotes."""
    ag = agent_frame()
    obs = sorted(set(ag.gold_intent))
    d = ag[ag.decision_complete]
    g, p = d.gold_decision == "escalate", d.pred_decision == "escalate"
    tp, fp, fn = int((g & p).sum()), int((~g & p).sum()), int((g & ~p).sum())

    t = {
        "intent macro-F1": round(f1_score(ag.gold_intent, ag.pred_intent, labels=obs,
                                          average="macro", zero_division=0), 2),
        "escalate precision": round(tp / (tp + fp), 2),
        "escalate recall": round(tp / (tp + fn), 2),
        "missed escalations": fn,
        "reason-code accuracy": round((d.gold_reason == d.pred_reason).mean(), 2),
        "agent escalation rate": round(p.mean(), 2),
        "golden set size": len(
            [l for l in (GOLDEN / "labelled.jsonl").read_text().splitlines() if l.strip()]),
    }

    # second annotator, codebook v2
    sa_all = [json.loads(l) for l in (RESULTS / "second_annotator.jsonl").read_text().splitlines()]
    # Different denominators on purpose: the decision kappa is over items that
    # HAVE a human decision (39), the intent kappa over every item with a human
    # intent (40). Computing intent over the decision subset silently reported
    # 0.45 against the generated report's 0.43 -- caught by this script.
    sa_dec = [r for r in sa_all if str(r["h_decision"]) in ("auto", "escalate")]
    t["second-annotator decision kappa"] = round(
        cohen_kappa_score([r["h_decision"] for r in sa_dec],
                          [r["a_decision"] for r in sa_dec]), 2)
    t["second-annotator intent kappa"] = round(
        cohen_kappa_score([r["h_intent"] for r in sa_all],
                          [r["a_intent"] for r in sa_all]), 2)

    # retrieval ablation
    ab_path = RESULTS / "ablation_retrieval.jsonl"
    if ab_path.exists():
        ab = pd.DataFrame([json.loads(l) for l in ab_path.read_text().splitlines()])
        ab = ab[ab.decision_complete]
        ge, pe = ab.gold_decision == "escalate", ab.pred_decision == "escalate"
        t["ablation k=0 recall"] = round(
            int((ge & pe).sum()) / int(ge.sum()), 2)
    return t


# (label, value from truths(), regex that must find that value in the README)
CHECKS = [
    ("intent macro-F1",                 r"Intent macro-F1 \| \*\*([0-9.]+)\*\*"),
    ("escalate precision",              r"Escalate precision \| 0\.63 \| \*\*([0-9.]+)\*\*"),
    ("escalate recall",                 r"Escalate recall \| 0\.91 \| \*\*([0-9.]+)\*\*"),
    ("reason-code accuracy",            r"Reason-code accuracy \| 0\.27 \| \*\*([0-9.]+)\*\*"),
    ("second-annotator decision kappa", r"escalate / auto \| 41% \| \*\*0\.08\*\* \| \*\*90%\*\* \| \*\*([0-9.]+)\*\*"),
    ("ablation k=0 recall",             r"\*\*Escalate recall\*\* \| \*\*0\.73\*\* \| \*\*([0-9.]+)\*\*"),
]


def main() -> int:
    text = README.read_text()
    t = truths()
    bad = []
    print(f"Checking {len(CHECKS)} pinned claims in README.md against results/\n")
    for label, pattern in CHECKS:
        m = re.search(pattern, text)
        if not m:
            bad.append(f"{label}: claim not found in README "
                       f"(pattern {pattern!r}) -- the prose was reworded, so this "
                       f"check no longer pins anything")
            print(f"  MISSING  {label}")
            continue
        claimed, actual = float(m.group(1)), float(t[label])
        ok = abs(claimed - actual) < 0.005
        print(f"  {'OK      ' if ok else 'MISMATCH'} {label}: "
              f"README {claimed} vs computed {actual}")
        if not ok:
            bad.append(f"{label}: README says {claimed}, results say {actual}")

    print(f"\nOther values recomputed from the artifacts (not pinned to prose):")
    for k, v in t.items():
        if k not in dict(CHECKS):
            print(f"  {k}: {v}")

    if bad:
        print(f"\nFAILED -- {len(bad)} problem(s):")
        for b in bad:
            print(f"  {b}")
        return 1
    print("\nAll pinned claims match the committed results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
