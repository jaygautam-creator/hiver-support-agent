"""
Brand selection, step 2.

Volume is not the criterion -- resolvability is. The agent has to draft replies
"grounded in how the brand historically resolved similar issues", which is
impossible if the brand's historical replies are all "please DM us".

For each candidate brand this measures, over its FIRST replies to customers:
  deflection_rate  -- reply just moves the conversation to DM/private channel
  substantive_rate -- reply contains an actual instruction, answer, or apology+info
  self_serve_rate  -- reply points at a help URL (a weaker but real resolution)

Output: results/brand_deflection.md
"""
import re
import sys
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/twcs/twcs.csv")
OUT = Path("results/brand_deflection.md")
CHUNK = 300_000

CANDIDATES = ["AmazonHelp", "AppleSupport", "Uber_Support", "AmericanAir",
              "Delta", "SpotifyCares", "British_Airways", "XboxSupport",
              "Tesco", "TMobileHelp", "SouthwestAir", "hulu_support"]

DEFLECT = re.compile(
    r"\b(dm|d\.m\.|direct message|private message|pm us|send us a (dm|message|private)"
    r"|click the link|follow and dm|shoot us a dm|via dm|in a dm)\b", re.I)
URL = re.compile(r"https?://\S+")
# Rough proxy for a reply that actually tells the customer to DO something.
INSTRUCT = re.compile(
    r"\b(try|tap|go to|open|settings|restart|reset|update|check|select|toggle|"
    r"sign out|log out|uninstall|reinstall|hold|press|swipe|enable|disable)\b", re.I)


def main():
    if not RAW.exists():
        sys.exit(f"{RAW} not found")

    cand = set(CANDIDATES)
    replies = {b: [] for b in CANDIDATES}
    cols = ["author_id", "inbound", "text", "in_response_to_tweet_id"]

    n = 0
    for chunk in pd.read_csv(RAW, usecols=cols, chunksize=CHUNK, dtype=str):
        n += len(chunk)
        b = chunk[chunk["author_id"].isin(cand) & chunk["in_response_to_tweet_id"].notna()]
        for brand, grp in b.groupby("author_id"):
            replies[brand].extend(grp["text"].dropna().tolist())
        print(f"  scanned {n:,}", end="\r", flush=True)
    print()

    rows = []
    for brand in CANDIDATES:
        texts = pd.Series(replies[brand], dtype=str)
        if texts.empty:
            continue
        defl = texts.str.contains(DEFLECT)
        url = texts.str.contains(URL)
        instr = texts.str.contains(INSTRUCT)
        # "substantive" = gives an instruction and is not purely a DM handoff
        subst = instr & ~defl
        rows.append({
            "brand": brand,
            "n_replies": len(texts),
            "deflection_%": round(100 * defl.mean(), 1),
            "self_serve_url_%": round(100 * url.mean(), 1),
            "substantive_%": round(100 * subst.mean(), 1),
            "median_len": int(texts.str.len().median()),
        })

    df = pd.DataFrame(rows).sort_values("substantive_%", ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "# Brand deflection analysis\n\n"
        "Measured over every brand reply that responds to another tweet.\n\n"
        "- **deflection_%** - reply pushes the customer to DM/private channel\n"
        "- **substantive_%** - reply contains an actionable instruction and is *not* a DM handoff\n"
        "- **self_serve_url_%** - reply links to a help resource\n\n"
        "A brand with a high deflection rate cannot support a grounded-reply agent:\n"
        "there is no historical resolution to ground in, only a handoff.\n\n"
        + df.to_markdown(index=False) + "\n"
    )
    print(df.to_string(index=False))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
