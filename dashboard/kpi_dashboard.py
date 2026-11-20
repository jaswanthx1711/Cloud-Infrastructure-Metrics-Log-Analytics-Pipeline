"""
kpi_dashboard.py  —  E-Commerce Business Analytics KPI Pipeline
Interactive dashboard for channel KPIs, funnel analysis, cohort retention,
A/B testing, and RFM customer segmentation.
"""

import datetime
import os
import sys
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Paths — prefer centralised config, fall back to local resolve ────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from config import DB_PATH
except ImportError:
    REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DB_PATH   = os.path.join(REPO_ROOT, "data", "analytics.db")

# ── Page config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="E-Commerce Analytics · KPI Pipeline",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Guard: ensure pipeline has been run ─────────────────────────────────
if not os.path.exists(DB_PATH):
    st.error(
        "⚠️ **Database not found.**\n\n"
        "Run `python3 etl/pipeline.py` (or `make run`) first to generate the analytics database."
    )
    st.stop()

# ── Colour palette (used everywhere) ───────────────────────────────────
C = {
    "bg":          "#080C14",
    "surface":     "#0F1623",
    "surface2":    "#151D2E",
    "border":      "#1E2D45",
    "accent":      "#3B82F6",      # electric blue
    "accent2":     "#8B5CF6",      # violet
    "accent3":     "#06B6D4",      # cyan
    "green":       "#10B981",
    "amber":       "#F59E0B",
    "red":         "#EF4444",
    "text":        "#F0F4FF",
    "muted":       "#6B7FA8",
    "chart_seq":   ["#3B82F6","#8B5CF6","#06B6D4","#10B981","#F59E0B","#EF4444"],
}

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=C["text"], size=12),
    margin=dict(l=12, r=12, t=28, b=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)

AXIS_STYLE = dict(gridcolor="#1E2D45", zerolinecolor="#1E2D45")

# ── Global CSS ──────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset / global ──────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
    background-color: {C['bg']} !important;
    color: {C['text']};
}}
.stApp, .stApp > div, [data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
section.main, .main {{
    background-color: {C['bg']} !important;
}}
.main .block-container  {{
    padding: 1.6rem 2.2rem 2rem;
    max-width: 1400px;
    background-color: {C['bg']} !important;
}}
footer, header {{ visibility: hidden; }}
h1, h2, h3, h4, .page-title {{ color: {C['text']} !important; }}

/* ── Sidebar ─────────────────────────────── */
[data-testid="stSidebar"] {{
    background: {C['surface']} !important;
    border-right: 1px solid {C['border']};
}}
[data-testid="stSidebar"] .stRadio label {{
    font-size: 0.88rem;
    color: {C['muted']};
    padding: 0.45rem 0.7rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.18s;
}}
[data-testid="stSidebar"] .stRadio label:hover {{
    color: {C['text']};
    background: rgba(59,130,246,0.12);
}}

/* ── KPI Metric Card ─────────────────────── */
.kpi-card {{
    background: linear-gradient(145deg, {C['surface']} 0%, {C['surface2']} 100%);
    border: 1px solid {C['border']};
    border-radius: 16px;
    padding: 1.35rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}}
.kpi-card::before {{
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 16px;
    opacity: 0;
    transition: opacity 0.2s;
    background: radial-gradient(circle at 60% 0%, rgba(59,130,246,0.06) 0%, transparent 70%);
}}
.kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.5); }}
.kpi-card:hover::before {{ opacity: 1; }}
.kpi-accent-bar {{
    height: 3px;
    border-radius: 3px;
    margin-bottom: 1rem;
}}
.kpi-label {{
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {C['muted']};
    margin-bottom: 0.4rem;
}}
.kpi-value {{
    font-size: 1.95rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
    color: {C['text']};
}}
.kpi-sub {{
    font-size: 0.75rem;
    color: {C['muted']};
    margin-top: 0.45rem;
}}
.kpi-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 99px;
    margin-top: 0.5rem;
}}
.badge-up   {{ background: rgba(16,185,129,0.15); color: #10B981; }}
.badge-down {{ background: rgba(239,68,68,0.15);  color: #EF4444; }}

/* ── Section Headers ─────────────────────── */
.section-title {{
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {C['muted']};
    margin: 2rem 0 0.9rem;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.section-title::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: {C['border']};
}}

/* ── Page Title ──────────────────────────── */
.page-title {{
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 0.25rem;
    color: {C['text']};
}}
.page-sub {{
    font-size: 0.88rem;
    color: {C['muted']};
    margin-bottom: 1.6rem;
}}

/* ── Chart Card ──────────────────────────── */
.chart-card {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 14px;
    padding: 1.2rem 1.4rem 0.8rem;
}}
.chart-title {{
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {C['muted']};
    margin-bottom: 0.6rem;
}}

/* ── Sidebar Brand ───────────────────────── */
.brand {{
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: {C['text']};
    margin-bottom: 0.1rem;
}}
.brand-sub {{
    font-size: 0.73rem;
    color: {C['muted']};
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.sidebar-divider {{
    height: 1px;
    background: {C['border']};
    margin: 1rem 0;
}}
.nav-section {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {C['muted']};
    margin: 0.6rem 0 0.3rem;
}}

/* ── Dataframe overrides ─────────────────── */
[data-testid="stDataFrame"] {{ border-radius: 12px; border: 1px solid {C['border']}; overflow:hidden; }}

/* ── Streamlit radio tweak ───────────────── */
.stRadio > div {{ gap: 4px; }}
</style>
""", unsafe_allow_html=True)


# ── DB connection ───────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    if not os.path.exists(DB_PATH):
        st.error("Run `python etl/pipeline.py` first to build the database.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_conn()

@st.cache_data(ttl=300)
def q(sql): return pd.read_sql(sql, conn)


# ── Queries ─────────────────────────────────────────────────────────────
def load_channel_kpis():    return q("SELECT * FROM agg_channel_kpis ORDER BY total_revenue DESC")
def load_monthly_revenue(): return q("""
    SELECT month, channel, SUM(net_revenue) AS revenue, COUNT(DISTINCT order_id) AS orders
    FROM fct_orders WHERE status='completed' GROUP BY month,channel ORDER BY month """)
def load_funnel():          return q("""
    SELECT stage, stage_order, COUNT(DISTINCT user_id) AS users
    FROM fct_events GROUP BY stage,stage_order ORDER BY stage_order """)
def load_ab_test():         return q("""
    WITH v AS (SELECT plan, COUNT(DISTINCT user_id) AS visitors FROM fct_events WHERE stage='visit' GROUP BY plan),
         c AS (SELECT plan, COUNT(DISTINCT user_id) AS converters FROM fct_orders WHERE status='completed' GROUP BY plan)
    SELECT v.plan, v.visitors, COALESCE(c.converters,0) AS converters,
           ROUND(100.*COALESCE(c.converters,0)/v.visitors,2) AS cvr_pct
    FROM v LEFT JOIN c USING(plan) ORDER BY cvr_pct DESC """)
def load_rfm_segments():    return q("""
    WITH rfm_raw AS (
        SELECT user_id,
               JULIANDAY('2026-01-01')-JULIANDAY(MAX(order_date)) AS recency,
               COUNT(DISTINCT order_id) AS frequency,
               SUM(net_revenue) AS monetary
        FROM fct_orders WHERE status='completed' GROUP BY user_id),
    scored AS (
        SELECT *, NTILE(4) OVER(ORDER BY recency DESC) r,
                  NTILE(4) OVER(ORDER BY frequency)    f,
                  NTILE(4) OVER(ORDER BY monetary)     m FROM rfm_raw),
    segs AS (
        SELECT *, CASE
            WHEN r>=3 AND f>=3 AND m>=3 THEN 'Champions'
            WHEN r>=3 AND f>=2          THEN 'Loyal'
            WHEN r>=3 AND f=1           THEN 'Recent'
            WHEN r=2  AND f>=2          THEN 'At Risk'
            WHEN r=1  AND f>=2          THEN 'Cant Lose'
            ELSE 'Low Value' END AS segment FROM scored)
    SELECT segment, COUNT(*) users, ROUND(AVG(monetary),2) avg_ltv,
           ROUND(SUM(monetary),2) total_revenue FROM segs
    GROUP BY segment ORDER BY total_revenue DESC """)


# ── Helpers ─────────────────────────────────────────────────────────────
def kpi_card(label, value, sub="", color=None, badge=None, badge_type="up"):
    bar_color = color or C["accent"]
    badge_html = ""
    if badge:
        cls = "badge-up" if badge_type == "up" else "badge-down"
        arrow = "▲" if badge_type == "up" else "▼"
        badge_html = f'<span class="kpi-badge {cls}">{arrow} {badge}</span>'
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-accent-bar" style="background:linear-gradient(90deg,{bar_color},transparent)"></div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
      {badge_html}
    </div>""", unsafe_allow_html=True)

def section(title, icon=""):
    st.markdown(f'<div class="section-title"><span>{icon}</span>{title}</div>', unsafe_allow_html=True)

def chart_wrap(title, fig, height=320):
    st.markdown(f'<div class="chart-card"><div class="chart-title">{title}</div></div>', unsafe_allow_html=True)
    # Fix layout then render
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def apply_layout(fig, **extra):
    fig.update_layout(**{**PLOTLY_LAYOUT, **extra})
    return fig


# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:0.4rem 0 0.2rem">
      <div style="font-size:1.3rem;margin-bottom:2px">🛒</div>
      <div class="brand">E-Commerce Analytics</div>
      <div class="brand-sub">KPI Pipeline</div>
    </div>
    <div class="sidebar-divider"></div>
    <div class="nav-section">Navigation</div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["📊  KPI Overview",
         "🔽  Funnel Analysis",
         "📅  Revenue & Cohorts",
         "🧪  A/B Test Results",
         "🎯  RFM Segmentation"],
        label_visibility="collapsed",
    )

    st.markdown("""<div class="sidebar-divider"></div>""", unsafe_allow_html=True)

    # Refresh button — clears the query cache
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Data freshness indicator
    _mtime = os.path.getmtime(DB_PATH)
    st.caption(f"📅 Data as of: {datetime.datetime.fromtimestamp(_mtime).strftime('%Y-%m-%d %H:%M')}")
    st.markdown(f'<div style="font-size:0.71rem;color:{C["muted"]};line-height:1.8">'
                '📁 Source: analytics.db<br>🔄 Pipeline: on-demand<br>🗓 Period: 2025</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  PAGE 1 — KPI OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
if "KPI Overview" in page:
    st.markdown('<div class="page-title">KPI Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Executive summary of revenue, acquisition, and conversion performance across all channels</div>', unsafe_allow_html=True)

    kpis    = load_channel_kpis()
    funnel  = load_funnel()

    # Computed globals
    total_rev   = kpis["total_revenue"].sum()
    total_spend = kpis["total_spend"].sum()
    total_buyers= kpis["buyers"].sum()
    avg_cac     = kpis["avg_cac"].mean()
    avg_ltv     = kpis["ltv_estimate"].mean()
    overall_roas= total_rev / total_spend if total_spend > 0 else 0

    visit_n   = funnel.loc[funnel["stage"]=="visit",   "users"].values
    purchase_n= funnel.loc[funnel["stage"]=="purchase","users"].values
    overall_cvr = (purchase_n[0]/visit_n[0]*100) if len(visit_n) and len(purchase_n) else 0

    # ── Row 1 KPI cards ──
    c1,c2,c3,c4 = st.columns(4, gap="small")
    with c1: kpi_card("Total Revenue",  f"${total_rev:,.0f}",  "Completed orders", C["accent"])
    with c2: kpi_card("Overall CVR",    f"{overall_cvr:.1f}%", "Visit → Purchase", C["accent2"], badge="vs funnel", badge_type="up")
    with c3: kpi_card("Avg CAC",        f"${avg_cac:,.2f}",    "Per new customer", C["accent3"])
    with c4: kpi_card("Overall ROAS",   f"{overall_roas:.1f}×","Revenue / Spend",  C["green"],   badge="healthy", badge_type="up")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c5,c6,c7 = st.columns(3, gap="small")
    with c5: kpi_card("Total Buyers",   f"{int(total_buyers):,}", "Unique purchasers", C["accent"])
    with c6: kpi_card("Avg LTV Est.",   f"${avg_ltv:,.0f}",       "3× avg order value", C["amber"])
    with c7: kpi_card("Total Ad Spend", f"${total_spend:,.0f}",   "Across all campaigns", C["red"])

    # ── Revenue by channel ──
    section("Revenue & Efficiency by Channel", "📣")
    ca, cb = st.columns(2, gap="medium")

    with ca:
        fig = go.Figure()
        sorted_kpis = kpis.sort_values("total_revenue")
        fig.add_trace(go.Bar(
            y=sorted_kpis["channel"].str.replace("_"," ").str.title(),
            x=sorted_kpis["total_revenue"],
            orientation="h",
            marker=dict(
                color=sorted_kpis["total_revenue"],
                colorscale=[[0,"#1E2D45"],[0.3,"#3B82F6"],[1.0,"#06B6D4"]],
                line=dict(width=0),
            ),
            text=sorted_kpis["total_revenue"].apply(lambda v: f"${v/1000:.1f}K"),
            textposition="inside",
            textfont=dict(color="white", size=11, family="Inter"),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=280,
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11)),
            bargap=0.28,
        )
        st.markdown('<div class="chart-card"><div class="chart-title">Revenue by Acquisition Channel</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cb:
        fig2 = go.Figure()
        for i, row in kpis.iterrows():
            fig2.add_trace(go.Scatter(
                x=[row["avg_cac"]], y=[row["avg_roas"]],
                mode="markers+text",
                text=[row["channel"].replace("_"," ").title()],
                textposition="top center",
                textfont=dict(size=9, color=C["muted"]),
                marker=dict(
                    size=max(12, row["total_revenue"]/5000),
                    color=C["chart_seq"][i % len(C["chart_seq"])],
                    opacity=0.85,
                    line=dict(width=1.5, color="white"),
                ),
                hovertemplate=f"<b>{row['channel']}</b><br>CAC: ${row['avg_cac']:.2f}<br>ROAS: {row['avg_roas']:.1f}×<extra></extra>",
                showlegend=False,
            ))
        # Reference lines
        fig2.add_hline(y=4, line=dict(color=C["green"], width=1, dash="dot"),
                       annotation_text="ROAS=4× target", annotation_font_color=C["green"],
                       annotation_position="bottom right")
        fig2.update_layout(**PLOTLY_LAYOUT, height=280,
            xaxis=dict(title="Avg CAC ($)", gridcolor="#1E2D45"),
            yaxis=dict(title="Avg ROAS (×)", gridcolor="#1E2D45"),
        )
        st.markdown('<div class="chart-card"><div class="chart-title">CAC vs ROAS Efficiency Matrix</div>', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ── KPI table ──
    section("Channel Performance Table", "📋")
    disp = kpis.copy()
    disp.columns = ["Channel","Buyers","Revenue","Avg Order","LTV Est.","Spend","Conversions","Avg CVR","Avg CAC","Avg ROAS"]
    disp["Revenue"]    = disp["Revenue"].map("${:,.0f}".format)
    disp["Avg Order"]  = disp["Avg Order"].map("${:,.0f}".format)
    disp["LTV Est."]   = disp["LTV Est."].map("${:,.0f}".format)
    disp["Spend"]      = disp["Spend"].map("${:,.0f}".format)
    disp["Avg CVR"]    = disp["Avg CVR"].map("{:.1%}".format)
    disp["Avg CAC"]    = disp["Avg CAC"].map("${:,.2f}".format)
    disp["Avg ROAS"]   = disp["Avg ROAS"].map("{:.1f}×".format)
    disp["Channel"]    = disp["Channel"].str.replace("_"," ").str.title()
    st.dataframe(disp, use_container_width=True, hide_index=True, height=260)


# ══════════════════════════════════════════════════════════════════════════
#  PAGE 2 — FUNNEL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
elif "Funnel" in page:
    st.markdown('<div class="page-title">Funnel Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Step-by-step conversion rates from first visit through to completed purchase</div>', unsafe_allow_html=True)

    funnel = load_funnel()
    top    = funnel["users"].max()
    funnel["cvr_from_top"] = (funnel["users"] / top * 100).round(1)
    funnel["prev"]         = funnel["users"].shift(1).fillna(funnel["users"].iloc[0])
    funnel["step_cvr"]     = (funnel["users"] / funnel["prev"] * 100).round(1)
    funnel["dropoff"]      = (funnel["prev"] - funnel["users"]).astype(int)
    funnel["dropoff_pct"]  = (funnel["dropoff"] / funnel["prev"] * 100).round(1)
    labels = funnel["stage"].str.replace("_"," ").str.title()

    # ── Summary cards ──
    cols = st.columns(5, gap="small")
    palette = [C["accent"], C["accent2"], C["accent3"], C["green"], C["amber"]]
    for i, (_, row) in enumerate(funnel.iterrows()):
        with cols[i]:
            kpi_card(
                labels.iloc[i],
                f"{int(row['users']):,}",
                f"{row['cvr_from_top']}% of top",
                palette[i],
                badge=f"{row['step_cvr']}% step" if i>0 else None,
                badge_type="up" if row["step_cvr"] > 50 else "down"
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    ca, cb = st.columns([1,1], gap="medium")

    with ca:
        # Waterfall funnel
        fig = go.Figure(go.Funnel(
            y=labels,
            x=funnel["users"],
            textinfo="value+percent initial",
            marker=dict(
                color=palette,
                line=dict(width=0),
            ),
            textfont=dict(family="Inter, sans-serif", size=12, color="white"),
            connector=dict(line=dict(color=C["border"], dash="dot", width=1)),
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=350, showlegend=False,
                          title=dict(text="Funnel Waterfall", font=dict(size=13, color=C["muted"]), x=0))
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cb:
        # Step CVR bar
        cvr_df = funnel.iloc[1:].copy()
        colors = [C["green"] if v >= 50 else C["amber"] if v >= 30 else C["red"] for v in cvr_df["step_cvr"]]
        fig2 = go.Figure(go.Bar(
            x=labels.iloc[1:],
            y=cvr_df["step_cvr"],
            marker=dict(color=colors, line=dict(width=0)),
            text=cvr_df["step_cvr"].astype(str) + "%",
            textposition="outside",
            textfont=dict(color=C["text"], size=11),
            hovertemplate="<b>%{x}</b><br>Step CVR: %{y:.1f}%<extra></extra>",
            width=0.55,
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=350,
            showlegend=False,
            yaxis=dict(title="Step CVR %", gridcolor="#1E2D45", range=[0, cvr_df["step_cvr"].max()*1.25]),
            xaxis=dict(title=""),
            title=dict(text="Step-over-Step Conversion Rate", font=dict(size=13, color=C["muted"]), x=0),
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Drop-off table
    section("Drop-off Analysis", "⬇️")
    display = funnel[["stage","users","dropoff","dropoff_pct","step_cvr","cvr_from_top"]].copy()
    display.columns = ["Stage","Users","Dropped","Drop-off %","Step CVR %","% of Top"]
    display["Stage"] = display["Stage"].str.replace("_"," ").str.title()
    st.dataframe(display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
#  PAGE 3 — REVENUE & COHORTS
# ══════════════════════════════════════════════════════════════════════════
elif "Revenue" in page or "Cohort" in page:
    st.markdown('<div class="page-title">Revenue & Cohorts</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Monthly revenue trends, channel mix, and cohort-based retention analysis</div>', unsafe_allow_html=True)

    monthly = load_monthly_revenue()
    monthly_total = monthly.groupby("month")["revenue"].sum().reset_index()

    # ── Revenue trend ──
    section("Monthly Net Revenue Trend", "📈")
    fig = go.Figure()
    # Stacked by channel
    channels = monthly["channel"].unique()
    for i, ch in enumerate(channels):
        ch_data = monthly[monthly["channel"]==ch]
        fig.add_trace(go.Bar(
            x=ch_data["month"], y=ch_data["revenue"],
            name=ch.replace("_"," ").title(),
            marker_color=C["chart_seq"][i % len(C["chart_seq"])],
            hovertemplate=f"<b>{ch}</b><br>%{{x}}<br>Revenue: $%{{y:,.0f}}<extra></extra>",
        ))
    # Overlay total line
    fig.add_trace(go.Scatter(
        x=monthly_total["month"], y=monthly_total["revenue"],
        name="Total",
        line=dict(color="white", width=2, dash="dot"),
        marker=dict(size=5, color="white"),
        hovertemplate="<b>Total</b><br>%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=340, barmode="stack",
        xaxis=dict(title="", tickangle=-30),
        yaxis=dict(title="Revenue ($)", gridcolor="#1E2D45"),
    )
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"))
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Channel mix + monthly heatmap ──
    ca, cb = st.columns(2, gap="medium")

    with ca:
        section("Channel Revenue Mix", "🥧")
        ch_totals = monthly.groupby("channel")["revenue"].sum().reset_index()
        fig2 = go.Figure(go.Pie(
            labels=ch_totals["channel"].str.replace("_"," ").str.title(),
            values=ch_totals["revenue"],
            hole=0.55,
            marker=dict(colors=C["chart_seq"], line=dict(color=C["bg"], width=3)),
            textinfo="label+percent",
            textfont=dict(size=11, family="Inter"),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=300,
            showlegend=False,
            annotations=[dict(text="<b>Revenue</b><br>Mix", x=0.5, y=0.5, showarrow=False,
                              font=dict(size=12, color=C["muted"]), xanchor="center")],
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cb:
        section("Monthly Orders Volume", "📦")
        orders_by_month = monthly.groupby("month")["orders"].sum().reset_index()
        fig3 = go.Figure(go.Scatter(
            x=orders_by_month["month"],
            y=orders_by_month["orders"],
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.10)",
            line=dict(color=C["accent"], width=2.5),
            marker=dict(size=6, color=C["accent"]),
            hovertemplate="<b>%{x}</b><br>Orders: %{y:,}<extra></extra>",
        ))
        fig3.update_layout(**PLOTLY_LAYOUT, height=300,
            xaxis=dict(title="", tickangle=-30),
            yaxis=dict(title="Orders", gridcolor="#1E2D45"),
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Table
    section("Revenue by Month × Channel", "📋")
    pivot = monthly.pivot_table(index="month", columns="channel", values="revenue", aggfunc="sum").fillna(0)
    pivot.columns = [c.replace("_"," ").title() for c in pivot.columns]
    st.dataframe(pivot.style.format("${:,.0f}").background_gradient(cmap="Blues", axis=None),
                 use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
#  PAGE 4 — A/B TEST RESULTS
# ══════════════════════════════════════════════════════════════════════════
elif "A/B" in page:
    st.markdown('<div class="page-title">A/B Test Results</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Conversion rate analysis across plan tiers and acquisition channels — with statistical context</div>', unsafe_allow_html=True)

    ab   = load_ab_test()
    kpis = load_channel_kpis()

    # Summary cards
    best_plan    = ab.loc[ab["cvr_pct"].idxmax(), "plan"]
    best_cvr     = ab["cvr_pct"].max()
    worst_plan   = ab.loc[ab["cvr_pct"].idxmin(), "plan"]
    worst_cvr    = ab["cvr_pct"].min()
    lift         = round(best_cvr - worst_cvr, 2)

    c1,c2,c3 = st.columns(3, gap="small")
    with c1: kpi_card("Best Plan (CVR)", best_plan.title(), f"{best_cvr:.2f}% conversion", C["green"])
    with c2: kpi_card("Worst Plan (CVR)", worst_plan.title(), f"{worst_cvr:.2f}% conversion", C["red"])
    with c3: kpi_card("CVR Lift", f"+{lift:.2f}pp", "Best vs worst plan", C["accent2"], badge="significant", badge_type="up")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    ca, cb = st.columns(2, gap="medium")

    with ca:
        section("CVR by Plan Tier", "📐")
        clrs = [C["green"] if v == ab["cvr_pct"].max() else C["accent"] for v in ab["cvr_pct"]]
        fig = go.Figure(go.Bar(
            x=ab["plan"].str.title(),
            y=ab["cvr_pct"],
            marker=dict(color=clrs, line=dict(width=0)),
            text=ab["cvr_pct"].apply(lambda v: f"{v:.2f}%"),
            textposition="outside",
            textfont=dict(color=C["text"], size=12),
            hovertemplate="<b>%{x}</b><br>CVR: %{y:.2f}%<extra></extra>",
            width=0.55,
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=300,
            showlegend=False,
            yaxis=dict(title="CVR %", gridcolor="#1E2D45",
                       range=[0, ab["cvr_pct"].max()*1.3]),
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cb:
        section("CVR by Acquisition Channel", "📣")
        ch_cvr = kpis.sort_values("avg_cvr", ascending=False).copy()
        ch_cvr["cvr_pct"] = ch_cvr["avg_cvr"] * 100
        clrs2 = [C["green"] if v == ch_cvr["cvr_pct"].max() else C["accent3"] for v in ch_cvr["cvr_pct"]]
        fig2 = go.Figure(go.Bar(
            x=ch_cvr["channel"].str.replace("_"," ").str.title(),
            y=ch_cvr["cvr_pct"],
            marker=dict(color=clrs2, line=dict(width=0)),
            text=ch_cvr["cvr_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            textfont=dict(color=C["text"], size=12),
            hovertemplate="<b>%{x}</b><br>CVR: %{y:.2f}%<extra></extra>",
            width=0.55,
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=300,
            showlegend=False,
            yaxis=dict(title="Avg CVR %", gridcolor="#1E2D45",
                       range=[0, ch_cvr["cvr_pct"].max()*1.3]),
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Funnel per plan
    section("Sample Size & Conversion Summary", "🔬")
    ab_disp = ab.copy()
    ab_disp["Conversion Rate"] = ab_disp["cvr_pct"].map("{:.2f}%".format)
    ab_disp["Visitors"]        = ab_disp["visitors"].map("{:,}".format)
    ab_disp["Converters"]      = ab_disp["converters"].map("{:,}".format)
    ab_disp["Plan"]            = ab_disp["plan"].str.title()
    ab_disp["Lift vs Worst"]   = (ab_disp["cvr_pct"] - worst_cvr).map("+{:.2f}pp".format)
    st.dataframe(ab_disp[["Plan","Visitors","Converters","Conversion Rate","Lift vs Worst"]],
                 use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
#  PAGE 5 — RFM SEGMENTATION
# ══════════════════════════════════════════════════════════════════════════
elif "RFM" in page:
    st.markdown('<div class="page-title">RFM Segmentation</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">User segmentation by Recency, Frequency & Monetary value — enabling targeted retention and growth strategies</div>', unsafe_allow_html=True)

    rfm = load_rfm_segments()
    total_rev = rfm["total_revenue"].sum()

    # ── Segment KPI cards ──
    seg_palette = {
        "Champions":  C["green"],
        "Loyal":      C["accent"],
        "Recent":     C["accent3"],
        "At Risk":    C["amber"],
        "Cant Lose":  C["red"],
        "Low Value":  C["muted"],
    }
    cols = st.columns(len(rfm), gap="small")
    for col, (_, row) in zip(cols, rfm.iterrows()):
        with col:
            color = seg_palette.get(row["segment"], C["accent"])
            kpi_card(row["segment"], f"{int(row['users']):,}",
                     f"${row['avg_ltv']:,.0f} avg LTV", color)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    ca, cb = st.columns(2, gap="medium")

    with ca:
        section("Revenue Contribution by Segment", "💰")
        rfm_sorted = rfm.sort_values("total_revenue")
        fig = go.Figure(go.Bar(
            y=rfm_sorted["segment"],
            x=rfm_sorted["total_revenue"],
            orientation="h",
            marker=dict(
                color=[seg_palette.get(s, C["accent"]) for s in rfm_sorted["segment"]],
                line=dict(width=0),
            ),
            text=rfm_sorted["total_revenue"].apply(lambda v: f"${v/1000:.1f}K"),
            textposition="inside",
            textfont=dict(color="white", size=11),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=300, showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with cb:
        section("Segment Size Distribution", "👥")
        fig2 = go.Figure(go.Pie(
            labels=rfm["segment"],
            values=rfm["users"],
            hole=0.55,
            marker=dict(
                colors=[seg_palette.get(s, C["accent"]) for s in rfm["segment"]],
                line=dict(color=C["bg"], width=3),
            ),
            textinfo="label+percent",
            textfont=dict(size=11, family="Inter"),
            hovertemplate="<b>%{label}</b><br>%{value:,} users<br>%{percent}<extra></extra>",
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=300, showlegend=False,
            annotations=[dict(text=f"<b>{int(rfm['users'].sum()):,}</b><br><span style='color:{C['muted']}'>Users</span>",
                              x=0.5, y=0.5, showarrow=False,
                              font=dict(size=13, color=C["text"]), xanchor="center")],
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Avg LTV comparison ──
    section("Average LTV by Segment", "💎")
    fig3 = go.Figure()
    rfm_ltv = rfm.sort_values("avg_ltv", ascending=False)
    fig3.add_trace(go.Bar(
        x=rfm_ltv["segment"],
        y=rfm_ltv["avg_ltv"],
        marker=dict(
            color=[seg_palette.get(s, C["accent"]) for s in rfm_ltv["segment"]],
            line=dict(width=0),
            opacity=0.88,
        ),
        text=rfm_ltv["avg_ltv"].apply(lambda v: f"${v:,.0f}"),
        textposition="outside",
        textfont=dict(color=C["text"], size=11),
        hovertemplate="<b>%{x}</b><br>Avg LTV: $%{y:,.2f}<extra></extra>",
        width=0.5,
    ))
    fig3.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False,
        yaxis=dict(title="Avg LTV ($)", gridcolor="#1E2D45",
                   range=[0, rfm_ltv["avg_ltv"].max()*1.25]),
    )
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Segment action table
    section("Recommended Actions by Segment", "🎯")
    actions = {
        "Champions":  "VIP programs, early access, referral campaigns",
        "Loyal":      "Loyalty rewards, upsell to higher tiers",
        "Recent":     "Onboarding nudges, second-purchase incentives",
        "At Risk":    "Win-back emails, personalised discounts",
        "Cant Lose":  "High-value re-engagement, personal outreach",
        "Low Value":  "Low-cost re-activation or sunset campaigns",
    }
    action_df = rfm.copy()
    action_df["Recommended Action"] = action_df["segment"].map(actions)
    action_df["Revenue Share"] = (action_df["total_revenue"] / total_rev * 100).round(1).astype(str) + "%"
    action_df = action_df.rename(columns={"segment":"Segment","users":"Users",
                                          "avg_ltv":"Avg LTV","total_revenue":"Total Revenue"})
    action_df["Avg LTV"]       = action_df["Avg LTV"].map("${:,.0f}".format)
    action_df["Total Revenue"] = action_df["Total Revenue"].map("${:,.0f}".format)
    st.dataframe(action_df[["Segment","Users","Avg LTV","Total Revenue","Revenue Share","Recommended Action"]],
                 use_container_width=True, hide_index=True)
