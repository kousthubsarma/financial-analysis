"""Normalize features into 0-100 risk sub-scores and a weighted composite.

Convention: higher score = higher risk. Scores are relative percentile ranks
within the processed universe. For each metric we set `higher_is_riskier`.
"""
import numpy as np
import pandas as pd

# metric -> higher_is_riskier?  (True: big value = more risk)
DIMENSIONS = {
    "financial": {
        "net_margin_sec": False,
        "operating_margin_sec": False,
        "roa_sec": False,
        "returnOnEquity": False,
        "revenue_growth_sec": False,
        "net_income_growth_sec": False,
        "altman_z": False,
    },
    "liquidity": {
        "current_ratio_sec": False,
        "quick_ratio_sec": False,
        "cash_ratio": False,
        "fcf_margin": False,
    },
    "debt": {
        "debt_to_equity_sec": True,
        "debt_to_assets": True,
        "net_debt_to_ebitda": True,
        "interest_coverage": False,
    },
    "market": {
        "beta": True,
        "annualized_volatility": True,
        "max_drawdown_1y": True,   # more negative = riskier (handled below)
        "shortPercentOfFloat": True,
    },
    "governance": {
        "overallRisk": True,
        "auditRisk": True,
        "boardRisk": True,
        "compensationRisk": True,
        "shareHolderRightsRisk": True,
        "insider_net_buy_pct_6m": False,
    },
    "innovation": {   # low innovation treated as a (strategic) risk
        "rd_intensity": False,
        "rd_growth": False,
        "capex_intensity": False,
    },
    "risk_language": {
        "risk_text_change": True,
        "uncertainty_density": True,
        "litigation_density": True,
        "risk_length_change_pct": True,
    },
}

DEFAULT_WEIGHTS = {
    "financial": 0.22, "liquidity": 0.15, "debt": 0.20, "market": 0.15,
    "governance": 0.12, "innovation": 0.06, "risk_language": 0.10,
}


def _pct_rank_risk(series: pd.Series, higher_is_riskier: bool) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().sum() < 2:
        return pd.Series(np.nan, index=s.index)
    r = s.rank(pct=True)  # 0..1, higher value -> higher rank
    if not higher_is_riskier:
        r = 1 - r
    return r * 100


def score(df: pd.DataFrame, weights: dict | None = None):
    weights = weights or DEFAULT_WEIGHTS
    out = df.copy()
    dim_cols = {}
    for dim, metrics in DIMENSIONS.items():
        parts = []
        for col, hir in metrics.items():
            if col in out.columns:
                sc = _pct_rank_risk(out[col], hir)
                out[f"score__{dim}__{col}"] = sc
                parts.append(sc)
        if parts:
            dim_score = pd.concat(parts, axis=1).mean(axis=1)
            out[f"risk_{dim}"] = dim_score
            dim_cols[dim] = f"risk_{dim}"

    # composite: weighted mean over available dimension scores (renormalize weights)
    w = pd.Series({d: weights.get(d, 0) for d in dim_cols})
    comp = pd.Series(0.0, index=out.index)
    wsum = pd.Series(0.0, index=out.index)
    for dim, col in dim_cols.items():
        valid = out[col].notna()
        comp[valid] += out.loc[valid, col] * w[dim]
        wsum[valid] += w[dim]
    out["risk_composite"] = (comp / wsum.replace(0, np.nan)).round(1)
    rank = out["risk_composite"].rank(ascending=False, method="min")
    out["risk_rank"] = rank.round().astype("Int64")  # nullable int; NaN stays <NA>
    for col in dim_cols.values():
        out[col] = out[col].round(1)
    return out
