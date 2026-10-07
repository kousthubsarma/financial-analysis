"""Shared configuration and paths."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"          # cached API responses / filings (safe to delete; rebuilt on demand)
PROCESSED = DATA / "processed"
for p in (RAW, PROCESSED):
    p.mkdir(parents=True, exist_ok=True)

# SEC requires a descriptive User-Agent with contact info:
# https://www.sec.gov/os/accessing-edgar-data
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "SP500RiskResearch research-contact@example.com")
SEC_MAX_RPS = 8  # SEC fair-access limit is 10 req/s

WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# How many companies to process. Start at 100; raise to 503 to cover the full index.
LIMIT = int(os.environ.get("SP500_LIMIT", "100"))
