"""
The evaluation harness. Produces every number in the report.

SAMPLE SIZE: the usable golden set is 40 hand-labelled examples, below the
assignment's 150 minimum. See README "Deviations". Three consequences are
handled here rather than glossed over:

  * The simple baseline is fitted by 5-fold cross-validation and scored on
    out-of-fold predictions, instead of a train/test split. At n=40 a fixed
    split would leave ~10 training labels and ~30 test items, which is worse on
    both ends. Every item still gets a prediction from a model that never saw it.
    Note this if anything FAVOURS the simple baseline, which sees in-domain
    labels while the agent is zero-shot -- so the comparison is conservative
    towards the agent, not generous.

  * Every headline number carries a bootstrap 95% confidence interval. At n=40
    a point estimate on its own is close to meaningless, and quoting one without
    an interval is the single easiest way to mislead.

  * Macro-F1 is computed over OBSERVED classes only. `how_to` and
    `billing_or_purchase` have zero examples in the 40, so they are unmeasured,
    not "perfect" or "zero" -- averaging them in either direction would be a
    fabricated number.

Structure mirrors the three things the agent does, because "results vs. two
baselines" is only meaningful if all three tasks are measured:

  1. INTENT      macro-F1 (not accuracy) + per-class + confusion pairs
  2. ESCALATION  precision/recall on the ESCALATE class specifically
  3. REPLY       LLM-judge rubric + an automated fabricated-URL rate

Reported separately on the natural and targeted slices. They are never pooled
into a single headline, because the targeted slice deliberately distorts class
prevalence and any pooled number inherits that distortion.

Macro-F1 rather than accuracy throughout: on a corpus where one class is ~40%
of traffic, accuracy mostly measures the prior.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold

from src.baselines import SimpleBaseline, TrivialBaseline
from src.config import GOLDEN, RESULTS
from src.retrieve import load_or_build
from src.taxonomy import LABELS

LABELLED = GOLDEN / "labelled.jsonl"
URL_RE = re.compile(r"https?://")


def bootstrap_ci(values: np.ndarray, stat, n_boot: int = 2000,
                 seed: int = 20260909) -> tuple[float, float]:
    """Percentile bootstrap 95% CI. Mandatory at n=40."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    draws = np.array([stat(values[i]) for i in idx])
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def load_golden() -> pd.DataFrame:
    if not LABELLED.exists():
        raise SystemExit(
            f"{LABELLED} not found.\n"
            f"Label golden/label.html in a browser, click Export, and move the "
            f"downloaded labelled.jsonl into golden/."
        )
    rows = [json.loads(l) for l in LABELLED.read_text().splitlines()]
    df = pd.DataFrame(rows)

    df = df[df["intent"].notna()].reset_index(drop=True)
    # Three items were confirmed in the labelling UI without a decision (a bug in
    # that tool: confirm was not gated on completeness). They still carry a valid
    # intent, so they are kept for intent scoring and excluded from escalation
    # scoring, rather than dropped entirely or silently imputed.
    df["decision_complete"] = df["decision"].notna() & df["reason"].notna()
    n_inc = int((~df["decision_complete"]).sum())
    if n_inc:
        print(f"  {n_inc} items lack a decision -- scored for intent only")
    return df


def simple_oof(gold: pd.DataFrame, retriever) -> dict[str, "object"]:
    """Out-of-fold predictions for the simple baseline (5-fold stratified CV).

    Classes with fewer than 2 examples cannot be stratified, so folds are built
    on a collapsed label that groups singletons together; the model still trains
    on the true labels.
    """
    counts = gold["intent"].value_counts()
    strat = gold["intent"].where(gold["intent"].map(counts) >= 5, "_rare")
    n_splits = min(5, strat.value_counts().min())
    preds: dict[str, object] = {}

    if n_splits < 2:
        raise SystemExit("Too few labels per class for cross-validation.")

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=20260909)
    for tr_i, te_i in skf.split(gold, strat):
        tr = gold.iloc[tr_i]
        tr = tr[tr["decision_complete"]] if len(tr[tr["decision_complete"]]) > 5 else tr
        model = SimpleBaseline(tr.assign(decision=tr["decision"].fillna("auto")), retriever)
        for _, r in gold.iloc[te_i].iterrows():
            preds[r["pair_id"]] = model.run(r["customer_text"])
    print(f"  simple baseline: {n_splits}-fold CV, {len(preds)} out-of-fold predictions")
    return preds


def run_systems(gold: pd.DataFrame) -> pd.DataFrame:
    """Run all three systems over every golden example."""
    from src.agent import run as agent_run

    retriever = load_or_build()
    trivial = TrivialBaseline(majority_intent=Counter(gold["intent"]).most_common(1)[0][0])
    simple_preds = simple_oof(gold, retriever)

    out = []
    for n, (_, r) in enumerate(gold.iterrows(), 1):
        msg = r["customer_text"]
        print(f"  [{n}/{len(gold)}] {msg[:55]}...", flush=True)

        t = trivial.run(msg)
        s = simple_preds[r["pair_id"]]
        a = agent_run(msg, retriever)

        for name, o, retrieved in (("trivial", t, []),
                                   ("simple", s, []),
                                   ("agent", a, a.retrieved)):
            out.append({
                "pair_id": r["pair_id"], "slice": r["slice"],
                "decision_complete": bool(r["decision_complete"]),
                "customer_text": msg,
                "gold_intent": r["intent"], "gold_decision": r["decision"],
                "gold_reason": r["reason"],
                "system": name,
                "pred_intent": o.intent, "pred_decision": o.decision,
                "pred_reason": o.reason, "pred_reason_text": o.reason_text,
                "reply": o.reply,
                "retrieved": json.dumps(retrieved),
                "fabricated_url": bool(URL_RE.search(o.reply)),
            })
    return pd.DataFrame(out)


def judge_replies(preds: pd.DataFrame, workers: int = 3,
                  n_messages: int = 20) -> pd.DataFrame:
    """Score every reply. Calls are independent, so they run concurrently.

    Serially this is ~25s x 120 calls = 50 minutes. A few workers hide the judge
    model's latency, but the free tier is RATE limited, not concurrency limited:
    6 workers at a 1s interval produced 42 retries and no completed calls. So the
    global interval in src/llm.py caps the rate and the pool only fills the gaps.
    Results are reassembled by index, never by completion order.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from src.judge import score

    # PAIRED SUBSAMPLE. Judging every message x 3 systems is beyond the free
    # tier's daily quota. Judging a subset of MESSAGES and scoring all three
    # systems on each preserves the paired design -- every system is compared on
    # identical inputs, which is what makes the comparison valid -- while cutting
    # the call count. Dropping whole systems, or sampling replies independently,
    # would break the pairing.
    #
    # PINNED, NOT REDRAWN. The ids live in golden/judge_subsample.json. They were
    # drawn at random, but they are now fixed: when the golden set grew 40 -> 198
    # a redraw shared 0 of 20 ids with the cached set, which would have burned
    # all 60 judge calls to re-answer a question already settled (the judge is
    # saturated; see results/judge_validation.md) . The pinned ids are still a
    # uniform random subsample of the full set -- see that file's _comment.
    ids = sorted(preds["pair_id"].unique())
    pin_path = GOLDEN / "judge_subsample.json"
    keep = None
    if pin_path.exists():
        pinned = set(json.loads(pin_path.read_text())["pair_ids"])
        keep = pinned & set(ids)
        missing = pinned - set(ids)
        if missing:
            print(f"  WARNING: {len(missing)} pinned judge ids absent from the "
                  f"golden set; judging {len(keep)} messages")
    if keep is None and n_messages < len(ids):
        rng = np.random.default_rng(20260909)
        keep = set(rng.choice(ids, size=n_messages, replace=False))

    if keep is not None:
        judged = preds[preds["pair_id"].isin(keep)].copy()
        print(f"  judging a pinned paired subsample: {len(keep)} of {len(ids)} "
              f"messages x 3 systems = {len(judged)} calls "
              f"(free-tier daily quota)")
    else:
        judged = preds.copy()

    rows = list(judged.itertuples(index=False))
    agent_ctx = {r.pair_id: r.retrieved for r in rows if r.system == "agent"}
    done = [0]
    done_lock = threading.Lock()

    def one(item):
        i, r = item
        ex = json.loads(r.retrieved) or json.loads(agent_ctx.get(r.pair_id, "[]"))
        s = score(r.customer_text, r.reply, ex)
        with done_lock:
            done[0] += 1
            n = done[0]
        print(f"  judged {n}/{len(rows)}", flush=True)
        return i, {"groundedness": s.groundedness, "action": s.action,
                   "tone": s.tone, "safety_violation": s.safety_violation,
                   "judge_note": s.note, "judge_mean": s.mean}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, enumerate(rows)))

    scores = [d for _, d in sorted(results, key=lambda t: t[0])]
    scored = pd.concat([judged.reset_index(drop=True), pd.DataFrame(scores)], axis=1)
    # Left-join back so unjudged rows keep their intent/escalation metrics and
    # simply carry NaN judge columns.
    return preds.merge(
        scored[["pair_id", "system", "groundedness", "action", "tone",
                "safety_violation", "judge_note", "judge_mean"]],
        on=["pair_id", "system"], how="left")


def intent_table(df: pd.DataFrame, slice_name: str | None = None) -> pd.DataFrame:
    d = df if slice_name is None else df[df["slice"] == slice_name]
    rows = []
    for sysname, g in d.groupby("system"):
        # Only classes actually present in the gold labels. Absent classes are
        # unmeasured; averaging them in as 0 (or omitting silently) invents a
        # number either way.
        observed = sorted(set(g.gold_intent))
        correct = (g.gold_intent.values == g.pred_intent.values).astype(float)
        lo, hi = bootstrap_ci(correct, np.mean)

        pairs = np.array(list(zip(g.gold_intent, g.pred_intent)), dtype=object)
        f1_lo, f1_hi = bootstrap_ci(
            pairs, lambda a: f1_score(list(a[:, 0]), list(a[:, 1]),
                                      labels=observed, average="macro",
                                      zero_division=0))
        rows.append({
            "system": sysname,
            "n": len(g),
            "accuracy": round(correct.mean(), 3),
            "acc_95CI": f"[{lo:.2f}, {hi:.2f}]",
            "macro_f1": round(f1_score(g.gold_intent, g.pred_intent, labels=observed,
                                       average="macro", zero_division=0), 3),
            "f1_95CI": f"[{f1_lo:.2f}, {f1_hi:.2f}]",
            "classes_measured": len(observed),
        })
    return pd.DataFrame(rows).sort_values("macro_f1", ascending=False)


def escalation_table(df: pd.DataFrame, slice_name: str | None = None) -> pd.DataFrame:
    d = df[df["decision_complete"]]
    d = d if slice_name is None else d[d["slice"] == slice_name]
    rows = []
    for sysname, g in d.groupby("system"):
        gold_e = g.gold_decision == "escalate"
        pred_e = g.pred_decision == "escalate"
        tp = (gold_e & pred_e).sum()
        fp = (~gold_e & pred_e).sum()
        fn = (gold_e & ~pred_e).sum()
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        # Recall CI over the gold-escalate items only -- that is the population
        # the recall claim is about, and at n=11 it is very wide. Saying so is
        # the point.
        hits = (pred_e[gold_e]).values.astype(float)
        r_lo, r_hi = bootstrap_ci(hits, np.mean) if len(hits) else (0.0, 0.0)
        rows.append({
            "system": sysname,
            "escalate_precision": round(prec, 3),
            "escalate_recall": round(rec, 3),
            "recall_95CI": f"[{r_lo:.2f}, {r_hi:.2f}]",
            "escalate_f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0,
            # The costly error: a message a human should have seen, auto-handled.
            "missed_escalations": int(fn),
            "n_gold_escalate": int(gold_e.sum()),
            "reason_code_acc": round((g.gold_reason == g.pred_reason).mean(), 3),
        })
    return pd.DataFrame(rows).sort_values("escalate_recall", ascending=False)


def reply_table(df: pd.DataFrame) -> pd.DataFrame:
    if "judge_mean" not in df.columns:
        return pd.DataFrame()
    df = df[df["judge_mean"].notna()]
    if df.empty:
        return pd.DataFrame()
    rows = []
    for sysname, g in df.groupby("system"):
        rows.append({
            "system": sysname,
            "n_judged": len(g),
            "groundedness": round(g.groundedness.mean(), 2),
            "action": round(g.action.mean(), 2),
            "tone": round(g.tone.mean(), 2),
            "judge_mean": round(g.judge_mean.mean(), 2),
            "safety_violations": int(g.safety_violation.sum()),
            "fabricated_url_%": round(100 * g.fabricated_url.mean(), 1),
        })
    return pd.DataFrame(rows).sort_values("judge_mean", ascending=False)


def dump_errors(df: pd.DataFrame) -> None:
    d = RESULTS / "errors"
    d.mkdir(parents=True, exist_ok=True)
    ag = df[df.system == "agent"]

    wrong = ag[ag.gold_intent != ag.pred_intent]
    pairs = Counter(zip(wrong.gold_intent, wrong.pred_intent))
    lines = ["# Intent errors, grouped by confusion pair\n"]
    for (g, p), n in pairs.most_common():
        lines.append(f"\n## {g} -> {p}  ({n})\n")
        for _, r in wrong[(wrong.gold_intent == g) & (wrong.pred_intent == p)].iterrows():
            lines.append(f"- `{r.pair_id}` {r.customer_text[:200]}")
    (d / "intent_confusions.md").write_text("\n".join(lines))

    missed = ag[(ag.gold_decision == "escalate") & (ag.pred_decision == "auto")]
    lines = ["# Missed escalations -- the costly error\n"]
    for _, r in missed.iterrows():
        lines.append(f"\n- **{r.customer_text[:220]}**")
        lines.append(f"  - gold `{r.gold_reason}` / agent said `{r.pred_reason}`: {r.pred_reason_text}")
        lines.append(f"  - reply: {r.reply}")
    (d / "missed_escalations.md").write_text("\n".join(lines))
    print(f"  wrote {d}/intent_confusions.md and missed_escalations.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true", help="skip LLM judging")
    args = ap.parse_args()

    gold = load_golden()
    print(f"Evaluating on all {len(gold)} hand-labelled examples "
          f"(cross-validated; no held-out split at this sample size)")

    preds = run_systems(gold)
    if not args.no_judge:
        preds = judge_replies(preds)

    RESULTS.mkdir(parents=True, exist_ok=True)
    preds.to_json(RESULTS / "predictions.jsonl", orient="records", lines=True)

    parts = ["# Results\n",
             f"**n = {len(gold)}** hand-labelled examples "
             f"({int(gold.decision_complete.sum())} with a decision label). "
             f"Simple baseline scored on out-of-fold cross-validated predictions.\n",
             "All intervals are percentile bootstrap 95% CIs over 2000 resamples. "
             "At this sample size the intervals, not the point estimates, are the "
             "result -- see the README's *What is misleading about my headline "
             "number* section.\n",
             f"Classes with zero gold examples "
             f"({', '.join(sorted(set(LABELS) - set(gold.intent)))}) are "
             f"**unmeasured** and excluded from macro-F1.\n"]
    # Sizes are read off the data, never hardcoded: these titles said "all 40"
    # / "n=24" / "n=16" as literals, so growing the golden set would have
    # relabelled the tables with the old counts while the numbers underneath
    # changed.
    n_nat = int((gold["slice"] == "natural").sum())
    n_tgt = int((gold["slice"] == "targeted").sum())
    for title, tbl in [
        (f"Intent -- all {len(gold)}", intent_table(preds)),
        (f"Intent -- natural slice (deployment estimate, n={n_nat})",
         intent_table(preds, "natural")),
        (f"Intent -- targeted slice (diagnostic only, n={n_tgt})",
         intent_table(preds, "targeted")),
        ("Escalation -- all", escalation_table(preds)),
        ("Reply quality", reply_table(preds)),
    ]:
        if len(tbl):
            parts += [f"\n## {title}\n", tbl.to_markdown(index=False), ""]

    ag = preds[preds.system == "agent"]
    if len(ag):
        cm = confusion_matrix(ag.gold_intent, ag.pred_intent, labels=LABELS)
        parts += ["\n## Agent confusion matrix (rows = gold)\n",
                  pd.DataFrame(cm, index=LABELS, columns=LABELS).to_markdown(), ""]
        parts += ["\n## Agent per-class intent report\n", "```",
                  classification_report(ag.gold_intent, ag.pred_intent,
                                        zero_division=0), "```"]

    (RESULTS / "main_table.md").write_text("\n".join(parts))
    dump_errors(preds)
    print(f"\nWrote {RESULTS/'main_table.md'}")
    print("\n" + "\n".join(parts[:40]))


if __name__ == "__main__":
    main()
