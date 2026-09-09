"""
Phase 2: derive the intent taxonomy FROM THE DATA.

The assignment asks for intents "that you define from the data", so this is the
evidence trail for that claim rather than a taxonomy that appears from nowhere.

Method: TF-IDF over conversation openers -> KMeans -> for each cluster print the
most distinctive terms and a random sample of real messages. I then read the
output and write the taxonomy by hand; clustering is a reading aid, not the
answer. Clusters are not intents -- they are dominated by surface vocabulary
(device names, iOS versions) that cuts across intents.

Output: results/taxonomy_derivation.md
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import SEED, SUBSAMPLE

OUT = Path("results/taxonomy_derivation.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=14)
    ap.add_argument("--n", type=int, default=4000, help="openers to cluster")
    ap.add_argument("--samples", type=int, default=8)
    args = ap.parse_args()

    df = pd.read_parquet(SUBSAMPLE)
    df = df[df["is_opener"]].sample(args.n, random_state=SEED).reset_index(drop=True)

    vec = TfidfVectorizer(
        max_features=5000, ngram_range=(1, 2), min_df=5, max_df=0.4,
        stop_words="english", sublinear_tf=True,
    )
    X = vec.fit_transform(df["customer_text"])
    km = KMeans(n_clusters=args.k, random_state=SEED, n_init=10).fit(X)
    df["cluster"] = km.labels_

    terms = vec.get_feature_names_out()
    lines = [
        "# Intent taxonomy derivation",
        "",
        f"TF-IDF (1-2 grams) over {args.n:,} randomly sampled conversation openers, "
        f"KMeans k={args.k}, seed={SEED}.",
        "",
        "Clusters are a **reading aid**, not the taxonomy. They group by surface "
        "vocabulary (device names, iOS versions) which cuts across real intents. "
        "The taxonomy in `src/taxonomy.py` was written by hand after reading this "
        "output, and deliberately does not have k classes.",
        "",
    ]

    for c in range(args.k):
        centroid = km.cluster_centers_[c]
        top = [terms[i] for i in centroid.argsort()[::-1][:10]]
        sub = df[df["cluster"] == c]
        lines += [
            f"## Cluster {c}  ({len(sub)} msgs, {100*len(sub)/len(df):.1f}%)",
            "",
            f"**Top terms:** {', '.join(top)}",
            "",
        ]
        for t in sub["customer_text"].sample(
            min(args.samples, len(sub)), random_state=SEED
        ):
            lines.append(f"- {t[:220]}")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT}  ({args.k} clusters over {args.n:,} messages)")


if __name__ == "__main__":
    main()
