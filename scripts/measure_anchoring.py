"""
Measures how much the verification pass anchored the reviewer.

The estimator, which needs no double-labelling:

  A = pre-labeller accuracy on the 40 BLIND items
      -- items the reviewer labelled from scratch, never having seen the guess.
      This is how often the rules are genuinely right.

  B = acceptance rate on the 158 VERIFY items
      -- how often the reviewer left the pre-label untouched.

If the reviewer were judging independently, B should approximate A. B - A is the
anchoring effect: the share of verified labels that were accepted because they
were already sitting there, not because they were right.

This number belongs in the report's "what is misleading about my headline
number" section, because every metric computed on the verified 158 inherits it.
"""
import json
from pathlib import Path

import pandas as pd

from src.config import GOLDEN, RESULTS

# Reads the DISCARDED verification pass, not the final golden set. Those 158
# labels were thrown away precisely because of what this script measures; the
# file is retained as the evidence for that decision.
LABELLED = GOLDEN / "verification_pass_discarded.jsonl"
OUT = RESULTS / "anchoring.md"


def main() -> None:
    if not LABELLED.exists():
        raise SystemExit(f"{LABELLED} not found -- export from golden/label.html first.")

    df = pd.DataFrame([json.loads(l) for l in LABELLED.read_text().splitlines()])
    df = df[df["confirmed"] & df["intent"].notna()]
    if df.empty:
        raise SystemExit("No confirmed labels yet.")

    blind = df[df["mode"] == "blind"]
    verify = df[df["mode"] == "verify"]

    lines = ["# Anchoring measurement\n"]
    if len(blind) < 10:
        lines.append(f"Only {len(blind)} blind items confirmed -- too few to estimate.\n")
    else:
        A_int = (blind["pre_intent"] == blind["intent"]).mean()
        A_dec = (blind["pre_decision"] == blind["decision"]).mean()
        lines += [
            f"**Blind items:** {len(blind)}  |  **Verify items:** {len(verify)}\n",
            "| Field | Pre-labeller accuracy (blind, A) | Acceptance rate (verify, B) | Anchoring (B-A) |",
            "|---|---|---|---|",
        ]
        if len(verify):
            B_int = (~verify["changed_from_prelabel"]).mean()
            B_dec = (verify["pre_decision"] == verify["decision"]).mean()
            lines += [
                f"| intent | {A_int:.1%} | {B_int:.1%} | **{B_int - A_int:+.1%}** |",
                f"| decision | {A_dec:.1%} | {B_dec:.1%} | **{B_dec - A_dec:+.1%}** |",
            ]
        lines += [
            "",
            "A positive gap means labels on the verified items were accepted more "
            "often than the pre-labeller is actually right -- i.e. the reviewer "
            "was anchored. Every metric computed on the verified subset inherits "
            "this bias, and it flatters any system whose errors resemble the "
            "pre-labeller's.",
            "",
            "Mitigation already in place: the pre-labeller is a keyword rule set, "
            "independent of both the Gemini agent (so no self-consistency loop) "
            "and of the simple baseline (which learns escalation rather than "
            "matching keywords).",
        ]

    # Timing, as evidence of how much attention each mode actually received.
    if "label_ms" in df:
        lines.append("\n## Time per item\n")
        t = df.assign(sec=df.label_ms / 1000).groupby("mode")["sec"].median().round(1)
        lines.append(t.to_frame("median_seconds").to_markdown())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
