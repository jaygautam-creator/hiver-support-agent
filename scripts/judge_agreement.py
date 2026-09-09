"""
Computes how well the LLM judge agrees with the human.

Reports three things, because any one alone is misleading:

  * exact agreement  -- intuitive, but inflated when one score dominates.
  * Cohen's kappa (quadratic weights) -- chance-corrected and ordinal-aware:
    scoring a 3 as a 1 is penalised more than scoring it a 2. This is the number
    the report leads with.
  * Spearman rho -- whether the judge RANKS replies the same way, which is what
    actually matters for comparing systems even if it is harsher or softer in
    absolute terms.

A judge with high exact agreement but low kappa is agreeing by accident because
almost everything scores 3. That case is called out explicitly.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

from src.config import GOLDEN, RESULTS

HUMAN = GOLDEN / "human_judge.jsonl"
PREDS = RESULTS / "predictions.jsonl"
OUT = RESULTS / "judge_agreement.md"

DIMS = [("groundedness", "h_groundedness"), ("action", "h_action"), ("tone", "h_tone")]


def main() -> None:
    if not HUMAN.exists():
        raise SystemExit(f"{HUMAN} not found -- score golden/judge_validation.html "
                         f"and move the export into golden/.")

    human = pd.DataFrame([json.loads(l) for l in HUMAN.read_text().splitlines()])
    human = human[human["h_groundedness"].notna()]
    if human.empty:
        raise SystemExit("No human scores yet.")

    preds = pd.DataFrame([json.loads(l) for l in PREDS.read_text().splitlines()])
    preds["uid"] = preds["pair_id"] + "::" + preds["system"]
    df = human.merge(preds, on="uid", how="inner")
    print(f"matched {len(df)} scored replies")

    lines = ["# LLM judge vs human agreement\n",
             f"**n = {len(df)}** replies, stratified across all three systems, "
             f"scored blind: the human never saw which system wrote a reply or "
             f"what the judge scored it.\n",
             "| Dimension | Exact | Cohen's kappa (quadratic) | Spearman rho | Judge mean | Human mean |",
             "|---|---|---|---|---|---|"]

    for llm_col, h_col in DIMS:
        a, b = df[llm_col].astype(int), df[h_col].astype(int)
        exact = (a == b).mean()
        try:
            k = cohen_kappa_score(a, b, weights="quadratic")
        except ValueError:
            k = float("nan")
        rho = spearmanr(a, b).statistic if a.nunique() > 1 and b.nunique() > 1 else float("nan")
        lines.append(f"| {llm_col} | {exact:.0%} | {k:.2f} | {rho:.2f} | "
                     f"{a.mean():.2f} | {b.mean():.2f} |")

    if "h_safety" in df and df["h_safety"].notna().any():
        s_a = df["safety_violation"].astype(bool)
        s_h = df["h_safety"].astype(bool)
        lines.append(f"| safety (binary) | {(s_a == s_h).mean():.0%} | "
                     f"{cohen_kappa_score(s_a, s_h):.2f} | - | "
                     f"{s_a.mean():.2f} | {s_h.mean():.2f} |")

    # The trap this exists to catch.
    lines.append("\n## Reading these numbers\n")
    for llm_col, h_col in DIMS:
        a = df[llm_col].astype(int)
        top = (a == 3).mean()
        if top > 0.8:
            lines.append(
                f"- **{llm_col}: the judge gave a 3 to {top:.0%} of replies.** "
                f"Exact agreement here is largely the two raters both defaulting "
                f"to the top score, not the judge discriminating quality. Treat "
                f"this dimension's agreement as weak evidence regardless of the "
                f"headline percentage.")
    lines.append(
        "\nkappa < 0.4 = poor, 0.4-0.6 = moderate, 0.6-0.8 = substantial. Any "
        "reply-quality claim in this report is only as trustworthy as the kappa "
        "for the dimension it rests on."
    )

    # Where they disagree most -- the useful diagnostic.
    df["gap"] = sum(abs(df[c].astype(int) - df[h].astype(int)) for c, h in DIMS)
    worst = df.nlargest(5, "gap")
    lines.append("\n## Largest disagreements\n")
    for _, r in worst.iterrows():
        lines.append(
            f"\n- **{r.customer_text[:130]}**\n"
            f"  - reply: {r.reply[:150]}\n"
            f"  - judge G/A/T: {r.groundedness}/{r.action}/{r.tone} "
            f"vs human: {int(r.h_groundedness)}/{int(r.h_action)}/{int(r.h_tone)}\n"
            f"  - judge note: {r.judge_note}")

    OUT.write_text("\n".join(lines))
    print("\n".join(lines[:14]))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
