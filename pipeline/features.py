"""Derive risk features from the raw collected data."""
import numpy as np
import pandas as pd


def _safe_div(a, b):
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    return a / b.replace(0, np.nan)


def build_features(universe, yahoo, sec_fund, sec_risk) -> pd.DataFrame:
    df = universe.merge(yahoo, on="ticker", how="left")
    df = df.merge(sec_fund, on="ticker", how="left")
    df = df.merge(sec_risk, on="ticker", how="left")

    # marketCap fallback when Yahoo omits it
    mc = pd.to_numeric(df["marketCap"], errors="coerce")
    fallback = pd.to_numeric(df.get("sharesOutstanding"), errors="coerce") * pd.to_numeric(df.get("currentPrice"), errors="coerce")
    df["marketCap"] = mc.fillna(fallback)

    # --- fundamentals-derived ratios ---
    df["current_ratio_sec"] = _safe_div(df["current_assets"], df["current_liabilities"])
    df["working_capital"] = pd.to_numeric(df["current_assets"], errors="coerce") - pd.to_numeric(df["current_liabilities"], errors="coerce")
    df["quick_ratio_sec"] = _safe_div(
        pd.to_numeric(df["current_assets"], errors="coerce") - pd.to_numeric(df["inventory"], errors="coerce"),
        df["current_liabilities"],
    )
    df["cash_ratio"] = _safe_div(df["cash"], df["current_liabilities"])

    total_debt = pd.to_numeric(df["long_term_debt"], errors="coerce").fillna(0) + pd.to_numeric(df["short_term_debt"], errors="coerce").fillna(0)
    df["total_debt_sec"] = total_debt
    df["debt_to_equity_sec"] = _safe_div(total_debt, df["stockholders_equity"])
    df["debt_to_assets"] = _safe_div(total_debt, df["total_assets"])
    df["net_debt_to_ebitda"] = _safe_div(total_debt - pd.to_numeric(df["cash"], errors="coerce").fillna(0), df["ebitda"])
    df["interest_coverage"] = _safe_div(df["operating_income"], df["interest_expense"].abs())

    # profitability / efficiency
    df["net_margin_sec"] = _safe_div(df["net_income"], df["revenue"])
    df["operating_margin_sec"] = _safe_div(df["operating_income"], df["revenue"])
    df["roa_sec"] = _safe_div(df["net_income"], df["total_assets"])
    df["fcf"] = pd.to_numeric(df["op_cash_flow"], errors="coerce") - pd.to_numeric(df["capex"], errors="coerce").abs()
    df["fcf_margin"] = _safe_div(df["fcf"], df["revenue"])

    # growth (YoY from SEC)
    df["revenue_growth_sec"] = _safe_div(pd.to_numeric(df["revenue"], errors="coerce") - pd.to_numeric(df["revenue_prior"], errors="coerce"), df["revenue_prior"])
    df["net_income_growth_sec"] = _safe_div(pd.to_numeric(df["net_income"], errors="coerce") - pd.to_numeric(df["net_income_prior"], errors="coerce"), df["net_income_prior"].abs())

    # innovation
    df["rd_intensity"] = _safe_div(df["rd_expense"], df["revenue"])
    df["rd_growth"] = _safe_div(pd.to_numeric(df["rd_expense"], errors="coerce") - pd.to_numeric(df["rd_expense_prior"], errors="coerce"), df["rd_expense_prior"])
    df["capex_intensity"] = _safe_div(pd.to_numeric(df["capex"], errors="coerce").abs(), df["revenue"])

    # Altman Z-score (manufacturing form; proxy using available fields)
    ta = pd.to_numeric(df["total_assets"], errors="coerce")
    df["altman_z"] = (
        1.2 * _safe_div(df["working_capital"], ta)
        + 1.4 * _safe_div(df["retained_earnings"], ta)
        + 3.3 * _safe_div(df["ebit"], ta)
        + 0.6 * _safe_div(df["marketCap"], df["total_liabilities"])
        + 1.0 * _safe_div(df["revenue"], ta)
    )

    return df
