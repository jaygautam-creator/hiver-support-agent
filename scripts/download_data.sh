#!/usr/bin/env bash
# Fetches the primary dataset: Customer Support on Twitter (Kaggle).
#   thoughtvector/customer-support-on-twitter  (~500MB zip -> twcs/twcs.csv, ~2.8M rows)
#
# Requires Kaggle API credentials, either:
#   ~/.kaggle/access_token  (new-style KGAT_ token; Kaggle -> Settings -> API)
#   ~/.kaggle/kaggle.json   (legacy username/key pair)
#
# Graders do NOT need to run this. data/brand_subsample.parquet is committed.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f ~/.kaggle/access_token ]; then
  chmod 600 ~/.kaggle/access_token
elif [ -f ~/.kaggle/kaggle.json ]; then
  chmod 600 ~/.kaggle/kaggle.json
else
  echo "ERROR: no Kaggle credentials found."
  echo "Get a token from https://www.kaggle.com/settings -> API -> Create New Token"
  echo "then save it to ~/.kaggle/access_token"
  exit 1
fi

echo "Downloading (~500MB, a few minutes)..."
kaggle datasets download -d thoughtvector/customer-support-on-twitter -p data/raw --unzip

echo "Done. Files in data/raw:"
ls -lh data/raw
