"""
Does retrieval actually do anything?

The brief asks for replies "grounded in how that brand has historically resolved
similar issues", and this repo spends a whole component -- a 73k-document TF-IDF
index -- on that clause. Nothing so far has tested whether removing it changes
anything. An expensive component nobody has ablated is a component nobody knows
the value of.

This runs the SAME agent, prompt, model and temperature over the SAME 40 golden
items with k=0: no historical examples at all, taxonomy and policy only.

PREDICTION, recorded before the run (this is the point of writing it here):

  1. INTENT and ESCALATION barely move. Both are driven by the taxonomy and
     policy prose in the system prompt, not by the examples. Expect within a few
     points, i.e. inside the noise of n=40.
  2. REPLY GROUNDEDNESS drops clearly. It is the only output that depends on
     seeing what Apple actually said.
  3. FABRICATED URLs appear. With no <url>-bearing examples to copy the shape
     from, the model has to invent link text or omit it. The main run has a hard
     0% and the prompt forbids URLs explicitly, so this is the sharpest
     falsifiable claim here: if 0% survives k=0, the URL discipline comes from
     the instruction, not the grounding.

If (1) holds, the honest conclusion is that retrieval earns its place on replies
only, and the intent/escalation numbers in the report are NOT evidence that
retrieval works. That would be worth knowing and is not what the architecture
diagram implies.

Cost: 40 agent calls + 20 judge calls, all cached.
"""
import json

import pandas as pd
from sklearn.metrics import f1_score

from src.agent import run as agent_run
from src.config import GOLDEN, RESULTS
from src.evaluate import URL_RE, load_golden
from src.judge import score
from src.retrieve import load_or_build

OUT = RESULTS / "ablation_retrieval.md"


def main() -> None:
    gold = load_golden()
    retriever = load_or_build()
    base = pd.DataFrame([json.loads(l) for l in
                         (RESULTS / "predictions.jsonl").read_text().splitlines()])
    base = base[base.system == "agent"].set_index("pair_id")

    pinned = set(json.loads((GOLDEN / "judge_subsample.json").read_text())["pair_ids"])

    rows = []
    for n, (_, r) in enumerate(gold.iterrows(), 1):
        print(f"  [{n}/{len(gold)}] k=0  {r['customer_text'][:50]}...", flush=True)
        o = agent_run(r["customer_text"], retriever, k=0)
        rows.append({
            "pair_id": r["pair_id"],
            "gold_intent": r["intent"], "gold_decision": r["decision"],
            "gold_reason": r["reason"],
            "decision_complete": bool(r["decision_complete"]),
            "pred_intent": o.intent, "pred_decision": o.decision,
            "pred_reason": o.reason, "reply": o.reply,
            "fabricated_url": bool(URL_RE.search(o.reply)),
        })
    abl = pd.DataFrame(rows).set_index("pair_id")

    # Judge the same pinned subsample, so the comparison is paired.
    #
    # The judge is given the k=5 RETRIEVED EXAMPLES as its grounding reference
    # for both arms, not the ablated (empty) context. Groundedness asks "is this
    # reply supported by what Apple actually did" -- that reference has to be
    # held constant, or the k=0 arm would be graded against nothing and score
    # perfectly by default.
    for pid in sorted(pinned & set(abl.index)):
        ref = json.loads(base.at[pid, "retrieved"])
        s = score(base.at[pid, "customer_text"], abl.at[pid, "reply"], ref)
        print(f"  judged {pid}", flush=True)
        abl.loc[pid, "groundedness"] = s.groundedness
        abl.loc[pid, "judge_mean"] = s.mean

    def intent_f1(df, pred_col):
        obs = sorted(set(df["gold_intent"]))
        return f1_score(df["gold_intent"], df[pred_col], labels=obs,
                        average="macro", zero_division=0)

    common = sorted(set(abl.index) & set(base.index))
    b, a = base.loc[common], abl.loc[common]
    bd = b[b.decision_complete]
    ad = a[a.decision_complete]

    def esc(df):
        g, p = df.gold_decision == "escalate", df.pred_decision == "escalate"
        tp, fp, fn = (g & p).sum(), (~g & p).sum(), (g & ~p).sum()
        return (tp / (tp + fp) if tp + fp else 0.0,
                tp / (tp + fn) if tp + fn else 0.0, int(fn))

    bp, br, bfn = esc(bd)
    ap, ar, afn = esc(ad)

    lines = [
        "# Ablation: does retrieval do anything?\n",
        f"The same agent, prompt, model and temperature over the same "
        f"**{len(common)}** golden items, with **k=0** — no historical examples, "
        f"taxonomy and policy only. The prediction was written into "
        f"`scripts/ablate_retrieval.py` before the run.\n",
        "| Metric | k=5 (shipped) | k=0 (no retrieval) | Δ |",
        "|---|---|---|---|",
        f"| Intent macro-F1 | {intent_f1(b,'pred_intent'):.3f} | "
        f"{intent_f1(a,'pred_intent'):.3f} | "
        f"{intent_f1(a,'pred_intent')-intent_f1(b,'pred_intent'):+.3f} |",
        f"| Intent accuracy | {(b.gold_intent==b.pred_intent).mean():.3f} | "
        f"{(a.gold_intent==a.pred_intent).mean():.3f} | "
        f"{(a.gold_intent==a.pred_intent).mean()-(b.gold_intent==b.pred_intent).mean():+.3f} |",
        f"| Escalate precision | {bp:.2f} | {ap:.2f} | {ap-bp:+.2f} |",
        f"| Escalate recall | {br:.2f} | {ar:.2f} | {ar-br:+.2f} |",
        f"| Missed escalations | {bfn} | {afn} | {afn-bfn:+d} |",
        f"| Reason-code accuracy | {(bd.gold_reason==bd.pred_reason).mean():.3f} | "
        f"{(ad.gold_reason==ad.pred_reason).mean():.3f} | "
        f"{(ad.gold_reason==ad.pred_reason).mean()-(bd.gold_reason==bd.pred_reason).mean():+.3f} |",
        f"| **Fabricated URLs** | **{100*b.fabricated_url.mean():.0f}%** | "
        f"**{100*a.fabricated_url.mean():.0f}%** | "
        f"{100*(a.fabricated_url.mean()-b.fabricated_url.mean()):+.0f}pp |",
    ]

    jb = b[b.judge_mean.notna()]
    ja = a[a.judge_mean.notna()]
    if len(ja):
        lines.append(
            f"| Judge groundedness (n={len(ja)}) | {jb.groundedness.mean():.2f} | "
            f"{ja.groundedness.mean():.2f} | "
            f"{ja.groundedness.mean()-jb.groundedness.mean():+.2f} |")

    changed = [p for p in common if b.at[p, "pred_intent"] != a.at[p, "pred_intent"]]
    lines += [
        f"\nIntent changed on **{len(changed)} of {len(common)}** items; "
        f"decision changed on "
        f"**{sum(b.at[p,'pred_decision']!=a.at[p,'pred_decision'] for p in common)}**.\n",
        "\n## Two replies, side by side\n",
    ]
    for pid in sorted(pinned & set(abl.index))[:3]:
        lines += [f"\n**{b.at[pid,'customer_text'][:110] if 'customer_text' in b else pid}**",
                  f"\n- k=5: {b.at[pid,'reply']}",
                  f"- k=0: {a.at[pid,'reply']}"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    (RESULTS / "ablation_retrieval.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in
                  abl.reset_index().to_dict("records")) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
