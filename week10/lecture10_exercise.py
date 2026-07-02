"""
Lecture 10 Exercise — CO₂ Emissions Dashboard
BBD (Big Book of Dashboards) + SWD (Storytelling with Data) conventions applied throughout.
Run: streamlit run lecture10_exercise.py
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CO₂ Emissions Explorer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global style — white background, clean typography ─────────────────────────
st.markdown(
    """
    <style>
        /* Main area */
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #F7F8FA; }
        /* Caption / filter summary */
        .filter-bar {
            background: #EEF2F7;
            border-left: 3px solid #2E75B6;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 0.82rem;
            color: #444;
            margin-bottom: 0.8rem;
        }
        /* KPI cards */
        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 18px;
            text-align: center;
        }
        .kpi-label  { font-size: 0.75rem; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em; }
        .kpi-value  { font-size: 1.6rem; font-weight: 600; color: #1E3A5F; line-height: 1.2; }
        .kpi-delta  { font-size: 0.78rem; margin-top: 2px; }
        .delta-up   { color: #C0392B; }   /* more CO2 = bad → red */
        .delta-down { color: #1A7A4A; }   /* less CO2 = good → green */
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Palette (semantic, CVD-safe) ──────────────────────────────────────────────
BLUE      = "#2E75B6"   # highlight / top-emitter line
GREY      = "#B0B7C3"   # de-emphasised lines (SWD grey-and-highlight)
RED_SOFT  = "#C0392B"   # negative delta
GREEN     = "#1A7A4A"   # positive delta
BAR_BLUE  = "#4A90C4"   # bar chart fill (categorical — single hue)

CHART_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial, sans-serif", size=12, color="#2D2D2D"),
    title_font=dict(family="Arial, sans-serif", size=14, color="#1E3A5F"),
    margin=dict(t=55, b=40, l=10, r=10),
    legend=dict(
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#E2E8F0",
        borderwidth=1,
        font=dict(size=11),
    ),
)

# ── Data loader with caching ───────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("co2_emissions.csv")
    df["Date"] = pd.to_datetime(df["Year"].astype(str) + "-01-01")
    return df


df = load_data()

MIN_DATE = datetime.date(int(df["Year"].min()), 1, 1)
MAX_DATE = datetime.date(int(df["Year"].max()), 1, 1)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌍 CO₂ Emissions Explorer")
st.caption("Source: Our World in Data — ourworldindata.org/co2-emissions  |  Dataset: 15 major economies, 2000–2022")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — Sidebar: 5 widgets + chained filter + guards
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("Filters")

    # (a) selectbox — Region (chained to Country list below)
    regions = ["All"] + sorted(df["Region"].unique())
    selected_region = st.selectbox("Region", regions, index=0)

    # Build country list chained to selected region
    if selected_region == "All":
        country_pool = sorted(df["Country"].unique())
    else:
        country_pool = sorted(
            df[df["Region"] == selected_region]["Country"].unique()
        )

    # (b) multiselect — Countries (pre-seeded with pool so 'All' works intuitively)
    selected_countries = st.multiselect(
        "Countries",
        options=country_pool,
        default=country_pool,          # all countries in region selected by default
    )

    st.divider()

    # (c) date_input — two-handle date range
    date_range = st.date_input(
        "Date range",
        value=(MIN_DATE, MAX_DATE),
        min_value=MIN_DATE,
        max_value=MAX_DATE,
        format="YYYY-MM-DD",
    )

    st.divider()

    # (d) radio — Metric toggle
    metric = st.radio(
        "Metric",
        ["Total CO₂ (Mt)", "CO₂ per capita"],
        index=0,
    )

    # (e) checkbox — SWD grey-and-highlight mode
    highlight_top = st.checkbox("Highlight top emitter only", value=False)

    st.divider()
    st.caption("BBD: all filters in one place — users see all options simultaneously.")

# ── Guards ────────────────────────────────────────────────────────────────────
if not selected_countries:
    st.warning("⚠️ Select at least one country in the sidebar.")
    st.stop()

if len(date_range) != 2:
    st.warning("⚠️ Please select both a start **and** an end date.")
    st.stop()

# ── Apply filters ─────────────────────────────────────────────────────────────
start_ts = pd.Timestamp(date_range[0])
end_ts   = pd.Timestamp(date_range[1])

filtered = df[
    df["Country"].isin(selected_countries)
    & (df["Date"] >= start_ts)
    & (df["Date"] <= end_ts)
].copy()

if filtered.empty:
    st.warning("⚠️ No data matches the current filters. Adjust region, countries, or date range.")
    st.stop()

# Resolve column and label from metric toggle
y_col   = "CO2_Mt"       if metric == "Total CO₂ (Mt)" else "CO2_per_capita"
y_label = "CO₂ (Mt)"     if y_col == "CO2_Mt"          else "CO₂ per Capita (t)"

# ══════════════════════════════════════════════════════════════════════════════
# EXTENSION — KPI row (placed above charts, BBD Ch.8 Multiple KPIs)
# ══════════════════════════════════════════════════════════════════════════════
last_year  = int(filtered["Year"].max())
first_year = int(filtered["Year"].min())

last_year_data  = filtered[filtered["Year"] == last_year]
first_year_data = filtered[filtered["Year"] == first_year]

total_last  = last_year_data[y_col].sum()
total_first = first_year_data[y_col].sum()
pct_change  = ((total_last - total_first) / total_first * 100) if total_first else 0

top_emitter_row = last_year_data.loc[last_year_data[y_col].idxmax()]
top_emitter     = top_emitter_row["Country"]
top_emitter_val = top_emitter_row[y_col]

k1, k2, k3, k4 = st.columns(4)

def _delta_html(pct: float) -> str:
    arrow = "▲" if pct > 0 else "▼"
    cls   = "delta-up" if pct > 0 else "delta-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}% vs {first_year}</span>'

with k1:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Total {metric} in {last_year}</div>
            <div class="kpi-value">{total_last:,.0f}</div>
            <div class="kpi-delta">{_delta_html(pct_change)}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Countries shown</div>
            <div class="kpi-value">{len(selected_countries)}</div>
            <div class="kpi-delta" style="color:#6B7280;">{selected_region}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Top emitter in {last_year}</div>
            <div class="kpi-value" style="font-size:1.25rem;">{top_emitter}</div>
            <div class="kpi-delta" style="color:#6B7280;">{top_emitter_val:,.0f} {y_label}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with k4:
    years_shown = last_year - first_year
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Period</div>
            <div class="kpi-value">{first_year}–{last_year}</div>
            <div class="kpi-delta" style="color:#6B7280;">{years_shown} year span</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Filter summary caption (BBD: always show matching record count)
# ══════════════════════════════════════════════════════════════════════════════
summary = (
    f"🔍  <b>{len(selected_countries)} countries</b> &nbsp;|&nbsp; "
    f"Region: <b>{selected_region}</b> &nbsp;|&nbsp; "
    f"{date_range[0].strftime('%d %b %Y')} – {date_range[1].strftime('%d %b %Y')} &nbsp;|&nbsp; "
    f"Metric: <b>{metric}</b> &nbsp;|&nbsp; "
    f"{len(filtered)} data points"
)
st.markdown(f'<div class="filter-bar">{summary}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Two charts reacting to all filters
# ══════════════════════════════════════════════════════════════════════════════
col_left, col_right = st.columns([2, 1])

# ── LEFT: Line chart ──────────────────────────────────────────────────────────
with col_left:
    # Colour type: sequential single-hue palette (qualitative for multi-country)
    # When highlight_top ON → SWD grey-and-highlight: one blue line, all others grey

    if highlight_top:
        # Identify the highest total emitter over the full selected period
        country_totals = (
            filtered.groupby("Country")[y_col].sum().reset_index()
        )
        top_country = country_totals.loc[country_totals[y_col].idxmax(), "Country"]

        # Build figure manually (go.Figure) so we control line colour per trace
        fig_line = go.Figure()

        for country in filtered["Country"].unique():
            country_df = filtered[filtered["Country"] == country].sort_values("Year")
            is_top = country == top_country

            # End-of-line annotation only for the highlighted country (SWD p.187)
            last_row = country_df.iloc[-1]

            fig_line.add_trace(
                go.Scatter(
                    x=country_df["Year"],
                    y=country_df[y_col],
                    mode="lines",
                    name=country,
                    line=dict(
                        color=BLUE if is_top else GREY,
                        width=2.5 if is_top else 1.2,
                    ),
                    opacity=1.0 if is_top else 0.55,
                    showlegend=True,
                )
            )
            if is_top:
                fig_line.add_annotation(
                    x=last_row["Year"],
                    y=last_row[y_col],
                    text=f"<b>{top_country}</b>",
                    showarrow=False,
                    xanchor="left",
                    xshift=6,
                    font=dict(color=BLUE, size=11),
                )

        insight_suffix = f"— {top_country} leads in {last_year}"
    else:
        # Standard multi-line chart (qualitative palette, muted)
        # Colour type: qualitative (one colour per country)
        n = len(selected_countries)
        palette = px.colors.qualitative.Safe[:n] if n <= 10 else px.colors.qualitative.Alphabet[:n]

        fig_line = px.line(
            filtered.sort_values("Year"),
            x="Year",
            y=y_col,
            color="Country",
            color_discrete_sequence=palette,
            labels={y_col: y_label, "Year": ""},
        )
        fig_line.update_traces(line_width=2)
        insight_suffix = f"— {last_year} latest data point"

    # Insight title (SWD: name the finding, not the topic)
    line_title = (
        f"China's emissions dwarf all others {insight_suffix}"
        if "China" in selected_countries and highlight_top
        else f"{metric} trends, {first_year}–{last_year} {insight_suffix}"
    )

    fig_line.update_layout(
        **CHART_LAYOUT,
        title=dict(text=line_title, x=0),
        xaxis=dict(
            showgrid=False,
            title="",
            tickmode="linear",
            dtick=4 if (last_year - first_year) > 10 else 2,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#ECECEC",
            gridwidth=1,
            title=y_label,
            rangemode="tozero",           # zero baseline (SWD p.51)
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ── RIGHT: Horizontal bar chart — ranking in last selected year ────────────────
with col_right:
    # Colour type: single-hue sequential (one bar per country, ranked)
    ranking = (
        last_year_data[["Country", y_col]]
        .sort_values(y_col, ascending=True)   # ascending so longest bar is at top
        .reset_index(drop=True)
    )

    # Assign colour: top emitter gets accent blue, rest get lighter shade
    bar_colors = [
        BLUE if c == ranking.iloc[-1]["Country"] else BAR_BLUE
        for c in ranking["Country"]
    ]

    fig_bar = go.Figure(
        go.Bar(
            x=ranking[y_col],
            y=ranking["Country"],
            orientation="h",
            marker_color=bar_colors,        # single-hue: highlight top bar
            marker_line_width=0,
            text=ranking[y_col].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
            textfont=dict(size=10, color="#444"),
            cliponaxis=False,
        )
    )

    bar_title = (
        f"Ranking by {metric}<br><sup>Last year in range: {last_year}</sup>"
    )

    fig_bar.update_layout(
        **CHART_LAYOUT,
        title=dict(text=bar_title, x=0),
        xaxis=dict(
            showgrid=True,
            gridcolor="#ECECEC",
            title=y_label,
            rangemode="tozero",            # zero baseline (SWD p.51)
            range=[0, ranking[y_col].max() * 1.22],   # room for outside labels
        ),
        yaxis=dict(showgrid=False, title=""),
        showlegend=False,
    )
    fig_bar.update_layout(margin=dict(t=65, b=40, l=10, r=40))
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Data: Our World in Data — CO₂ and Greenhouse Gas Emissions. "
    "15 major economies, 2000–2022. "
    "CO₂ (Mt) = million tonnes of CO₂ equivalent. "
    "Per-capita figures in tonnes per person."
)
