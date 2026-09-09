"""
Turns the raw 2.8M-row Twitter support dump into one brand's conversation
pairs, and writes data/brand_subsample.parquet.

Raw schema (twcs.csv):
    tweet_id, author_id, inbound, created_at, text,
    response_tweet_id, in_response_to_tweet_id

The unit of work is a (customer message -> brand's first reply) pair, because
that is exactly what the agent has to produce: given an incoming message, a
reply. Later brand turns are kept as thread context but are not targets.

Cleaning is deliberately conservative -- see CLEANING_RULES. Every rule here is
a decision-log entry, because aggressive normalisation is the easiest way to
accidentally delete the signal you are trying to measure.
"""
import argparse
import html
import re
from pathlib import Path

import pandas as pd

from src.config import RAW_CSV, SUBSAMPLE, SEED

CHUNK = 250_000

# Order matters: mentions are stripped before URLs so a trailing handle in a
# URL-only tweet does not survive.
URL_RE = re.compile(r"https?://\S+|www\.\S+")
LEADING_MENTIONS_RE = re.compile(r"^(?:@\w+\s+)+")
MENTION_RE = re.compile(r"@\w+")
WS_RE = re.compile(r"\s+")

CLEANING_RULES = """
1. HTML-unescape (&amp; -> &). The dump is double-escaped in places.
2. Strip LEADING @Brand mentions. They are addressing metadata, not content --
   leaving them in lets a classifier cheat on the brand handle.
3. Replace remaining inline @handles with @user. Some carry meaning
   ("cc @support") but the specific handle never does, and keeping real
   usernames is a privacy problem in a repo.
4. Replace URLs with <url>. Link targets are dead and their tokens are noise;
   the FACT that a link was sent is signal, so a placeholder is kept.
5. Collapse whitespace, strip.
6. Drop messages under 15 characters after cleaning -- these are almost all
   "thanks", "ok", "?" and carry no classifiable intent.
7. NOT removed: emoji, casing, punctuation, misspellings, ALL-CAPS. Those carry
   the frustration signal the escalation decision depends on.
"""


def clean(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = html.unescape(text)
    t = LEADING_MENTIONS_RE.sub("", t)
    t = URL_RE.sub("<url>", t)
    t = MENTION_RE.sub("@user", t)
    return WS_RE.sub(" ", t).strip()


def load_brand(brand: str, raw: Path = RAW_CSV) -> pd.DataFrame:
    """Stream the raw CSV and keep only rows touching `brand`.

    Two passes over a chunked read: the first collects the brand's own tweets
    and the ids they reply to; the second pulls those parent customer tweets.
    Chunked so peak memory stays flat regardless of raw file size.
    """
    if not raw.exists():
        raise FileNotFoundError(f"{raw} missing -- run scripts/download_data.sh")

    cols = ["tweet_id", "author_id", "inbound", "created_at", "text",
            "response_tweet_id", "in_response_to_tweet_id"]

    brand_tweets = []
    wanted_parents: set[str] = set()

    for chunk in pd.read_csv(raw, usecols=cols, chunksize=CHUNK, dtype=str):
        b = chunk[chunk["author_id"] == brand]
        if len(b):
            brand_tweets.append(b)
            wanted_parents.update(b["in_response_to_tweet_id"].dropna().tolist())

    if not brand_tweets:
        raise ValueError(f"No tweets found for author_id={brand!r}")
    brand_df = pd.concat(brand_tweets, ignore_index=True)

    parents = []
    for chunk in pd.read_csv(raw, usecols=cols, chunksize=CHUNK, dtype=str):
        p = chunk[chunk["tweet_id"].isin(wanted_parents)]
        if len(p):
            parents.append(p)
    parent_df = pd.concat(parents, ignore_index=True) if parents else pd.DataFrame(columns=cols)

    return brand_df, parent_df


def build_pairs(brand_df: pd.DataFrame, parent_df: pd.DataFrame, brand: str) -> pd.DataFrame:
    """Join each brand reply to the customer message it answers.

    Keeps the FIRST brand reply per customer message only. Later turns in the
    same thread are the brand reacting to its own conversation, not to an
    incoming message, so they are not valid targets for a first-response agent.
    """
    parents = parent_df[parent_df["inbound"].astype(str).str.lower() == "true"]

    merged = brand_df.merge(
        parents[["tweet_id", "author_id", "created_at", "text", "in_response_to_tweet_id"]],
        left_on="in_response_to_tweet_id",
        right_on="tweet_id",
        suffixes=("_reply", "_cust"),
    )

    merged = merged.sort_values("created_at_reply").drop_duplicates(
        subset=["tweet_id_cust"], keep="first"
    )

    out = pd.DataFrame({
        "pair_id": merged["tweet_id_cust"].astype(str) + "_" + merged["tweet_id_reply"].astype(str),
        "customer_id": merged["author_id_cust"],
        "customer_text_raw": merged["text_cust"],
        "customer_text": merged["text_cust"].map(clean),
        "brand_reply_raw": merged["text_reply"],
        "brand_reply": merged["text_reply"].map(clean),
        "customer_created_at": merged["created_at_cust"],
        "reply_created_at": merged["created_at_reply"],
        # True when the customer message opens the conversation. A mid-thread
        # message is often an answer to the brand's own clarifying question
        # ("iOS 11.1"), which cannot be classified standalone -- so this is a
        # stratification variable, not cosmetic metadata.
        "is_opener": merged["in_response_to_tweet_id_cust"].isna(),
        "brand": brand,
    })

    before = len(out)
    out = out[(out["customer_text"].str.len() >= 15) & (out["brand_reply"].str.len() >= 15)]
    out = out.drop_duplicates(subset=["customer_text"])
    print(f"  dropped {before - len(out):,} short/duplicate pairs -> {len(out):,} kept")

    return out.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="author_id of the brand, e.g. AppleSupport")
    ap.add_argument("--out", default=str(SUBSAMPLE))
    args = ap.parse_args()

    print(f"Scanning raw data for {args.brand} ...")
    brand_df, parent_df = load_brand(args.brand)
    print(f"  {len(brand_df):,} brand tweets, {len(parent_df):,} parent tweets")

    pairs = build_pairs(brand_df, parent_df, args.brand)
    pairs = pairs.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(args.out, index=False)
    print(f"Wrote {len(pairs):,} pairs -> {args.out}")
    print("\nCleaning rules applied:" + CLEANING_RULES)


if __name__ == "__main__":
    main()
