"""End-to-end builder for the S&P 500 risk dataset.

Usage:
    python build_dataset.py            # first LIMIT companies (default 100)
    SP500_LIMIT=503 python build_dataset.py   # full index
"""
import argparse
import sys

from pipeline import (
    collect_sec_fundamentals,
    collect_sec_risk_text,
    collect_yahoo,
    features,
    scoring,
    universe as universe_mod,
)
from pipeline.config import LIMIT, PROCESSED


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=LIMIT)
    ap.add_argument("--refresh-universe", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[], help="collectors to skip: yahoo sec_fund sec_risk")
    args = ap.parse_args()

    print("Loading S&P 500 universe ...")
    uni_full = universe_mod.load_universe(refresh=args.refresh_universe)
    uni = uni_full.head(args.limit).copy()
    print(f"Processing {len(uni)} / {len(uni_full)} companies.\n")

    print("1/3 Yahoo Finance (market, governance, insider) ...")
    y = (collect_yahoo.collect_yahoo(uni) if "yahoo" not in args.skip
         else __import__("pandas").read_parquet(PROCESSED / "yahoo.parquet"))

    print("\n2/3 SEC XBRL fundamentals ...")
    sf = (collect_sec_fundamentals.collect_sec_fundamentals(uni) if "sec_fund" not in args.skip
          else __import__("pandas").read_parquet(PROCESSED / "sec_fundamentals.parquet"))

    print("\n3/3 SEC risk-factor language ...")
    sr = (collect_sec_risk_text.collect_sec_risk_text(uni) if "sec_risk" not in args.skip
          else __import__("pandas").read_parquet(PROCESSED / "sec_risk_text.parquet"))

    print("\nEngineering features ...")
    feat = features.build_features(uni, y, sf, sr)

    print("Scoring ...")
    scored = scoring.score(feat)

    out = PROCESSED / "sp500_risk_dataset.parquet"
    scored.to_parquet(out)
    scored.to_csv(PROCESSED / "sp500_risk_dataset.csv", index=False)
    print(f"\nDone. {scored.shape[0]} rows x {scored.shape[1]} cols -> {out}")
    print(scored[["ticker", "name", "risk_composite", "risk_rank"]].sort_values("risk_rank").head(10).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
