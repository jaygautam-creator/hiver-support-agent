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
# Set after scripts/survey_brands.py. See results/brand_survey.md for why.
BRAND = os.getenv("BRAND", "")

# --- Golden set ------------------------------------------------------------
GOLDEN_N = 200          # assignment allows 150-250
DEV_N = 50              # inspectable during development
TEST_N = GOLDEN_N - DEV_N   # opened once, at the end
JUDGE_AGREEMENT_N = 50  # replies scored by hand, blind, before the judge runs
