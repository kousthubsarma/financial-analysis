"""Collect market, valuation, governance and insider data from Yahoo Finance."""
import time

import numpy as np
import pandas as pd
import yfinance as yf

from .config import PROCESSED

# info-dict fields we keep (grouped by risk dimension for clarity)
INFO_FIELDS = [
    # identity / scale
    "longName", "sector", "industry", "fullTimeEmployees", "country", "marketCap",
    "enterpriseValue", "sharesOutstanding", "floatShares",
    # valuation
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "enterpriseToEbitda", "enterpriseToRevenue", "pegRatio",
    # profitability
    "profitMargins", "grossMargins", "operatingMargins", "ebitdaMargins",
    "returnOnAssets", "returnOnEquity",
    # growth
    "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
    # liquidity / leverage
    "currentRatio", "quickRatio", "debtToEquity", "totalCash", "totalDebt",
    "operatingCashflow", "freeCashflow", "ebitda", "totalRevenue",
    # market risk
    "beta", "fiftyTwoWeekChangePercent", "SandP52WeekChange",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currentPrice",
    # dividends
    "dividendYield", "payoutRatio",
    # short interest
    "shortPercentOfFloat", "shortRatio", "sharesPercentSharesOut",
    # ownership
    "heldPercentInsiders", "heldPercentInstitutions",
    # ISS governance risk scores (1=low risk .. 10=high risk)
    "auditRisk", "boardRisk", "compensationRisk", "shareHolderRightsRisk", "overallRisk",
    # analyst
    "numberOfAnalystOpinions", "recommendationMean", "targetMeanPrice",
]


def _price_risk(tkr: yf.Ticker) -> dict:
    """Annualized volatility and max drawdown from ~1y daily closes."""
    try:
        hist = tkr.history(period="1y", auto_adjust=True)
    except Exception:
        return {}
    if hist.empty or len(hist) < 30:
        return {}
    close = hist["Close"].dropna()
    rets = close.pct_change().dropna()
    vol = float(rets.std() * np.sqrt(252)) if len(rets) else np.nan
    roll_max = close.cummax()
    max_dd = float(((close - roll_max) / roll_max).min())
    pos_52w = float((close.iloc[-1] - close.min()) / (close.max() - close.min())) if close.max() > close.min() else np.nan
    return {"annualized_volatility": vol, "max_drawdown_1y": max_dd, "price_pos_52w": pos_52w}


def _insider(tkr: yf.Ticker) -> dict:
    try:
        ip = tkr.insider_purchases
    except Exception:
        return {}
    if ip is None or ip.empty:
        return {}
    try:
        row = ip.set_index(ip.columns[0]).iloc[:, 0]
        net = row.get("% Net Shares Purchased (Sold)")
        return {"insider_net_buy_pct_6m": float(net) if pd.notna(net) else np.nan}
    except Exception:
        return {}


def collect_yahoo(universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(universe)
    for i, r in universe.reset_index(drop=True).iterrows():
        yf_sym = r["yf_ticker"]
        print(f"  [yahoo {i + 1}/{n}] {yf_sym}", flush=True)
        rec = {"ticker": r["ticker"]}
        try:
            tkr = yf.Ticker(yf_sym)
            info = tkr.info or {}
            for f in INFO_FIELDS:
                rec[f] = info.get(f)
            rec.update(_price_risk(tkr))
            rec.update(_insider(tkr))
        except Exception as e:
            rec["_yahoo_error"] = str(e)[:200]
        rows.append(rec)
        time.sleep(0.3)  # be polite to Yahoo
    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "yahoo.parquet")
    return df
