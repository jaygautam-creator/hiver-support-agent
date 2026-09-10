"""
An INDEPENDENT MODEL relabels the golden set, and its labels are compared to the
human's.

WHAT THIS IS NOT
----------------
This is not a second human annotator, and it does not make the golden set more
correct. Two raters who both read the same written definitions can agree
perfectly and still both be wrong about the underlying task. Nothing here
validates the human labels.

WHAT IT ACTUALLY MEASURES
-------------------------
How unambiguous the taxonomy is. The annotator model is given exactly what the
human labeller was given -- the same intent definitions, the same disambiguation
rules, the same escalation policy codes, and the customer message with Apple's
reply withheld -- and nothing else. It drafts no reply and retrieves no
examples, so it is doing the human's task, not the agent's.

On that setup, a disagreement is a signal about the *definitions*: an item where
an independent reader applying the same written rules lands somewhere else is an
item whose label depends on something the rules do not say. That is the same
failure the 20-item pilot found by hand (LABELLING_NOTE.md), found cheaply and
at scale. The per-item disagreement list at the bottom of the report is the
useful output: it is a re-review queue for the human, not a verdict.

DELIBERATE CHOICES
------------------
  * A DIFFERENT MODEL FAMILY. The annotator is Gemma, not Gemini. The agent and
    judge are both Gemini, and the report already concedes that as a judge
    limitation. Using a Gemini model here would make "the annotator agrees with
    the agent" partly an artifact of shared lineage. It also spends a separate
    free-tier quota from both.
  * NOT the agent's prompt. The agent's prompt includes retrieved historical
    examples and a reply-drafting instruction. Reusing it would measure whether
    the agent agrees with the human -- which is just the headline result again,
    not an independent reading of the taxonomy.
  * Apple's reply is withheld, because it was withheld from the human. Showing
    it would let the annotator infer the label from Apple's behaviour.
  * Intent order is shuffled per item under a frozen seed, so the annotator
    cannot be agreeing by position bias.

Run: make second-annotator
"""
import argparse
import json
import random
from collections import Counter

import numpy as np
from sklearn.metrics import cohen_kappa_score, f1_score

from src.config import GOLDEN, RESULTS, SEED
from src.llm import generate
from src.taxonomy import (AUTO_CODES as TAXONOMY_AUTO_CODES,
                          ESCALATE_CODES,
                          DISAMBIGUATION_RULES, ESCALATION_POLICY, INTENTS,
                          LABELS, PRIORITY)

# A third family, on purpose. See DELIBERATE CHOICES above.
ANNOTATOR_MODEL = "gemma-4-31b-it"

OUT = RESULTS / "second_annotator.md"
PREDS = RESULTS / "second_annotator.jsonl"

# Imported, not re-typed -- see src/taxonomy.py.
ESC_CODES = list(ESCALATE_CODES)
AUTO_CODES = list(TAXONOMY_AUTO_CODES)

SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": LABELS},
        "decision": {"type": "string", "enum": ["auto", "escalate"]},
        "reason": {"type": "string", "enum": ESC_CODES + AUTO_CODES},
    },
    "required": ["intent", "decision", "reason"],
}


def _intent_block(order: list[str]) -> str:
    out = []
    for name in order:
        d = INTENTS[name]
        out.append(f"- {name}\n"
                   f"    definition: {d['definition']}\n"
                   f"    includes:   {d['includes']}\n"
                   f"    excludes:   {d['excludes']}")
    return "\n".join(out)


def _policy_block() -> str:
    # ESCALATION_POLICY is the same prose block injected into the agent prompt
    # and rendered in the labelling UI -- one source of truth, used verbatim so
    # the annotator reads exactly what the human read.
    return ESCALATION_POLICY


SYSTEM = """You are labelling a dataset of customer support messages sent to
AppleSupport on Twitter. You are the second annotator: another annotator has
already labelled these independently, and you must not try to guess what they
chose -- label what the written definitions actually say.

You do NOT write a reply. You do NOT see what Apple actually replied. You assign
three fields and nothing else.

Apply the definitions literally. Where a message could fit two intents, use the
stated priority order rather than your own preference. If a message is genuinely
unintelligible, that is what the 'other' intent and the A5 code are for -- an
unintelligible message is auto-handled with one clarifying question, not
escalated."""


def build_prompt(text: str, order: list[str]) -> str:
    return f"""INTENT DEFINITIONS (exactly one applies):
{_intent_block(order)}

DISAMBIGUATION RULES (these override your intuition):
{DISAMBIGUATION_RULES}

PRIORITY ORDER for messages that fit more than one intent
(earlier wins):
{" > ".join(PRIORITY)}

DECISION: 'escalate' if the message needs a human, 'auto' if a first reply can
be sent without one. Then cite exactly one policy code:
{_policy_block()}

Use an E-code with 'escalate' and an A-code with 'auto'. Never mix them.

CUSTOMER MESSAGE:
\"\"\"{text}\"\"\"

Return JSON with keys: intent, decision, reason."""


def _parse(raw: str) -> dict | None:
    """Tolerant JSON parse.

    Gemma appends a stray closing markdown fence even under schema-constrained
    decoding -- `{"intent": ...}\n```' -- which is valid JSON followed by junk.
    A strict json.loads() rejects it, and a strict parse here would have dropped
    roughly a third of the items while looking like a model failure rather than
    a parsing bug. raw_decode takes the first complete JSON value and ignores
    whatever trails it.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    if not all(k in obj for k in ("intent", "decision", "reason")):
        return None
    return obj


def annotate(rows: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    out: list[dict] = []
    unparsed: list[dict] = []
    failed: list[dict] = []
    for n, r in enumerate(rows, 1):
        order = LABELS[:]
        rng.shuffle(order)
        try:
            raw = generate(
                build_prompt(r["customer_text"], order),
                model=ANNOTATOR_MODEL,
                system=SYSTEM,
                temperature=0.0,
                json_schema=SCHEMA,
                max_output_tokens=256,
            )
        except Exception as e:  # noqa: BLE001
            # One item dying must not discard the whole pass. Gemma's free-tier
            # quota is the binding constraint here and it is exhausted partway
            # through a 40-item run, so the run is built to stop cleanly and
            # report on what it got: every completed call is already on disk in
            # the cache, and re-running resumes from there at zero cost. A run
            # that crashed instead would throw away a partial result that is
            # still informative, and the shortfall is reported in the output
            # rather than hidden.
            failed.append({"pair_id": r["pair_id"], "error": str(e)[:200]})
            print(f"  [{n}/{len(rows)}] FAILED ({type(e).__name__}): "
                  f"{str(e)[:120]}", flush=True)
            if len(failed) >= 3:
                print(f"  stopping: {len(failed)} consecutive failures, quota is "
                      f"likely exhausted. Re-run later to resume from cache.",
                      flush=True)
                break
            continue
        failed.clear()  # only CONSECUTIVE failures signal exhaustion
        a = _parse(raw)
        if a is None:
            # Counted and reported, never silently dropped: items that fail to
            # parse are not missing at random -- they would be the hardest ones,
            # and quietly discarding them inflates agreement.
            print(f"  [{n}/{len(rows)}] UNPARSEABLE, recorded: {raw[:80]!r}")
            unparsed.append({"pair_id": r["pair_id"], "raw": raw})
            continue
        out.append({
            "pair_id": r["pair_id"],
            "customer_text": r["customer_text"],
            "slice": r.get("slice"),
            "h_intent": r["intent"],
            "h_decision": r.get("decision"),
            "h_reason": r.get("reason"),
            "a_intent": a["intent"],
            "a_decision": a["decision"],
            "a_reason": a["reason"],
        })
        print(f"  [{n}/{len(rows)}] {r['pair_id']}  "
              f"human={r['intent']}/{r.get('decision')}  "
              f"annotator={a['intent']}/{a['decision']}", flush=True)
    if unparsed:
        print(f"  {len(unparsed)} of {len(rows)} responses unparseable")
    globals()["_UNPARSED"] = unparsed
    globals()["_ATTEMPTED"] = len(rows)
    return out


def _kappa(a, b) -> float:
    try:
        return cohen_kappa_score(a, b)
    except ValueError:
        return float("nan")


def report(rows: list[dict]) -> str:
    n = len(rows)
    hi = [r["h_intent"] for r in rows]
    ai = [r["a_intent"] for r in rows]
    i_agree = np.mean([x == y for x, y in zip(hi, ai)])
    i_kappa = _kappa(hi, ai)
    i_f1 = f1_score(hi, ai, average="macro", zero_division=0)

    # The eval harness (src/evaluate.py) scores escalation only on rows with a
    # decision AND a reason (n=37). Here the decision comparison needs only a
    # decision (n=39); the reason comparison applies the stricter filter below.
    # Stated because the two n's differ on purpose.
    dec = [r for r in rows if r["h_decision"] in ("auto", "escalate")]
    hd = [r["h_decision"] for r in dec]
    ad = [r["a_decision"] for r in dec]
    d_agree = np.mean([x == y for x, y in zip(hd, ad)]) if dec else float("nan")
    d_kappa = _kappa(hd, ad) if dec else float("nan")

    # NOT `if r["h_reason"]`: three golden rows carry a float NaN reason (round
    # 1's ungated confirm button), and NaN is TRUTHY in Python. Those rows would
    # pass a plain truthiness filter and then never match anything, silently
    # deflating the agreement below. Require an actual policy code.
    def _code(v) -> bool:
        return isinstance(v, str) and v[:1] in ("E", "A")

    both = [r for r in dec if _code(r["h_reason"]) and _code(r["a_reason"])]
    r_agree = (np.mean([r["h_reason"] == r["a_reason"] for r in both])
               if both else float("nan"))

    L = [
        "# Second annotator: an independent model relabels the golden set\n",
        f"Annotator model: `{ANNOTATOR_MODEL}` — a **different model family** "
        f"from both the agent (`gemini-3.1-flash-lite`) and the judge "
        f"(`gemini-3.5-flash-lite`), so agreement here is not an artifact of "
        f"shared lineage.\n",
        "## This is not a human agreement study\n",
        "The brief asks for human agreement, and this is not it. Two raters "
        "reading the same written definitions can agree perfectly and both be "
        "wrong; nothing below shows the human labels are *correct*. "
        "`golden/human_judge.jsonl` is still unfilled and the gap is still open "
        "in the README.\n",
        "What this measures is **how unambiguous the taxonomy is**. The "
        "annotator got exactly what the human got — same definitions, same "
        "disambiguation rules, same policy codes, Apple's reply withheld, no "
        "retrieved examples, no reply to draft. So a disagreement points at the "
        "*definitions*, not at either rater.\n",
        f"**n = {n}** items"
        + (f" of {globals()['_ATTEMPTED']} attempted — the run stopped early on "
           f"free-tier quota exhaustion, so this covers "
           f"{n / globals()['_ATTEMPTED']:.0%} of the golden set and every "
           f"number below is correspondingly thin. Completed calls are cached; "
           f"re-running `make second-annotator` resumes at zero cost."
           if globals().get("_ATTEMPTED") and n < globals()["_ATTEMPTED"]
           else " (every golden item carrying a human intent)") + "\n",
        *([f"> {len(globals().get('_UNPARSED', []))} response(s) could not be "
           f"parsed and are excluded from every number above; they are listed at "
           f"the end. Non-parsing items are not missing at random, so the "
           f"exclusion is reported rather than absorbed.\n"]
          if globals().get("_UNPARSED") else []),
        "| Field | Agreement | Cohen's kappa | Notes |",
        "|---|---|---|---|",
        f"| intent (7 classes) | {i_agree:.0%} | {i_kappa:.2f} | macro-F1 vs human {i_f1:.2f} |",
        f"| decision (auto/escalate) | {d_agree:.0%} | {d_kappa:.2f} | n={len(dec)} with a human decision |",
        f"| policy reason code | {r_agree:.0%} | — | n={len(both)}, exact code match |",
        "\nkappa < 0.4 poor, 0.4–0.6 moderate, 0.6–0.8 substantial, > 0.8 near-perfect.\n",
    ]

    # The interpretation that matters, stated per outcome rather than spun.
    L.append("## Reading this\n")
    if i_kappa >= 0.6:
        L.append(f"- Intent kappa of **{i_kappa:.2f}** means the intent "
                 f"definitions transfer: an independent reader applying them "
                 f"lands in the same place most of the time. That is evidence "
                 f"the taxonomy is teachable — which is the thing the 20-item "
                 f"pilot found it was *not*, before the definitions were "
                 f"rewritten.")
    elif i_kappa >= 0.4:
        L.append(f"- Intent kappa of **{i_kappa:.2f}** is only moderate. The "
                 f"definitions are not yet tight enough for two readers to "
                 f"apply them the same way, so some of the agent's measured "
                 f"intent error is definitional rather than a model failure. "
                 f"The confusions below say which boundaries leak.")
    else:
        L.append(f"- Intent kappa of **{i_kappa:.2f}** is poor. An independent "
                 f"reader given the same rules does not reproduce these labels, "
                 f"which puts a ceiling on what any intent number in this "
                 f"report can mean. This is the pilot's finding recurring and "
                 f"it should be treated as a live problem, not a footnote.")
    if not np.isnan(d_kappa):
        if d_kappa >= 0.6:
            L.append(f"- Escalation kappa of **{d_kappa:.2f}**: the "
                     f"escalate/auto boundary is the more reproducible of the "
                     f"two judgements, which is consistent with it being driven "
                     f"by explicit policy codes rather than prose definitions.")
        else:
            L.append(f"- Escalation kappa of **{d_kappa:.2f}**: the policy codes "
                     f"do not pin the escalate/auto call down as firmly as their "
                     f"explicitness suggests.")
    if not np.isnan(r_agree) and not np.isnan(d_agree) and r_agree < d_agree - 0.1:
        L.append(f"- The two raters agree on *whether* to escalate "
                 f"({d_agree:.0%}) more often than on *why* ({r_agree:.0%}). "
                 f"Several policy codes are therefore describing overlapping "
                 f"situations — a codebook problem, and a real one, since the "
                 f"report attributes escalations to specific clauses.")

    # Confusion structure: which boundaries actually leak.
    conf = Counter((r["h_intent"], r["a_intent"]) for r in rows
                   if r["h_intent"] != r["a_intent"])
    if conf:
        L.append("\n## Where the two readings diverge\n")
        L.append("| Human said | Annotator said | n |")
        L.append("|---|---|---|")
        for (h, a), c in conf.most_common(10):
            L.append(f"| {h} | {a} | {c} |")

    # Per-slice, because the targeted slice is deliberately the hard one.
    L.append("\n## By slice\n")
    L.append("| Slice | n | Intent agreement |")
    L.append("|---|---|---|")
    for sl in sorted({r["slice"] for r in rows if r["slice"]}):
        g = [r for r in rows if r["slice"] == sl]
        L.append(f"| {sl} | {len(g)} | "
                 f"{np.mean([r['h_intent'] == r['a_intent'] for r in g]):.0%} |")

    # The actual deliverable: a re-review queue.
    dis = [r for r in rows if r["h_intent"] != r["a_intent"]
           or (r["h_decision"] in ("auto", "escalate")
               and r["h_decision"] != r["a_decision"])]
    L.append(f"\n## Re-review queue ({len(dis)} items)\n")
    L.append("These are items where an independent reader of the same rules "
             "chose differently. They are **candidates for human re-review**, "
             "not corrections — the annotator has no authority over the human "
             "label. Re-reviewing them would be a second pass on the hardest "
             "items rather than on a random sample.\n")
    for r in dis:
        L.append(f"- `{r['pair_id']}` [{r['slice']}] {r['customer_text'][:150]}\n"
                 f"    - human:     {r['h_intent']} / {r['h_decision']} / {r['h_reason']}\n"
                 f"    - annotator: {r['a_intent']} / {r['a_decision']} / {r['a_reason']}")

    if globals().get("_UNPARSED"):
        L.append("\n## Unparseable responses\n")
        for u in globals()["_UNPARSED"]:
            L.append(f"- `{u['pair_id']}`: {u['raw'][:200]!r}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="annotate only the first N items (smoke test)")
    args = ap.parse_args()

    path = GOLDEN / "labelled.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found.")
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r.get("intent")]
    if args.limit:
        rows = rows[:args.limit]

    print(f"Annotating {len(rows)} items with {ANNOTATOR_MODEL} "
          f"({len(rows)} calls)")
    out = annotate(rows)
    if not out:
        raise SystemExit("no items annotated")

    PREDS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n")
    md = report(out)
    OUT.write_text(md + "\n")
    print("\n" + md[:2200])
    print(f"\nWrote {OUT} and {PREDS}")


if __name__ == "__main__":
    main()
