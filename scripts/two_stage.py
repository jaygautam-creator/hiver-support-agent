"""
Does splitting the call fix the weakest output?

The brief asks the agent to decide auto/escalate "with a stated reason". That
stated reason is the worst thing this system produces: the verdict is right 86%
of the time and the cited policy clause only 60% of the time, so a reviewer
auditing *why* is misled far more often than one auditing *what*.

The shipped agent emits intent, reply, decision and reason from ONE call. The
hypothesis is that this couples them: asked for a verdict and its justification
simultaneously, the model picks a plausible-sounding pair rather than deciding
first and then finding the clause that actually applies. Evidence that the
coupling is real already exists -- rewriting the escalation policy moved the
*replies* while retrieval was unchanged (README, Reply quality).

This runs a two-stage variant over the same 40 items:

  stage 1  message + taxonomy + policy      -> intent, decision          (no reason)
  stage 2  message + intent + decision + policy -> reason code, reply

PREDICTION, recorded before the run:

  1. REASON-CODE ACCURACY IMPROVES, 0.60 -> 0.70 or better. Stage 2 justifies a
     decision that is already fixed, so it cannot trade the code against the
     verdict to make the pair sound coherent.
  2. INTENT AND DECISION BARELY MOVE. Stage 1 sees exactly what the single call
     saw, minus the obligation to also produce a reason and a reply.
  3. REPLY QUALITY IS FLAT OR SLIGHTLY BETTER, for the same reason the policy
     rewrite moved it: less competing for the same output budget.

If (1) fails, the coupling hypothesis is wrong and the reason codes are limited
by something else -- most likely that the codes genuinely overlap on these
messages, which the second annotator's 62% code agreement would support.

Cost: 80 agent calls (2 per item). Not adopted on the strength of this run --
see the note at the end of the generated report.
"""
import json

import pandas as pd

from src.agent import SYSTEM as ONE_STAGE_SYSTEM, _prompt
from src.config import RESULTS
from src.llm import generate
from src.retrieve import load_or_build
from src.taxonomy import (AUTO_CODES, DISAMBIGUATION_RULES, ESCALATE_CODES,
                          ESCALATION_POLICY, INTENTS, LABELS, PRIORITY,
                          REASON_CODES)

OUT = RESULTS / "two_stage.md"

STAGE1_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": LABELS},
        "decision": {"type": "string", "enum": ["auto", "escalate"]},
    },
    "required": ["intent", "decision"],
}
STAGE2_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "enum": REASON_CODES},
        "reason_text": {"type": "string"},
        "reply": {"type": "string"},
    },
    "required": ["reason", "reason_text", "reply"],
}


def _taxonomy_block() -> str:
    return "\n".join(
        f"- {n}\n    definition: {d['definition']}\n"
        f"    includes:   {d['includes']}\n    excludes:   {d['excludes']}"
        for n, d in INTENTS.items())


STAGE1_SYSTEM = f"""You are a first-response triage agent for AppleSupport on Twitter.

Do TWO things for the incoming customer message: classify its intent, and decide
whether it can be auto-handled or must go to a human. Do not write a reply and do
not cite a policy code -- those come later, from a separate step.

INTENT TAXONOMY
{_taxonomy_block()}

DISAMBIGUATION RULES -- mechanical tests, apply them before judgement:
{DISAMBIGUATION_RULES}

When a message carries more than one intent, apply this priority order and pick
the first that fits: {" > ".join(PRIORITY)}

ESCALATION POLICY
{ESCALATION_POLICY}

Output must satisfy the provided JSON schema."""

STAGE2_SYSTEM = f"""You are a first-response triage agent for AppleSupport on Twitter.

The intent and the auto/escalate decision for this message have ALREADY BEEN
MADE by an earlier step and are given to you. They are fixed. Your job is to do
two things:

1. Cite the single policy code that justifies the decision you were given. An
   E-code must accompany `escalate` and an A-code must accompany `auto`; the
   decision is not yours to revisit, so pick the clause that actually applies to
   it rather than the one that would suit a different decision.
   Escalate codes: {", ".join(ESCALATE_CODES)}.  Auto codes: {", ".join(AUTO_CODES)}.

2. Draft Apple's first reply.

ESCALATION POLICY
{ESCALATION_POLICY}

REPLY RULES
- You are writing Apple's FIRST response on a public Twitter thread, not a
  resolution. Apple's historical pattern is to acknowledge, ask one diagnostic
  question, or point to a resource -- match that.
- Ground the reply in the historical examples provided. Do not invent support
  steps, article contents, phone numbers, or policies that do not appear there.
- Under 280 characters. No hashtags. No emoji.
- NEVER write a URL. Every link in the historical examples was replaced with the
  placeholder <url> during cleaning, so any URL you produce is fabricated. Write
  "<url>" where Apple would link, or refer to the resource in words.
- If escalating, the reply should set up the handoff rather than attempt a fix.
- Never ask for a password, payment details, or any credential.

Output must satisfy the provided JSON schema. `reason_text` is one short sentence
naming the specific signal in the message that triggers the code you chose."""


def run_two_stage(message, examples):
    s1 = json.loads(generate(
        f"INCOMING CUSTOMER MESSAGE:\n{message}",
        system=STAGE1_SYSTEM, json_schema=STAGE1_SCHEMA, temperature=0.0))
    s2 = json.loads(generate(
        f"{_prompt(message, examples)}\n\n{'=' * 60}\n"
        f"ALREADY DECIDED (fixed, do not change):\n"
        f"  intent:   {s1['intent']}\n  decision: {s1['decision']}",
        system=STAGE2_SYSTEM, json_schema=STAGE2_SCHEMA, temperature=0.0))
    return {**s1, **s2}


def main() -> None:
    preds = pd.DataFrame([json.loads(l) for l in
                          (RESULTS / "predictions.jsonl").read_text().splitlines()])
    base = preds[preds.system == "agent"].set_index("pair_id")
    retriever = load_or_build()

    rows = []
    for n, (pid, r) in enumerate(base.iterrows(), 1):
        print(f"  [{n}/{len(base)}] {r.customer_text[:50]}...", flush=True)
        o = run_two_stage(r.customer_text, retriever.query(r.customer_text, k=5))
        rows.append({"pair_id": pid, "gold_intent": r.gold_intent,
                     "gold_decision": r.gold_decision, "gold_reason": r.gold_reason,
                     "decision_complete": bool(r.decision_complete), **o})
    two = pd.DataFrame(rows).set_index("pair_id")

    from sklearn.metrics import f1_score
    obs = sorted(set(base.gold_intent))

    def block(df, icol, dcol, rcol):
        d = df[df.decision_complete]
        g, p = d[dcol] == "escalate", d[dcol] == "escalate"
        return {
            "intent_acc": (df.gold_intent == df[icol]).mean(),
            "intent_f1": f1_score(df.gold_intent, df[icol], labels=obs,
                                  average="macro", zero_division=0),
            "dec_acc": (d.gold_decision == d[dcol]).mean(),
            "reason_acc": (d.gold_reason == d[rcol]).mean(),
        }

    b = block(base, "pred_intent", "pred_decision", "pred_reason")
    t = block(two.assign(gold_intent=base.gold_intent,
                         gold_decision=base.gold_decision,
                         gold_reason=base.gold_reason),
              "intent", "decision", "reason")

    lines = [
        "# Two-stage: decide first, then justify\n",
        "The brief asks for a decision *with a stated reason*, and the stated "
        "reason is the weakest thing this system produces. The shipped agent "
        "emits intent, reply, decision and reason from one call; this variant "
        "splits it so stage 2 justifies a decision stage 1 has already fixed. "
        "The prediction was written into `scripts/two_stage.py` before the run.\n",
        "| Metric | 1 call (shipped) | 2 calls | Δ |",
        "|---|---|---|---|",
        f"| Intent accuracy | {b['intent_acc']:.3f} | {t['intent_acc']:.3f} | "
        f"{t['intent_acc']-b['intent_acc']:+.3f} |",
        f"| Intent macro-F1 | {b['intent_f1']:.3f} | {t['intent_f1']:.3f} | "
        f"{t['intent_f1']-b['intent_f1']:+.3f} |",
        f"| Decision accuracy | {b['dec_acc']:.3f} | {t['dec_acc']:.3f} | "
        f"{t['dec_acc']-b['dec_acc']:+.3f} |",
        f"| **Reason-code accuracy** | **{b['reason_acc']:.3f}** | "
        f"**{t['reason_acc']:.3f}** | **{t['reason_acc']-b['reason_acc']:+.3f}** |",
        f"\nCost: **2 calls per message instead of 1**.\n",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    (RESULTS / "two_stage.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False)
                  for r in two.reset_index().to_dict("records")) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
