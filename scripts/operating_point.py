"""
Turn the escalation metrics into the decision a support team actually makes.

The report asserts that costs are asymmetric -- "wrongly auto-handling a
locked-out customer loses them; wrongly escalating an easy one costs an agent
two minutes" -- and then never uses that asymmetry for anything. Precision and
recall are reported as if they were the answer. They are not: they are inputs to
a cost question, and which system you should deploy depends entirely on a ratio
nobody in this repo has written down.

This computes expected cost per 1,000 inbound messages across a range of
cost ratios R = (cost of a missed escalation) / (cost of a false escalation),
using the measured confusion counts. No new data, no LLM calls.

What it is honest about: the counts come from n=37 with 11 gold escalations, so
every number here inherits those intervals. The point is not the absolute cost.
It is (a) where the break-even against "escalate nothing" sits, and (b) that the
shipped configuration and the k=0 ablation swap places depending on R -- which
means "which system is better" is not answerable without the business input.
"""
import json

import numpy as np
import pandas as pd

from src.config import RESULTS

OUT = RESULTS / "operating_point.md"

# Deployment prevalence: the natural slice is the only unbiased estimate of how
# often a real inbound message needs a human. The targeted slice deliberately
# over-samples escalation-flavoured messages and must not set this.
def counts(df: pd.DataFrame) -> dict:
    g = df.gold_decision == "escalate"
    p = df.pred_decision == "escalate"
    return {"tp": int((g & p).sum()), "fp": int((~g & p).sum()),
            "fn": int((g & ~p).sum()), "tn": int((~g & ~p).sum()), "n": len(df)}


def main() -> None:
    preds = pd.DataFrame([json.loads(l) for l in
                          (RESULTS / "predictions.jsonl").read_text().splitlines()])
    preds = preds[preds.decision_complete]

    # NATURAL SLICE ONLY. Escalation prevalence is the number that scales every
    # cost below, and the pooled set is 30% only because the targeted slice
    # deliberately over-samples escalation-flavoured messages (46% there against
    # 21% natural). Using the pooled figure would inflate every row by ~40%
    # while looking like a deployment estimate.
    nat = preds[preds.slice == "natural"]

    systems = {}
    for name, g in nat.groupby("system"):
        systems[name] = counts(g)

    abl_path = RESULTS / "ablation_retrieval.jsonl"
    if abl_path.exists():
        a = pd.DataFrame([json.loads(l) for l in abl_path.read_text().splitlines()])
        nat_ids = set(nat.pair_id)
        a = a[a.decision_complete & a.pair_id.isin(nat_ids)]
        systems["agent (k=0, not shipped)"] = counts(a)

    base = systems["agent"]
    prevalence = (base["tp"] + base["fn"]) / base["n"]

    ratios = [1, 2, 5, 10, 20, 50, 100]
    lines = [
        "# Choosing an operating point\n",
        "The report says escalation costs are asymmetric and then never uses the "
        "asymmetry. Precision and recall are not the answer to \"should we deploy "
        "this\" -- they are inputs to a cost question whose other input is a "
        "business number this repo does not contain.\n",
        f"Let **R** = (cost of a missed escalation) / (cost of a false escalation). "
        f"Expected cost per **1,000 inbound messages** at the **natural-slice** "
        f"escalation prevalence of **{prevalence:.0%}** (n={base['n']}), in units "
        f"of one false escalation (≈ two minutes of agent time). The pooled "
        f"golden set reads 30%, but that includes the targeted slice, which "
        f"over-samples escalation-flavoured messages by design — using it would "
        f"inflate every row here while looking like a deployment estimate:\n",
    ]

    hdr = "| System | " + " | ".join(f"R={r}" for r in ratios) + " |"
    lines += [hdr, "|---" * (len(ratios) + 1) + "|"]

    table = {}
    for name, c in systems.items():
        row = []
        for r in ratios:
            # per-1000 cost = (false escalations + R * misses), scaled from n
            cost = (c["fp"] + r * c["fn"]) * 1000 / c["n"]
            row.append(cost)
        table[name] = row
        lines.append(f"| {name} | " + " | ".join(f"{v:,.0f}" for v in row) + " |")

    lines += [
        "\n`trivial` and `simple` escalate nothing, so their cost is purely "
        "R × every escalation that exists — the \"deploy no triage at all\" "
        "column.\n",
        "## What this changes\n",
    ]

    # Where does the agent beat "escalate nothing"?
    triv = table.get("trivial")
    ag = table["agent"]
    beats = [r for r, a_, t_ in zip(ratios, ag, triv) if a_ < t_]
    lines.append(
        f"**The agent beats escalating nothing at every R tested "
        f"({', '.join('R='+str(r) for r in beats)}).** "
        if len(beats) == len(ratios) else
        f"**The agent beats escalating nothing only for R ≥ {min(beats)}.** ")

    if "agent (k=0, not shipped)" in table:
        k0 = table["agent (k=0, not shipped)"]
        k5c, k0c = systems["agent"], systems["agent (k=0, not shipped)"]
        cheaper = [r for r, s_, k_ in zip(ratios, ag, k0) if k_ < s_]
        if len(cheaper) == len(ratios):
            n_esc = k5c["tp"] + k5c["fn"]
            lines.append(
                f"\n**The k=0 ablation is cheaper at every tested R, and there is "
                f"no crossover.** Same false escalations ({k0c['fp']} vs "
                f"{k5c['fp']}), fewer misses ({k0c['fn']} vs {k5c['fn']}), so it "
                f"dominates the shipped configuration at *any* cost ratio. Its row "
                f"is flat because it misses nothing on this slice, so its cost does "
                f"not grow with R at all.\n\n"
                f"**That flat row rests on one message.** The natural slice holds "
                f"{n_esc} gold escalations; k=5 misses one of them and k=0 misses "
                f"none. A single item is not a dominance result, and this table "
                f"would look completely different if that one message had gone the "
                f"other way. A crossover would have been the more useful outcome — "
                f"it would have made this a business question with a real answer. "
                f"What is actually here is a hint, at n={k5c['n']}, that retrieval "
                f"is not paying for itself, and not enough evidence to act on.")
        else:
            lines.append(
                f"\n**The shipped k=5 agent and the k=0 ablation swap places with R.** "
                f"k=0 is cheaper at {', '.join('R='+str(r) for r in cheaper)}; k=5 "
                f"elsewhere. So \"is retrieval worth keeping\" has no single answer — "
                f"the crossover is set by a number the business owns.")

    lines += [
        "\n## What this does not license\n",
        f"Every count here comes from **n={base['n']}** with "
        f"**{base['tp'] + base['fn']}** gold escalations. The escalation recall CI "
        f"is [0.45, 1.00]; propagating that through these costs would produce "
        f"intervals wider than the differences between the rows. This table shows "
        f"the *shape* of the decision and which input is missing. It does not "
        f"show which system to deploy, and it is not used to pick one.\n",
        "The missing input is a real cost ratio. For a support channel, R is "
        "usually estimated from the value of a retained customer against a "
        "loaded agent-minute — it is a number a support organisation already has, "
        "and it belongs in the config, not in a model.",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
