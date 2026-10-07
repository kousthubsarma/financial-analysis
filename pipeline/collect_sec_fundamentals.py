"""Pull structured fundamentals from SEC EDGAR XBRL company facts.

We extract the most recent reported value plus a prior-year value (for growth)
for a curated set of US-GAAP concepts spanning the risk dimensions.
"""
import pandas as pd

from . import sec_client
from .config import PROCESSED

# concept -> list of candidate us-gaap tags (first available wins)
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "op_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_liabilities": ["Liabilities"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "inventory": ["InventoryNet"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "short_term_debt": ["LongTermDebtCurrent", "DebtCurrent"],
    "stockholders_equity": ["StockholdersEquity"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "ebit": ["OperatingIncomeLoss"],
    "working_capital_proxy": ["AssetsCurrent"],
}

# flow concepts need annual (FY) duration data; stock concepts are point-in-time
FLOW = {"revenue", "net_income", "operating_income", "gross_profit", "rd_expense",
        "interest_expense", "capex", "op_cash_flow", "ebit"}


def _latest_two(facts: dict, tags: list, want_flow: bool):
    """Return (latest_val, prior_val, latest_end) for the best matching tag."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        if tag not in gaap:
            continue
        units = gaap[tag].get("units", {})
        series = units.get("USD") or (next(iter(units.values())) if units else None)
        if not series:
            continue
        if want_flow:
            # annual figures: ~360-370 day duration
            pts = [p for p in series if p.get("start") and p.get("end")
                   and 350 <= (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days <= 380]
        else:
            pts = [p for p in series if p.get("end") and not p.get("start")]
            if not pts:
                pts = [p for p in series if p.get("end")]
        if not pts:
            continue
        pts = sorted(pts, key=lambda p: p["end"])
        latest = pts[-1]
        end = pd.Timestamp(latest["end"])
        prior = None
        for p in reversed(pts[:-1]):
            if (end - pd.Timestamp(p["end"])).days >= 300:
                prior = p
                break
        return latest["val"], (prior["val"] if prior else None), latest["end"]
    return None, None, None


def collect_sec_fundamentals(universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(universe)
    for i, r in universe.reset_index(drop=True).iterrows():
        cik = int(r["cik"])
        print(f"  [sec-fund {i + 1}/{n}] {r['ticker']} (CIK {cik})", flush=True)
        rec = {"ticker": r["ticker"]}
        facts = sec_client.company_facts(cik)
        if not facts:
            rec["_sec_error"] = "no company facts"
            rows.append(rec)
            continue
        for concept, tags in CONCEPTS.items():
            val, prior, end = _latest_two(facts, tags, concept in FLOW)
            rec[concept] = val
            rec[f"{concept}_prior"] = prior
            if concept == "revenue":
                rec["fundamentals_asof"] = end
        # fallback: total liabilities = total assets - stockholders' equity
        if rec.get("total_liabilities") is None and rec.get("total_assets") is not None and rec.get("stockholders_equity") is not None:
            rec["total_liabilities"] = rec["total_assets"] - rec["stockholders_equity"]
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "sec_fundamentals.parquet")
    return df
