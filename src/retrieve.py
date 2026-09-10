"""
Retrieval over AppleSupport's historical resolutions.

The assignment asks for replies "grounded in how that brand has historically
resolved similar issues", so the drafter is given real past (customer message ->
Apple reply) pairs to work from rather than inventing support advice.

Method: TF-IDF over word 1-2 grams + character 3-5 grams, cosine nearest
neighbours. Deliberately not embeddings:
  * 73k documents through a free-tier embedding API is hours of rate-limited
    calls for a component that is not what the project is testing;
  * char n-grams handle this corpus's misspellings and "ios11"/"iOS 11"
    variation better than word-level alone;
  * it is fully deterministic and I can explain every part of it live, which
    matters more here than a marginal recall gain.
This is a stated tradeoff, not an oversight -- see DECISIONS.md.

LEAKAGE: golden-set pair_ids are removed from the index. Without this, the
drafter retrieves the exact message it is being evaluated on, together with
Apple's actual reply, and every groundedness metric becomes meaningless.
"""
import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from src.config import CACHE, GOLDEN, SUBSAMPLE

# Anchored to the repo root via src.config, not to the caller's cwd. As a
# relative path this silently rebuilt a fresh 232MB index into whatever
# directory the command happened to run from -- minutes of work, no error.
INDEX = CACHE / "retrieval_index.pkl"


@dataclass
class Example:
    customer_text: str
    brand_reply: str
    score: float


class Retriever:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True)
        self.word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.5,
                                    sublinear_tf=True, strip_accents="unicode")
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                    min_df=3, max_df=0.5, sublinear_tf=True)
        texts = self.df["customer_text"].tolist()
        self.M = normalize(hstack([self.word.fit_transform(texts),
                                   self.char.fit_transform(texts)]).tocsr())

    def query(self, text: str, k: int = 5) -> list[Example]:
        q = normalize(hstack([self.word.transform([text]),
                              self.char.transform([text])]).tocsr())
        sims = (self.M @ q.T).toarray().ravel()
        top = np.argpartition(-sims, min(k, len(sims) - 1))[:k]
        top = top[np.argsort(-sims[top])]
        return [
            Example(self.df.at[i, "customer_text"],
                    self.df.at[i, "brand_reply"],
                    float(sims[i]))
            for i in top
        ]


def build(exclude_golden: bool = True) -> Retriever:
    df = pd.read_parquet(SUBSAMPLE)
    df = df[df["is_opener"]]

    if exclude_golden:
        gold_path = GOLDEN / "to_label.jsonl"
        if gold_path.exists():
            ids = {json.loads(l)["pair_id"] for l in gold_path.read_text().splitlines()}
            before = len(df)
            df = df[~df["pair_id"].isin(ids)]
            print(f"  excluded {before - len(df)} golden-set pairs from the index")

    print(f"  indexing {len(df):,} historical pairs ...")
    return Retriever(df)


def load_or_build() -> Retriever:
    """Cache the fitted index to disk.

    Pickles the fitted COMPONENTS, not the Retriever object. Pickling the object
    stores a reference to the class's defining module, which is `__main__` when
    this file is run with `python -m src.retrieve` and `src.retrieve` when it is
    imported -- so an index built one way fails to load the other way.
    Storing plain components sidesteps that entirely.
    """
    if INDEX.exists():
        with INDEX.open("rb") as f:
            state = pickle.load(f)
        r = Retriever.__new__(Retriever)
        r.df, r.word, r.char, r.M = state["df"], state["word"], state["char"], state["M"]
        return r

    r = build()
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with INDEX.open("wb") as f:
        pickle.dump({"df": r.df, "word": r.word, "char": r.char, "M": r.M}, f)
    return r


if __name__ == "__main__":
    r = load_or_build()
    for q in ["my battery drains so fast since the ios 11 update",
              "i cant remember my apple id password and im locked out",
              "how do i turn off autocorrect"]:
        print(f"\nQ: {q}")
        for e in r.query(q, k=3):
            print(f"  [{e.score:.3f}] {e.customer_text[:80]}")
            print(f"          -> {e.brand_reply[:90]}")
