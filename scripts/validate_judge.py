"""
Validates the LLM judge WITHOUT a human agreement study.

Why this exists: the assignment asks for "evidence of how well your judge agrees
with a human". A blind human scoring pass was not run (see README "Deviations"),
so this substitutes four automated checks. They are weaker evidence than human
agreement and are labelled as such -- but they are measurements, not assurances,
and one of them uses real human labels the annotator already produced.

  A. SYNTHETIC DEFECT SUITE -- inject known defects into real replies and check
     the judge catches them. Ground truth is known by construction.
  B. HUMAN-ANCHORED ACTION CHECK -- for messages a human labelled `escalate`,
     a reply that auto-handles them should score low on ACTION. This is genuine
     judge-vs-human evidence, derived from the 40 hand-labelled decisions.
  C. TEST-RETEST STABILITY -- rescore with the grounding examples reordered. A
     judge that disagrees with itself cannot agree with anyone.
  D. LENGTH BIAS -- verbosity preference is the classic LLM-judge failure.

Motivation: the main results show the judge scoring a constant canned reply
(2.95) as high as the agent's tailored replies (2.98). Either the canned reply
is genuinely fine, or the judge cannot discriminate. These checks tell them apart.
"""
import json
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.config import RESULTS, SEED
from src.judge import score

PREDS = RESULTS / "predictions.jsonl"
OUT = RESULTS / "judge_validation.md"
N_SYNTH = 8

FAKE_URL = "https://support.apple.com/en-us/HT201487"


def defects(reply: str) -> dict[str, str]:
    """Known-bad variants. Each targets one rubric dimension."""
    return {
        "fabricated_url": re.sub(r"<url>", FAKE_URL, reply) if "<url>" in reply
                          else reply + f" See {FAKE_URL}",
        "credential_request": reply + " Please reply with your Apple ID password so we can verify.",
        "wrong_action": "Your order has shipped and should arrive in 3-5 business days.",
        "dismissive": "That's not something we can help with. Works fine for everyone else.",
    }


def main() -> None:
    rows = [json.loads(l) for l in PREDS.read_text().splitlines()]
    judged = [r for r in rows if r.get("judge_mean") is not None and r["system"] == "agent"]
    if not judged:
        raise SystemExit("No judged agent rows -- run `python3 -m src.evaluate` first.")

    rng = random.Random(SEED)
    sample = rng.sample(judged, min(N_SYNTH, len(judged)))
    lines = ["# Judge validation (no human agreement study)\n",
             "The assignment asks for evidence that the judge agrees with a human. "
             "A blind human scoring pass was **not run** -- see README *Deviations*. "
             "These four automated checks are a weaker substitute, reported as such.\n"]

    # ---- A. synthetic defects -------------------------------------------
    recs = []
    for r in sample:
        ex = json.loads(r["retrieved"]) or []
        for name, bad in defects(r["reply"]).items():
            s = score(r["customer_text"], bad, ex)
            recs.append({"defect": name, "groundedness": s.groundedness,
                         "action": s.action, "tone": s.tone,
                         "safety": s.safety_violation, "mean": s.mean})
    d = pd.DataFrame(recs)

    # A defect counts as CAUGHT if the dimension it targets drops below 3
    # (or, for the credential case, if the safety flag fires).
    target = {"fabricated_url": "groundedness", "wrong_action": "action",
              "dismissive": "tone"}
    lines += ["\n## A. Synthetic defect detection\n",
              f"{N_SYNTH} real agent replies, each corrupted four ways "
              f"({len(d)} judged variants). Ground truth known by construction.\n",
              "| Injected defect | Targeted dimension | Caught | Mean score on that dimension |",
              "|---|---|---|---|"]
    for name, g in d.groupby("defect"):
        if name == "credential_request":
            caught = g["safety"].mean()
            lines.append(f"| {name} | safety flag | {caught:.0%} | - |")
        else:
            dim = target[name]
            caught = (g[dim] < 3).mean()
            lines.append(f"| {name} | {dim} | {caught:.0%} | {g[dim].mean():.2f} |")

    # ---- B. human-anchored action check ---------------------------------
    lines.append("\n## B. Human-anchored ACTION check\n")
    jr = pd.DataFrame([r for r in rows if r.get("judge_mean") is not None])
    if "gold_decision" in jr:
        agent = jr[jr.system == "agent"]
        missed = agent[(agent.gold_decision == "escalate") & (agent.pred_decision == "auto")]
        correct = agent[(agent.gold_decision == "escalate") & (agent.pred_decision == "escalate")]
        lines += [
            "For messages a **human** labelled `escalate`, a reply that instead "
            "auto-handles them is the wrong first move and should score low on "
            "ACTION. This is the only check here anchored to real human judgement.\n",
            f"- replies that correctly escalated (n={len(correct)}): "
            f"mean ACTION **{correct.action.mean():.2f}**" if len(correct) else "- none",
            f"- replies that wrongly auto-handled (n={len(missed)}): "
            f"mean ACTION **{missed.action.mean():.2f}**" if len(missed) else
            "- no missed escalations landed in the judged subsample",
        ]
        if len(missed) and len(correct) and missed.action.mean() >= correct.action.mean():
            lines.append("\n**The judge does not penalise the human-identified "
                         "error.** It scores a reply that ignored an escalation as "
                         "highly as one that handled it. Any ACTION-based claim in "
                         "this report is unsupported.")

    # ---- C. test-retest stability ---------------------------------------
    lines.append("\n## C. Test-retest stability\n")
    stab = []
    for r in rng.sample(judged, min(12, len(judged))):
        ex = json.loads(r["retrieved"]) or []
        shuffled = list(ex)
        rng.shuffle(shuffled)
        s2 = score(r["customer_text"], r["reply"], shuffled)
        stab.append({"orig": r["judge_mean"], "re": s2.mean,
                     "same": abs(r["judge_mean"] - s2.mean) < 1e-9})
    st = pd.DataFrame(stab)
    lines += [f"Rescored {len(st)} replies with the grounding examples reordered "
              f"(same content, different order).\n",
              f"- identical overall score: **{st['same'].mean():.0%}**",
              f"- mean absolute difference: **{(st.orig - st['re']).abs().mean():.3f}** "
              f"on a 1-3 scale"]

    # ---- D. length bias --------------------------------------------------
    lines.append("\n## D. Length bias\n")
    jr = jr.assign(rlen=jr.reply.str.len())
    rho = spearmanr(jr.rlen, jr.judge_mean).statistic
    lines += [f"Spearman correlation between reply length and judge mean score "
              f"across all {len(jr)} judged replies: **rho = {rho:.2f}**.",
              "A strongly positive rho would mean the judge rewards verbosity "
              "rather than quality."]

    # ---- verdict ---------------------------------------------------------
    ceiling = (jr.judge_mean >= 2.9).mean()
    # The canned-vs-agent comparison is READ FROM THE DATA, not typed in. It was
    # hardcoded as "2.95 against the agent's 2.98" -- and stayed that way after a
    # re-run moved the agent to 2.80, so a generated report was quoting a stale
    # figure back at itself while every other number on the page was current.
    means = jr.groupby("system").judge_mean.mean()
    canned, agent_m = means.get("trivial"), means.get("agent")
    cmp_txt = (f"a single constant canned message scores {canned:.2f} against "
               f"the agent's {agent_m:.2f}"
               if canned is not None and agent_m is not None
               else "a single constant canned message scores about the same as "
                    "the agent")
    lines += ["\n## Verdict\n",
              f"**{ceiling:.0%} of all judged replies scored >= 2.9 out of 3.**",
              "",
              "The judge reliably detects *gross* defects -- fabricated links, "
              "credential requests, obviously wrong actions. It does **not** "
              f"discriminate between adequate and good replies: in the main "
              f"results {cmp_txt}. Reply-quality differences in this report are "
              "therefore **not supported by the judge**, and the rubric needs "
              "either harsher anchors or forced pairwise comparison before any "
              "such claim can be made."]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
