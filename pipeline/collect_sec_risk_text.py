"""Analyze risk-factor language and its year-over-year change in 10-K filings.

Lightweight approach (no heavy NLP deps): extract Item 1A "Risk Factors",
measure length, uncertainty/litigation term density, and the change versus the
prior year's 10-K (word-set Jaccard distance + length delta).
"""
import re
import warnings

import pandas as pd
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from . import sec_client
from .config import PROCESSED

# dictionaries for risk-tone counting
UNCERTAINTY_TERMS = [
    "may", "could", "might", "uncertain", "uncertainty", "risk", "risks", "adverse",
    "adversely", "volatile", "volatility", "fluctuate", "unpredictable", "contingent",
    "potential", "exposure", "unfavorable", "disruption", "decline",
]
LITIGATION_TERMS = ["litigation", "lawsuit", "regulatory", "investigation", "penalty",
                    "liability", "compliance", "sanction", "antitrust", "subpoena"]
MACRO_TERMS = ["inflation", "recession", "interest rate", "tariff", "geopolitical",
               "pandemic", "supply chain", "cyber", "cybersecurity", "artificial intelligence"]

_WORD = re.compile(r"[a-z]+")


def _clean(html_or_text: str) -> str:
    soup = BeautifulSoup(html_or_text, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    text = soup.get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def _extract_item_1a(text: str) -> str:
    """Grab text between 'Item 1A. Risk Factors' and 'Item 1B'/'Item 2'.

    Handles non-breaking spaces and chooses the occurrence that yields the
    largest body (the real section, not the table-of-contents entry).
    """
    norm = text.replace("\xa0", " ")
    low = norm.lower()
    starts = [m.start() for m in re.finditer(r"item\s*1a\.?\s*[\-:\.]?\s*risk\s*factors", low)]
    if not starts:
        return ""
    end_re = re.compile(r"item\s*1b\.?|item\s*2\.?\s*propert|item\s*3\.?\s*legal")
    best = ""
    for start in starts:
        m = end_re.search(low, start + 20)
        end = m.start() if m else min(start + 400_000, len(norm))
        chunk = norm[start:end]
        if len(chunk) > len(best):
            best = chunk
    return best


def _count(words: list, terms: list) -> int:
    joined = " ".join(words)
    return sum(joined.count(t) if " " in t else words.count(t) for t in terms)


def _latest_two_10k(cik: int):
    sub = sec_client.submissions(cik)
    if not sub:
        return []
    rec = sub["filings"]["recent"]
    out = []
    for form, acc, doc, date in zip(rec["form"], rec["accessionNumber"],
                                    rec["primaryDocument"], rec["filingDate"]):
        if form == "10-K" and doc:
            out.append((acc, doc, date))
        if len(out) == 2:
            break
    return out


def collect_sec_risk_text(universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(universe)
    for i, r in universe.reset_index(drop=True).iterrows():
        cik = int(r["cik"])
        print(f"  [sec-risk {i + 1}/{n}] {r['ticker']}", flush=True)
        rec = {"ticker": r["ticker"]}
        filings = _latest_two_10k(cik)
        if not filings:
            rec["_risktext_error"] = "no 10-K found"
            rows.append(rec)
            continue

        texts = []
        for acc, doc, date in filings:
            raw = sec_client.filing_document(cik, acc, doc)
            section = _extract_item_1a(_clean(raw)) if raw else ""
            texts.append((section, date))

        cur, cur_date = texts[0]
        words = _WORD.findall(cur.lower())
        wc = len(words)
        rec["risk_filing_date"] = cur_date
        rec["risk_section_words"] = wc
        if wc:
            rec["uncertainty_density"] = _count(words, UNCERTAINTY_TERMS) / wc * 1000
            rec["litigation_density"] = _count(words, LITIGATION_TERMS) / wc * 1000
            rec["macro_density"] = _count(words, MACRO_TERMS) / wc * 1000

        if len(texts) == 2 and texts[1][0]:
            prev_words = set(_WORD.findall(texts[1][0].lower()))
            cur_set = set(words)
            if cur_set or prev_words:
                inter = len(cur_set & prev_words)
                union = len(cur_set | prev_words)
                rec["risk_text_change"] = 1 - inter / union if union else 0.0  # Jaccard distance
            prev_wc = len(_WORD.findall(texts[1][0].lower()))
            rec["risk_length_change_pct"] = (wc - prev_wc) / prev_wc * 100 if prev_wc else None
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "sec_risk_text.parquet")
    return df
