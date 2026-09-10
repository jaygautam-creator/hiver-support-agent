"""Central config. Everything that could drift between runs lives here."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GOLDEN = ROOT / "golden"
RESULTS = ROOT / "results"
CACHE = ROOT / "cache"

RAW_CSV = DATA / "raw" / "twcs" / "twcs.csv"
SUBSAMPLE = DATA / "brand_subsample.parquet"

# --- Reproducibility -------------------------------------------------------
# Every sampling / split / clustering step seeds from this. Changing it changes
# the golden set, so it is frozen for the life of the project.
SEED = 20260909

# --- Models ----------------------------------------------------------------
# Google AI Studio free tier (the assignment permits "any LLM API or open model").
# Agent and judge are deliberately different models: a fast one does the
# high-volume drafting, a stronger one judges. They are still the same family,
# which is a real limitation of the judge -- stated in the report rather than
# hidden. (decision log)
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-3.1-flash-lite")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3.5-flash-lite")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Brand -----------------------------------------------------------------
# Chosen by measurement, not by volume; see results/brand_survey.md.
BRAND = "AppleSupport"

# NOTE: the golden-set sizes that used to live here (GOLDEN_N / DEV_N / TEST_N /
# JUDGE_AGREEMENT_N) were removed. Nothing read them -- the real sizes are set
# in scripts/build_golden_sample.py and golden/judge_subsample.json -- so they
# were four constants that looked authoritative and governed nothing.
