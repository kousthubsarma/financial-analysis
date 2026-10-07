"""S&P 500 Risk Analysis — Streamlit app."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import ui
from pipeline.config import PROCESSED
from pipeline.scoring import DEFAULT_WEIGHTS, DIMENSIONS, score

st.set_page_config(page_title="S&P 500 Risk Analysis", layout="wide", page_icon="📊")
ui.inject_css()
ui.register_plotly_theme()

DIM_LABELS = {
    "financial": "Financial", "liquidity": "Liquidity", "debt": "Debt / Leverage",
    "market": "Market", "governance": "Governance", "innovation": "Innovation",
    "risk_language": "Risk Language",
}
DIM_COLS = [f"risk_{d}" for d in DIMENSIONS]


def _dim_label(col: str) -> str:
    """Map a 'risk_<dim>' column to its display label (prefix-safe)."""
    return DIM_LABELS[col[len("risk_"):]]


def render_risk_bars(row):
    """Horizontal gauge per risk dimension with smooth filled bars."""
    rows_html = []
    for d in DIMENSIONS:
        val = row.get(f"risk_{d}")
        label = DIM_LABELS[d]
        if pd.isna(val):
            rows_html.append(f"""
            <div class="rb-row">
              <div class="rb-label">{label}</div>
              <div class="rb-track"></div>
              <div class="rb-val" style="color:{ui.MUTED}">n/a</div>
            </div>""")
            continue
        pct = float(val)
        color = ui.risk_color(pct)
        rows_html.append(f"""
        <div class="rb-row">
          <div class="rb-label">{label}</div>
          <div class="rb-track"><div class="rb-fill" style="width:{pct:.0f}%;background:{color}"></div></div>
          <div class="rb-val" style="color:{color}">{pct:.0f}</div>
        </div>""")
    st.markdown(f"""
    <style>
    .rb-row {{display:flex; align-items:center; gap:14px; margin:9px 0;}}
    .rb-label {{width:130px; font-size:13px; color:{ui.TEXT}; font-weight:600;}}
    .rb-track {{flex:1; height:12px; background:{ui.PANEL_2}; border-radius:999px; overflow:hidden;
      border:1px solid {ui.BORDER};}}
    .rb-fill {{height:100%; border-radius:999px; transition:width .4s ease;}}
    .rb-val {{width:34px; text-align:right; font-weight:700; font-size:14px;}}
    </style>
    <div>{''.join(rows_html)}</div>
    """, unsafe_allow_html=True)


@st.cache_data
def load_base() -> pd.DataFrame:
    p = PROCESSED / "sp500_risk_dataset.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def fmt_b(x):
    if pd.isna(x):
        return "—"
    for unit, div in [("T", 1e12), ("B", 1e9), ("M", 1e6)]:
        if abs(x) >= div:
            return f"${x / div:.1f}{unit}"
    return f"${x:,.0f}"


def section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


base = load_base()
if base.empty:
    st.error("Dataset not found. Run `python build_dataset.py` first.")
    st.stop()

asof = base["fundamentals_asof"].dropna().astype(str).max() if "fundamentals_asof" in base else "n/a"
ui.hero(len(base), asof)

# ---------------- sidebar: weights + filters ----------------
st.sidebar.header("Composite weights")
st.sidebar.caption("Adjust how dimensions contribute to the composite score. Rescoring is live.")
weights = {}
for d in DIMENSIONS:
    weights[d] = st.sidebar.slider(DIM_LABELS[d], 0.0, 1.0, float(DEFAULT_WEIGHTS[d]), 0.01)
if st.sidebar.button("Reset weights"):
    st.rerun()

df = score(base, weights)

st.sidebar.header("Filters")
sectors = sorted(df["gics_sector"].dropna().unique())
sel_sectors = st.sidebar.multiselect("Sectors", sectors, default=sectors)
view = df[df["gics_sector"].isin(sel_sectors)].copy()

if view.empty:
    st.warning("No companies match the current filters. Select at least one sector.")
    st.stop()

tab_over, tab_company, tab_sector, tab_explore, tab_data = st.tabs(
    ["📊  Overview", "🏢  Company", "🏭  Sector", "🔍  Explorer", "🗂  Data"]
)

# ---------------- overview ----------------
with tab_over:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", len(view))
    c2.metric("Avg composite risk", f"{view['risk_composite'].mean():.1f}")
    hi = view.loc[view["risk_composite"].idxmax()] if len(view) else None
    c3.metric("Highest risk", hi["ticker"] if hi is not None else "—",
              f"{hi['risk_composite']:.0f}" if hi is not None else "")
    lo = view.loc[view["risk_composite"].idxmin()] if len(view) else None
    c4.metric("Lowest risk", lo["ticker"] if lo is not None else "—",
              f"{lo['risk_composite']:.0f}" if lo is not None else "")

    st.write("")
    top = view.sort_values("risk_composite", ascending=False)
    lcol, rcol = st.columns([3, 2])
    with lcol:
        section("Highest-risk companies")
        fig = px.bar(top.head(20), x="risk_composite", y="ticker", orientation="h",
                     color="risk_composite", color_continuous_scale=ui.RISK_SCALE,
                     range_color=[0, 100], hover_data=["name", "gics_sector"],
                     labels={"risk_composite": "Composite risk", "ticker": ""})
        fig.update_layout(height=560, yaxis={"categoryorder": "total ascending"},
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with rcol:
        section("Risk distribution")
        hist = px.histogram(view, x="risk_composite", nbins=24,
                            labels={"risk_composite": "Composite risk"})
        hist.update_traces(marker_color=ui.ACCENT, marker_line_color=ui.BG, marker_line_width=1)
        hist.update_layout(height=250, bargap=0.05, yaxis_title="Companies")
        st.plotly_chart(hist, use_container_width=True)

        section("Risk tier mix")
        tiers = pd.cut(view["risk_composite"], [0, 34, 67, 100],
                       labels=["Low", "Moderate", "Elevated"])
        tc = tiers.value_counts().reindex(["Low", "Moderate", "Elevated"]).fillna(0)
        donut = go.Figure(go.Pie(labels=tc.index, values=tc.values, hole=0.62,
                                 marker_colors=[ui.GREEN, ui.AMBER, ui.RED], sort=False))
        donut.update_layout(height=250, showlegend=True,
                            legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(donut, use_container_width=True)

    section("Dimension heatmap · highest-risk 30")
    hm = top.head(30).set_index("ticker")[DIM_COLS]
    hm.columns = [_dim_label(c) for c in hm.columns]
    fig2 = px.imshow(hm, color_continuous_scale=ui.RISK_SCALE, zmin=0, zmax=100,
                     aspect="auto", labels={"color": "Risk"})
    fig2.update_layout(height=720)
    st.plotly_chart(fig2, use_container_width=True)

# ---------------- company ----------------
with tab_company:
    tk = st.selectbox("Company", view.sort_values("ticker")["ticker"],
                      format_func=lambda t: f"{t} — {view.loc[view.ticker == t, 'name'].iloc[0]}")
    row = view.loc[view["ticker"] == tk].iloc[0]
    hcol1, hcol2 = st.columns([4, 1])
    with hcol1:
        st.markdown(f"### {row['name']} ({tk})")
        st.caption(f"{row.get('gics_sector', '')} · {row.get('gics_sub_industry', '')} · {row.get('hq_location', '')}")
    with hcol2:
        st.markdown(f"<div style='text-align:right;padding-top:10px'>{ui.badge(row['risk_composite'])}</div>",
                    unsafe_allow_html=True)

    k = st.columns(5)
    k[0].metric("Composite risk", f"{row['risk_composite']:.0f}")
    k[1].metric("Rank", f"{int(row['risk_rank'])} / {len(view)}" if pd.notna(row["risk_rank"]) else "—")
    k[2].metric("Market cap", fmt_b(row.get("marketCap")))
    k[3].metric("Revenue (TTM/FY)", fmt_b(row.get("revenue")))
    k[4].metric("Beta", f"{row.get('beta'):.2f}" if pd.notna(row.get("beta")) else "—")

    st.write("")
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        section("Risk breakdown by dimension")
        render_risk_bars(row)
        st.write("")
        section("Risk profile vs. universe")
        dims = [DIM_LABELS[d] for d in DIMENSIONS]
        vals = [row.get(f"risk_{d}", np.nan) for d in DIMENSIONS]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(r=vals, theta=dims, fill="toself", name=tk,
                                        line_color=ui.ACCENT))
        radar.add_trace(go.Scatterpolar(r=[view[f"risk_{d}"].mean() for d in DIMENSIONS],
                                        theta=dims, name="Universe avg", opacity=0.45,
                                        line_color=ui.MUTED))
        radar.update_layout(polar={"radialaxis": {"range": [0, 100]},
                                   "bgcolor": "rgba(0,0,0,0)"}, height=400,
                            legend=dict(orientation="h", y=-0.12))
        st.plotly_chart(radar, use_container_width=True)
    with cc2:
        section("Key metrics")
        metrics = {
            "Net margin": row.get("net_margin_sec"), "ROA": row.get("roa_sec"),
            "Revenue growth (YoY)": row.get("revenue_growth_sec"),
            "Current ratio": row.get("current_ratio_sec"),
            "Debt / equity": row.get("debt_to_equity_sec"),
            "Interest coverage": row.get("interest_coverage"),
            "Altman Z": row.get("altman_z"), "Annualized volatility": row.get("annualized_volatility"),
            "Max drawdown (1y)": row.get("max_drawdown_1y"),
            "ISS overall risk (1-10)": row.get("overallRisk"),
            "R&D intensity": row.get("rd_intensity"),
            "Risk-text change (YoY)": row.get("risk_text_change"),
        }
        md = pd.DataFrame({"Metric": metrics.keys(),
                           "Value": [f"{v:.3f}" if isinstance(v, (int, float, np.floating)) and pd.notna(v) else "—"
                                     for v in metrics.values()]})
        st.dataframe(md, hide_index=True, use_container_width=True)

    summ = row.get("longBusinessSummary")
    if isinstance(summ, str) and summ:
        with st.expander("Business summary"):
            st.write(summ)

# ---------------- sector ----------------
with tab_sector:
    section("Average composite risk by sector")
    sec = df.groupby("gics_sector").agg(
        composite=("risk_composite", "mean"), n=("ticker", "count")).reset_index().sort_values("composite")
    fig = px.bar(sec, x="composite", y="gics_sector", orientation="h", color="composite",
                 color_continuous_scale=ui.RISK_SCALE, range_color=[0, 100], hover_data=["n"],
                 labels={"composite": "Avg composite risk", "gics_sector": ""})
    fig.update_layout(height=450, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    section("Dimension averages by sector")
    sd = df.groupby("gics_sector")[DIM_COLS].mean()
    sd.columns = [_dim_label(c) for c in sd.columns]
    st.plotly_chart(px.imshow(sd, color_continuous_scale=ui.RISK_SCALE, zmin=0, zmax=100,
                              aspect="auto", labels={"color": "Risk"}).update_layout(height=500),
                    use_container_width=True)

# ---------------- explorer ----------------
with tab_explore:
    section("Scatter explorer")
    numeric = sorted([c for c in view.columns if pd.api.types.is_numeric_dtype(view[c])
                      and view[c].notna().sum() > 3])
    c1, c2, c3 = st.columns(3)
    xdef = numeric.index("debt_to_equity_sec") if "debt_to_equity_sec" in numeric else 0
    ydef = numeric.index("annualized_volatility") if "annualized_volatility" in numeric else 1
    x = c1.selectbox("X", numeric, index=xdef)
    y = c2.selectbox("Y", numeric, index=ydef)
    size = c3.selectbox("Size", ["(none)"] + numeric,
                        index=(numeric.index("marketCap") + 1) if "marketCap" in numeric else 0)
    plot = view.dropna(subset=[x, y]).copy()
    if size != "(none)":
        plot = plot.dropna(subset=[size])
        plot[size] = plot[size].clip(lower=0)
    fig = px.scatter(plot, x=x, y=y, color="risk_composite", size=None if size == "(none)" else size,
                     hover_name="ticker", hover_data=["name", "gics_sector"],
                     color_continuous_scale=ui.RISK_SCALE, range_color=[0, 100])
    fig.update_traces(marker=dict(line=dict(width=0.5, color=ui.BG)))
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)

# ---------------- data ----------------
with tab_data:
    section("Full dataset")
    show = ["ticker", "name", "gics_sector", "risk_rank", "risk_composite"] + DIM_COLS
    show = [c for c in show if c in view.columns]
    tbl = view.sort_values("risk_composite", ascending=False)[show].rename(
        columns={"risk_composite": "composite", "risk_rank": "rank", "gics_sector": "sector",
                 **{f"risk_{d}": DIM_LABELS[d] for d in DIMENSIONS}})
    risk_cols = ["composite"] + [DIM_LABELS[d] for d in DIMENSIONS]
    styled = (tbl.style
              .map(ui.risk_cell_style, subset=risk_cols)
              .format({c: "{:.0f}" for c in risk_cols}))
    st.dataframe(styled, hide_index=True, use_container_width=True, height=560)
    st.download_button("⬇ Download full CSV", view.to_csv(index=False).encode(),
                       "sp500_risk_dataset.csv", "text/csv")
