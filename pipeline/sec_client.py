"""Rate-limited, disk-cached client for SEC EDGAR."""
import hashlib
import json
import threading
import time
from pathlib import Path

import requests

from .config import RAW, SEC_MAX_RPS, SEC_USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"})
_lock = threading.Lock()
_last_call = [0.0]


def _throttle():
    with _lock:
        wait = (1.0 / SEC_MAX_RPS) - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()


def _cache_path(url: str, suffix: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()[:20]
    d = RAW / "sec"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}{suffix}"


def get(url: str, as_json: bool = False, max_age_days: float = 7, retries: int = 4):
    """GET with caching. Returns parsed JSON, text, or None on 404."""
    cp = _cache_path(url, ".json" if as_json else ".txt")
    if cp.exists() and (time.time() - cp.stat().st_mtime) < max_age_days * 86400:
        raw = cp.read_text(encoding="utf-8", errors="ignore")
        return json.loads(raw) if as_json else raw

    for attempt in range(retries):
        _throttle()
        try:
            r = _session.get(url, timeout=60)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 404:
            return None
        if r.status_code in (429, 503):
            time.sleep(2 ** (attempt + 1))
            continue
        r.raise_for_status()
        cp.write_text(r.text, encoding="utf-8")
        return r.json() if as_json else r.text
    return None


def company_facts(cik: int):
    return get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", as_json=True)


def submissions(cik: int):
    return get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True, max_age_days=1)


def filing_document(cik: int, accession: str, primary_doc: str):
    acc = accession.replace("-", "")
    # Filed documents never change, so cache indefinitely.
    return get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{primary_doc}", max_age_days=3650)
