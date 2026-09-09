"""
Step 0: pick the brand with data, not vibes.

Streams the 2.8M-row raw CSV in chunks (keeps memory flat) and reports, per brand:
  - inbound volume            -> is there enough to retrieve over?
  - reply rate                -> does the brand actually answer? (needed for "how it
                                historically resolved" grounding)
  - median customer msg len   -> substantive issues vs one-liners
  - % threads with >=2 brand turns -> real resolution dialogue vs deflection to DM

Output: results/brand_survey.md  (an artifact for the decision log)
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/twcs/twcs.csv")
if not RAW.exists():
    alt = Path("data/raw/twcs.csv")
    RAW = alt if alt.exists() else RAW
OUT = Path("results/brand_survey.md")
CHUNK = 250_000

def main():
    if not RAW.exists():
        sys.exit(f"Raw data not found at {RAW}. Run scripts/download_data.sh first.")

    inbound_to = Counter()      # brand -> customer msgs directed at it
    outbound_by = Counter()     # brand -> msgs the brand sent
    msg_len = defaultdict(list)
    rows = 0

    cols = ["tweet_id", "author_id", "inbound", "text", "in_response_to_tweet_id"]
    for chunk in pd.read_csv(RAW, usecols=cols, chunksize=CHUNK, dtype=str):
        rows += len(chunk)
        chunk["inbound"] = chunk["inbound"].astype(str).str.lower().eq("true")

        # Brand handles are non-numeric author_ids; customers are numeric ids.
        brands = chunk[~chunk["inbound"]]
        outbound_by.update(brands["author_id"].value_counts().to_dict())

        # A customer tweet naming @Brand is inbound volume for that brand.
        cust = chunk[chunk["inbound"]].copy()
        mentions = cust["text"].fillna("").str.extract(r"^@(\w+)", expand=False)
        vc = mentions.value_counts()
        inbound_to.update(vc.to_dict())
        for b, grp in cust.assign(_b=mentions).dropna(subset=["_b"]).groupby("_b"):
            msg_len[b].extend(grp["text"].str.len().tolist()[:2000])

        print(f"  scanned {rows:,} rows", end="\r", flush=True)

    print(f"\nScanned {rows:,} rows total.")

    recs = []
    for brand, n_in in inbound_to.most_common(40):
        n_out = outbound_by.get(brand, 0)
        lens = msg_len.get(brand, [])
        recs.append({
            "brand": brand,
            "inbound_msgs": n_in,
            "brand_replies": n_out,
            "reply_ratio": round(n_out / n_in, 2) if n_in else 0.0,
            "median_len": int(pd.Series(lens).median()) if lens else 0,
        })

    df = pd.DataFrame(recs).sort_values("inbound_msgs", ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "# Brand survey\n\n"
        f"Scanned {rows:,} raw rows.\n\n"
        "Selection criteria: enough inbound volume to retrieve over, a reply_ratio\n"
        "near or above 1.0 (the brand actually answers rather than deflecting), and\n"
        "median message length long enough to carry a real issue.\n\n"
        + df.head(25).to_markdown(index=False) + "\n"
    )
    print(df.head(25).to_string(index=False))
    print(f"\nWrote {OUT}")

if __name__ == "__main__":
    main()
