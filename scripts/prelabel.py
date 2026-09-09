"""
Rule-based pre-labeller, used ONLY to seed the human verification pass.

Why rules and not the agent: pre-labelling with the system under evaluation makes
the golden set agree with it by construction, and the resulting accuracy measures
self-consistency rather than correctness. A weak, independent, non-neural
pre-labeller has no such relationship to the agent -- and it is wrong often
enough that a reviewer cannot safely click through it.

It is also NOT the simple baseline (which learns both intent and escalation), so
seeding the golden set with these rules does not inflate that baseline either.

Its accuracy on the 40 blind items is the reference point for measuring how much
the verification pass anchored the reviewer -- see scripts/measure_anchoring.py.
"""
import json
import re

from src.config import GOLDEN, SEED
from src.baselines import PRELABEL_RULES

OUT = GOLDEN / "prelabels.jsonl"
N_BLIND = 40

# Intent rules, applied in order; first match wins. Mirrors the mechanical tests
# R1-R3 in src/taxonomy.py, crudely -- crude is the point.
UPDATE = r"\b(ios ?\d|update|updated|upgrad|11\.\d|10\.\d|high sierra|new software)\b"
INTENT_RULES: list[tuple[str, str]] = [
    ("account_access", r"\b(apple id|icloud|hack|compromis|locked out|password|"
                       r"can'?t (log|sign) ?in|two.factor|2fa|account recovery)\b"),
    ("hardware_or_repair", r"\b(repair|warrant|genius bar|apple store|replace|"
                           r"cracked|broke|broken|charger|cable|screen|battery "
                           r"replace|service cent|physical|damage)\b"),
    ("billing_or_purchase", r"\b(refund|charge|charged|billed|billing|subscription|"
                            r"receipt|purchase|bought|itunes|app store|money|paid|"
                            r"\$\d|£\d)\b"),
    ("how_to", r"\b(how (do|can|to)|where (is|do)|is it possible|can i )\b"),
    ("software_bug", r"\b(bug|glitch|crash|freez|not working|doesn'?t work|broken|"
                     r"won'?t|error|fix)\b"),
    ("feedback_or_complaint", r"\b(worst|garbage|trash|hate|terrible|awful|"
                              r"disappoint|switch|android|shit|fuck)\b"),
]

DECISION_BY_INTENT = {
    "account_access": ("escalate", "E1"),
    "billing_or_purchase": ("escalate", "E2"),
    "hardware_or_repair": ("escalate", "E3"),
    "how_to": ("auto", "A1"),
    "software_bug": ("auto", "A2"),
    "feedback_or_complaint": ("auto", "A4"),
    "other": ("auto", "A4"),
}


# `other` is a real class (non-English, unintelligible), not a fallback bucket.
# An unmatched message is far more likely to be a problem report than genuinely
# unclassifiable, so the default is software_bug -- which also means an unmatched
# item arrives at the reviewer with a plausible guess to correct rather than a
# shrug. Non-Latin / accented text is the actual `other` test.
NON_ENGLISH = re.compile(r"[\u00c0-\u024f\u0370-\u1cff\u3000-\u9fff]|¿|¡")


def predict(text: str) -> tuple[str, str, str]:
    # R1 takes precedence: an update named as trigger beats a generic bug word.
    if re.search(UPDATE, text, re.I) and re.search(
            r"\b(slow|batter|drain|freez|lag|hot|crash|worse|bug|glitch|broke)\b", text, re.I):
        intent = "software_bug"
    elif len(NON_ENGLISH.findall(text)) >= 3:
        intent = "other"
    else:
        intent = "software_bug"          # default guess, not a shrug
        for name, pat in INTENT_RULES:
            if re.search(pat, text, re.I):
                intent = name
                break
    decision, reason = DECISION_BY_INTENT[intent]
    return intent, decision, reason


def main() -> None:
    import random

    items = [json.loads(l) for l in (GOLDEN / "to_label.jsonl").read_text().splitlines()]

    # The blind subset is drawn with the frozen seed, before any pre-label is
    # shown, so which items test anchoring cannot be influenced by their content.
    rng = random.Random(SEED)
    blind = set(rng.sample([i["pair_id"] for i in items], N_BLIND))

    n_esc = 0
    with OUT.open("w") as f:
        for it in items:
            intent, decision, reason = predict(it["customer_text"])
            n_esc += decision == "escalate"
            f.write(json.dumps({
                "pair_id": it["pair_id"],
                "pre_intent": intent,
                "pre_decision": decision,
                "pre_reason": reason,
                "mode": "blind" if it["pair_id"] in blind else "verify",
            }) + "\n")

    print(f"Wrote {OUT}  ({len(items)} pre-labels)")
    print(f"  blind items (no pre-label shown): {N_BLIND}")
    print(f"  verify items:                     {len(items) - N_BLIND}")
    print(f"  pre-labeller escalation rate:     {100*n_esc/len(items):.0f}%")
    from collections import Counter
    c = Counter(predict(i["customer_text"])[0] for i in items)
    print("  pre-label intent spread:", dict(c.most_common()))


if __name__ == "__main__":
    main()
