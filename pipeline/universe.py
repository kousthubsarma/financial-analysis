"""S&P 500 constituent list (Wikipedia, which tracks S&P index changes)."""
import io

import pandas as pd
import requests

from .config import PROCESSED, WIKI_SP500_URL


def load_universe(refresh: bool = False) -> pd.DataFrame:
    out = PROCESSED / "universe.parquet"
    if out.exists() and not refresh:
        return pd.read_parquet(out)
    html = requests.get(WIKI_SP500_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    df = pd.read_html(io.StringIO(html))[0]
    df = df.rename(columns={
        "Symbol": "ticker", "Security": "name", "GICS Sector": "gics_sector",
        "GICS Sub-Industry": "gics_sub_industry", "Headquarters Location": "hq_location",
        "Date added": "date_added_to_index", "CIK": "cik", "Founded": "founded",
    })
    df["cik"] = df["cik"].astype(int)
    # Yahoo uses '-' for share classes (BRK.B -> BRK-B)
    df["yf_ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    df["founded_year"] = pd.to_numeric(df["founded"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce")
    df["years_in_index"] = (pd.Timestamp.today() - pd.to_datetime(df["date_added_to_index"], errors="coerce")).dt.days / 365.25
    df = df.reset_index(drop=True)
    df.to_parquet(out)
    return df
