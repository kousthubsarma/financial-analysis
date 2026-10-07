# S&P 500 Risk Analysis

A Streamlit app that scores S&P 500 companies across seven risk dimensions using
public data from SEC EDGAR filings, Yahoo Finance market data, and ISS governance signals.

Higher score = higher risk, ranked relative to peers.

## Risk dimensions

| Dimension | Example attributes | Source |
|---|---|---|
| **Financial** | margins, ROA/ROE, growth, Altman Z-score | SEC XBRL + Yahoo |
| **Liquidity** | current/quick/cash ratios, free cash flow margin | SEC XBRL |
| **Debt / Leverage** | debt-to-equity, net-debt/EBITDA, interest coverage | SEC XBRL + Yahoo |
| **Market** | beta, annualized volatility, max drawdown, short interest | Yahoo price history |
| **Governance** | ISS audit/board/comp/shareholder-rights scores, insider trading | Yahoo |
| **Innovation** | R&D intensity, R&D growth, capex intensity | SEC XBRL |
| **Risk Language** | YoY change in 10-K Item 1A risk factors, uncertainty/litigation density | SEC filing text |

Each metric is normalized to a 0–100 relative percentile, averaged per dimension,
then combined into a weighted **composite risk score** (weights adjustable live in the app).

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Build the dataset

```bash
# first 100 companies (default)
.venv/bin/python build_dataset.py

# full index
SP500_LIMIT=503 .venv/bin/python build_dataset.py
```

API responses and filings are cached under `data/raw/` (git-ignored), so re-runs
only fetch what's new. The scored dataset is written to `data/processed/`.

> Set a descriptive `SEC_USER_AGENT` env var with contact info per
> [SEC fair-access rules](https://www.sec.gov/os/accessing-edgar-data).

## Run the app

```bash
.venv/bin/streamlit run app.py
```

Then open http://localhost:8501.

## Project layout

```
app.py                  Streamlit UI
build_dataset.py        end-to-end dataset builder
pipeline/
  universe.py           S&P 500 constituent list
  collect_yahoo.py      market / valuation / governance / insider data
  collect_sec_fundamentals.py   XBRL fundamentals
  collect_sec_risk_text.py      10-K Item 1A risk-language analysis
  features.py           derived ratios and scores
  scoring.py            dimension normalization + composite
  ui.py                 theme, CSS, chart template, components
  sec_client.py         rate-limited, cached SEC EDGAR client
```

## Data sources

- [SEC EDGAR](https://www.sec.gov/edgar) — XBRL company facts and 10-K filings
- [Yahoo Finance](https://finance.yahoo.com/) via `yfinance`
- [Wikipedia](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) — index constituents

## Notes

Some fields are structurally sparse (e.g. R&D is not reported by banks, REITs, or
utilities). Scoring handles missing metrics by averaging whatever is available per
dimension. The risk-language analysis uses a lightweight dictionary/Jaccard approach,
not heavy NLP.

This project is for research and educational purposes and is not investment advice.
