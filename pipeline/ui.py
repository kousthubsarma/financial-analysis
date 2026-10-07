"""Shared UI theme: palette, CSS, Plotly template, and reusable components."""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---- palette ----
BG = "#0e1117"
PANEL = "#171b26"
PANEL_2 = "#1e2432"
BORDER = "#2a3142"
TEXT = "#e6e9ef"
MUTED = "#8b93a7"
ACCENT = "#6ea8fe"

# risk gradient (low -> high)
RISK_SCALE = [
    [0.0, "#1a9850"], [0.25, "#91cf60"], [0.5, "#fee08b"],
    [0.75, "#fc8d59"], [1.0, "#d73027"],
]

GREEN = "#2ec27e"
AMBER = "#f0b429"
RED = "#f0506e"


def risk_color(pct: float) -> str:
    if pct is None:
        return MUTED
    if pct < 34:
        return GREEN
    if pct < 67:
        return AMBER
    return RED


def risk_label(pct: float) -> str:
    if pct < 34:
        return "Low"
    if pct < 67:
        return "Moderate"
    return "Elevated"


def register_plotly_theme():
    """A dark Plotly template used across all charts for a consistent look."""
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=TEXT, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[ACCENT, "#8e7cff", "#4dd4ac", "#f0b429", "#f0506e", "#2ec27e"],
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER),
        hoverlabel=dict(bgcolor=PANEL_2, bordercolor=BORDER, font_size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    pio.templates["sprisk"] = tmpl
    pio.templates.default = "plotly_dark+sprisk"


CSS = f"""
<style>
#MainMenu, footer {{visibility: hidden;}}
.block-container {{padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1300px;}}

/* hero header */
.hero {{
  background: linear-gradient(120deg, #1b2742 0%, #15213a 45%, #1a1430 100%);
  border: 1px solid {BORDER};
  border-radius: 16px;
  padding: 22px 26px;
  margin-bottom: 18px;
}}
.hero h1 {{
  margin: 0; font-size: 30px; font-weight: 700; letter-spacing: -0.5px; color: {TEXT};
}}
.hero p {{margin: 6px 0 0; color: {MUTED}; font-size: 14px;}}
.hero .pill {{
  display:inline-block; margin-top:12px; margin-right:8px; padding:4px 12px;
  background: rgba(110,168,254,0.12); border:1px solid rgba(110,168,254,0.3);
  border-radius: 999px; color:{ACCENT}; font-size:12px; font-weight:600;
}}

/* metric cards */
div[data-testid="stMetric"] {{
  background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px;
  padding: 14px 16px;
}}
div[data-testid="stMetricLabel"] p {{color: {MUTED}; font-size: 12px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.4px;}}
div[data-testid="stMetricValue"] {{font-size: 26px; font-weight: 700;}}

/* ---- tab bar: segmented pill control ---- */
div[data-baseweb="tab-list"] {{
  gap: 4px;
  background: {PANEL};
  border: 1px solid {BORDER};
  border-radius: 12px;
  padding: 5px;
  margin-bottom: 18px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
}}
button[data-baseweb="tab"] {{
  flex: 1;
  height: 42px;
  font-size: 14px;
  font-weight: 600;
  color: {MUTED};
  background: transparent;
  border-radius: 9px;
  padding: 0 14px;
  transition: background .15s ease, color .15s ease;
}}
button[data-baseweb="tab"]:hover {{
  background: {PANEL_2};
  color: {TEXT};
}}
button[data-baseweb="tab"][aria-selected="true"] {{
  background: linear-gradient(120deg, rgba(110,168,254,0.22), rgba(142,124,255,0.22));
  color: {TEXT};
  box-shadow: 0 1px 2px rgba(0,0,0,0.3);
}}
/* hide the default underline/highlight bar */
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {{display: none !important;}}
button[data-baseweb="tab"] [data-testid="stMarkdownContainer"] p {{
  font-size: 14px; font-weight: 600; margin: 0;
}}

/* generic panel + section heading */
.panel {{
  background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px;
  padding: 18px 20px; margin-bottom: 14px;
}}
.section-title {{font-size: 16px; font-weight: 700; color: {TEXT}; margin: 2px 0 12px;}}

/* risk badge */
.badge {{display:inline-block; padding:5px 14px; border-radius:999px;
  font-weight:700; font-size:13px;}}

/* sidebar */
section[data-testid="stSidebar"] {{background: {PANEL}; border-right: 1px solid {BORDER};}}
section[data-testid="stSidebar"] h2 {{font-size: 14px; text-transform: uppercase;
  letter-spacing: 0.5px; color: {MUTED};}}

/* dataframe rounding */
div[data-testid="stDataFrame"] {{border: 1px solid {BORDER}; border-radius: 12px;}}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(n_companies: int, asof: str):
    st.markdown(f"""
    <div class="hero">
      <h1>S&amp;P 500 Risk Analysis</h1>
      <p>Multi-dimensional risk scoring from SEC filings, market data, and governance signals.
         Higher score means higher risk, ranked relative to peers.</p>
      <span class="pill">{n_companies} companies</span>
      <span class="pill">Fundamentals as of {asof}</span>
      <span class="pill">7 risk dimensions</span>
    </div>
    """, unsafe_allow_html=True)


def badge(pct: float) -> str:
    c = risk_color(pct)
    return (f'<span class="badge" style="background:{c}22;color:{c};border:1px solid {c}55">'
            f'{risk_label(pct)} · {pct:.0f}</span>')


def _grad_hex(pct):
    """Interpolate the RISK_SCALE to a hex color for a 0-100 value (no matplotlib)."""
    import pandas as pd
    if pd.isna(pct):
        return ""
    t = max(0.0, min(1.0, float(pct) / 100))
    stops = RISK_SCALE
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
            rgb = [int(int(c0[j:j + 2], 16) + f * (int(c1[j:j + 2], 16) - int(c0[j:j + 2], 16)))
                   for j in (1, 3, 5)]
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    return stops[-1][1]


def risk_cell_style(val):
    """Styler callback: tint a risk cell by its 0-100 value."""
    import pandas as pd
    if pd.isna(val):
        return ""
    bg = _grad_hex(val)
    # dark text on light (mid) backgrounds, light text on dark ends
    return f"background-color:{bg}; color:#0e1117; font-weight:600;"
