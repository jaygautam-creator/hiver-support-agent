"""
Phase 3a: draw the golden-set sample. Labelling happens afterwards, by hand.

Two-slice design, because a single sampling scheme cannot serve both purposes:

  NATURAL  (n=100) -- uniform random over conversation openers. Preserves true
      class prevalence, so any metric computed on it estimates live performance.
      On its own it is useless for rare classes: `account_access` would get ~3
      examples and its F1 would be noise.

  TARGETED (n=100) -- keyword-seeded oversampling of classes the natural slice
      starves, plus deliberately hard regions (non-English, very short, heavy
      profanity). Gives every class enough support to have a readable F1.

Metrics are reported on BOTH slices and never pooled into one headline without
saying which. The enriched number is the diagnostic; the natural number is the
deployment estimate. Pooling them silently is the single easiest way to publish
a misleading headline, which is exactly what the report has to address.

Known bias, stated up front: keyword-seeded strata over-select messages that
literally contain those keywords, so the targeted slice makes those classes look
easier to spot than they are in the wild. This is why the natural slice exists.
"""
import json
from pathlib import Path

import pandas as pd

from src.config import GOLDEN, SEED, SUBSAMPLE

OUT = GOLDEN / "to_label.jsonl"
N_NATURAL = 100
N_TARGETED = 100

# Seeds are intentionally broad and imperfect -- they only have to surface
# candidates for a human to read, not to be a classifier.
SEEDS: dict[str, str] = {
    "account_access": r"apple id|icloud|password|hacked|locked out|two.factor|2fa|sign in|log ?in|account",
    "hardware_or_repair": r"genius bar|apple store|repair|warranty|replace|cracked|screen broke|battery replace|service cent",
    "billing_or_purchase": r"refund|charged|charge|subscription|itunes|app store|receipt|billing|purchase|buy|price",
    "how_to": r"how do i|how to|how can i|where is|is it possible|can i ",
    "hard_nonenglish": r"[àáâãäçèéêëìíîïñòóôõöùúûü]|¿|¡",
    "hard_short": None,      # handled numerically below
    "hard_profanity": r"fuck|shit|wtf|damn|piss|garbage|trash|useless",
}
PER_STRATUM = N_TARGETED // len(SEEDS)


def main() -> None:
    # REFUSE if labels already exist. This script draws a fresh frame from
    # data/brand_subsample.parquet; if that parquet has changed at all since the
    # frame was first drawn, the new draw contains different pair_ids and every
    # existing label is orphaned -- silently, because the labels file is never
    # touched. That is a whole-golden-set loss with no error message, so it is
    # a hard stop rather than a comment.
    labelled = GOLDEN / "labelled.jsonl"
    if labelled.exists() and labelled.read_text().strip():
        n = len([l for l in labelled.read_text().splitlines() if l.strip()])
        raise SystemExit(
            f"REFUSING: {labelled} already holds {n} labels drawn against the "
            f"current frame in {OUT.name}.\n"
            f"Re-drawing would orphan every one of them. If you really mean to "
            f"start the golden set over, move both files aside first."
        )

    df = pd.read_parquet(SUBSAMPLE)
    df = df[df["is_opener"]].reset_index(drop=True)
    print(f"frame: {len(df):,} conversation openers")

    natural = df.sample(N_NATURAL, random_state=SEED).copy()
    natural["slice"] = "natural"
    natural["stratum"] = "random"
    taken = set(natural["pair_id"])

    picked = [natural]
    for name, pattern in SEEDS.items():
        pool = df[~df["pair_id"].isin(taken)]
        if name == "hard_short":
            cand = pool[pool["customer_text"].str.len().between(15, 45)]
        else:
            cand = pool[pool["customer_text"].str.contains(pattern, case=False, regex=True)]
        n = min(PER_STRATUM, len(cand))
        s = cand.sample(n, random_state=SEED).copy()
        s["slice"] = "targeted"
        s["stratum"] = name
        taken.update(s["pair_id"])
        picked.append(s)
        print(f"  {name:<20} pool={len(cand):>6,}  drew {n}")

    g = pd.concat(picked, ignore_index=True)

    # Shuffle so the labeller never sees stratum order -- labelling ten
    # `account_access` candidates in a row primes you to see the eleventh as one.
    g = g.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    # dev/test assigned NOW, before any label exists, so the split cannot be
    # influenced by what turns out to be easy.
    g["split"] = ["dev" if i % 4 == 0 else "test" for i in range(len(g))]

    GOLDEN.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for _, r in g.iterrows():
            f.write(json.dumps({
                "pair_id": r["pair_id"],
                "customer_text": r["customer_text"],
                "brand_reply": r["brand_reply"],       # shown AFTER labelling only
                "slice": r["slice"],
                "stratum": r["stratum"],
                "split": r["split"],
                "intent": None,
                "decision": None,
                "reason": None,
            }, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(g)} unlabelled examples -> {OUT}")
    print(f"  natural {(g['slice']=='natural').sum()} | targeted {(g['slice']=='targeted').sum()}")
    print(f"  dev {(g['split']=='dev').sum()} | test {(g['split']=='test').sum()}")


if __name__ == "__main__":
    main()
