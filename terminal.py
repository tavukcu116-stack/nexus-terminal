# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v56.4 - OPTIMIZED)
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import backend_core as core
import analytics_engine as analytics
from streamlit_autorefresh import st_autorefresh

# ─────────────────────────────────────────
# SAYFA AYARLARI
# ─────────────────────────────────────────
st.set_page_config(page_title="NEXUS QUANT v56.4", layout="wide", page_icon="🏛️")
st_autorefresh(interval=60_000, key="nexus_v56_refresh")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;600;700&display=swap');

.stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
h1,h2,h3,h4,label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; font-weight: 600; }
div[data-testid="stMetric"] {
    background: #131722 !important; border: 1px solid #2a2e39 !important;
    border-radius: 4px !important; padding: 10px !important;
}
.panel-box {
    background: #131722; border: 1px solid #2a2e39;
    border-radius: 4px; padding: 14px; margin-bottom: 10px;
}
.gate-passed  { color: #00ebc7; font-family: 'JetBrains Mono', monospace; font-weight: bold; }
.gate-failed  { color: #ff5a5f; font-family: 'JetBrains Mono', monospace; font-weight: bold; }
.status-wait  { color: #ffb74d; font-family: 'JetBrains Mono', monospace; font-weight: bold; }
.mono         { font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.7; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    if st.button("♻️ FORCE FLUSH (CACHE TEMİZLE)"):
        st.cache_data.clear()
        st.success("Ön bellek temizlendi!")
        st.rerun()

    render_asset = st.selectbox(
        "🏛️ PRODUCTION WATCHLIST",
        ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "NASDAQ", "US30", "BTC/USD", "ETH/USD"]
    )
    risk_pct = st.slider("İşlem Başı Risk (%R)", 0.25, 5.0, 1.0, 0.25)

prop_capital = st.number_input(
    "Account Balance Capital Size ($)",
    value=10_000.0, step=1_000.0,
    key=f"capital_{render_asset}"
)

ASSET_MAP = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY",
    "XAU/USD": "XAU/USD", "NASDAQ": "IXIC", "US30": "DJI",
    "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}
api_symbol = ASSET_MAP[render_asset]

# ─────────────────────────────────────────
# VERİ ÇEKME
# ─────────────────────────────────────────
node = core.extract_quant_smc_matrix(api_symbol)
spread_pips, live_bid, live_ask = core.get_live_spread_data(api_symbol)
news_blocked, news_reason = core.check_economic_news_timeline(api_symbol)

with core.get_db() as conn_read:
    cursor = conn_read.cursor()
    cursor.execute(
        "SELECT COALESCE(SUM(pnl), 0.0) FROM v54_ledger WHERE timestamp >= date('now', 'start of day')"
    )
    daily_pnl_sum = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(pnl), 0.0) FROM v54_ledger")
    total_pnl_sum = cursor.fetchone()[0]

    df_ledger = pd.read_sql_query("SELECT * FROM v54_ledger", conn_read)

corr_blocked, corr_reason = core.check_live_circuit_barriers(render_asset, prop_capital)
daily_circuit_lock = (daily_pnl_sum <= -(prop_capital * 0.03)) or (corr_blocked and "DAILY" in corr_reason)
total_circuit_lock = total_pnl_sum < -(prop_capital * 0.05)

# Lot hesaplama
if node and "price" in node and "sl_p" in node and node["sl_p"] != 0:
    final_lot = core.calculate_position_size(prop_capital, risk_pct, node["price"], node["sl_p"], render_asset)
else:
    final_lot = 0.01

# ─────────────────────────────────────────
# BAŞLIK
# ─────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:0;font-weight:700;'>🏛️ NEXUS QUANT v56.4 — AUTONOMOUS RUNTIME</h2>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='color:#848e9c;font-size:12px;margin-top:2px;margin-bottom:15px;'>"
    "Enterprise Quantitative Suite & Live Data Stream Matrix</p>",
    unsafe_allow_html=True
)

# ─────────────────────────────────────────
# ANA LAYOUT
# ─────────────────────────────────────────
col_chart, col_desk = st.columns([3, 1])

with col_chart:
    if node is None:
        st.markdown(f"""
        <div class='panel-box' style='border-left:4px solid #ffb74d;background:#1a1510;margin-bottom:15px;'>
            <span style='font-size:24px;font-weight:700;color:#ffb74d;'>{render_asset}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            SMC Status: <span style='color:#ffb74d;font-weight:bold;'>STANDBY (PİYASA KAPALI OLABİLİR)</span><br>
            <span class='mono' style='color:#b2b5be;'>
                Canlı borsa verisi bekleniyor veya seans dışı işlem yapılıyor.
                Veri aktığı an grafik otonom canlanacaktır.
            </span>
        </div>
        """, unsafe_allow_html=True)

        fig_ph = go.Figure()
        fig_ph.update_layout(
            template="plotly_dark", paper_bgcolor="#0c0d12", plot_bgcolor="#0c0d12", height=400,
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            annotations=[dict(
                text="Awaiting Operational Market Data Stream...",
                showarrow=False, font=dict(size=14, color="#848e9c")
            )]
        )
        st.plotly_chart(fig_ph, use_container_width=True)

    else:
        df = node["df"]

        # Pozisyon yönetimi & otonom motor
        core.manage_v54_positions(render_asset, df)
        core.manage_v55_autonomous_engine(
            render_asset, node, final_lot,
            daily_circuit_lock, total_circuit_lock,
            corr_blocked, news_blocked, prop_capital
        )

        bias_color = "#00ebc7" if node["bias"] == "BUY" else "#ff5a5f" if node["bias"] == "SELL" else "#ffb74d"

        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:24px;font-weight:700;color:#ffffff;'>{render_asset}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            Setup Grade: <span style='color:#00ebc7;font-weight:bold;'>{node['q_class']} ({node['score']}/100 pts)</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            Bias: <span style='color:{bias_color};font-weight:bold;'>{node['bias']}</span><br>
            <span class='mono' style='color:#b2b5be;'>
                Zone: {node['zone']} &nbsp;|&nbsp; Structure: {node['structure']}
                &nbsp;|&nbsp; SL: {node['sl_p']:.5f}
                &nbsp;|&nbsp; TP1: {node['tp1_p']:.5f}
                &nbsp;|&nbsp; TP2: {node['tp2_p']:.5f}
                &nbsp;|&nbsp; RR: {node['rr']:.1f}x
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Grafik ──────────────────────────────────────────────────────
        fig = go.Figure(data=[go.Candlestick(
            x=df["datetime"], open=df["open"], high=df["high"],
            low=df["low"],    close=df["close"], name="Price Action",
            increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
        )])

        # FVG kutusu
        if node["fvg"]:
            f_color = "rgba(16,185,129,0.15)" if "BULLISH" in node["fvg"]["type"] else "rgba(239,68,68,0.15)"
            fig.add_shape(
                type="rect",
                x0=df["datetime"].iloc[-20], x1=df["datetime"].iloc[-1],
                y0=node["fvg"]["bottom"],    y1=node["fvg"]["top"],
                line_width=0, fillcolor=f_color
            )
            fig.add_annotation(
                x=df["datetime"].iloc[-1], y=node["fvg"]["top"],
                text=node["fvg"]["type"], showarrow=False,
                font=dict(size=9, color="#10B981"), xanchor="left"
            )

        # OB kutusu
        if node["ob"]:
            ob_color = "rgba(59,130,246,0.2)" if "BULLISH" in node["ob"]["type"] else "rgba(245,158,11,0.2)"
            fig.add_shape(
                type="rect",
                x0=node["ob"]["time"], x1=df["datetime"].iloc[-1],
                y0=node["ob"]["bottom"], y1=node["ob"]["top"],
                line=dict(dash="dot", width=1, color="#3b82f6"), fillcolor=ob_color
            )

        # Yatay seviyeler
        fig.add_hline(y=node["pdh"], line_color="#9c27b0", line_dash="dash",   annotation_text="PDH", annotation_font_size=9)
        fig.add_hline(y=node["pdl"], line_color="#9c27b0", line_dash="dash",   annotation_text="PDL", annotation_font_size=9)
        fig.add_hline(y=node["eq"],  line_color="#00bcd4", line_dash="dot",    annotation_text="EQ",  annotation_font_size=9)

        if node["bias"] != "WAIT":
            fig.add_hline(y=node["sl_p"],  line_color="#ef5350", line_width=2, annotation_text="SL",  annotation_font_size=9)
            fig.add_hline(y=node["tp1_p"], line_color="#66bb6a", line_dash="dash", annotation_text="TP1", annotation_font_size=9)
            fig.add_hline(y=node["tp2_p"], line_color="#1b5e20", line_width=2, annotation_text="TP2", annotation_font_size=9)

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#0c0d12", plot_bgcolor="#0c0d12",
            xaxis_rangeslider_visible=False, height=450,
            margin=dict(l=5, r=5, t=5, b=5)
        )
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────
# SAĞ PANEL
# ─────────────────────────────────────────
with col_desk:
    st.markdown("#### 📋 Matrix Verification")

    kz_label  = "✅ OPEN"    if (node and node["kz"]) else "❌ CLOSED"
    kz_class  = "gate-passed" if (node and node["kz"]) else "gate-failed"
    spr_label = f"{spread_pips:.1f} Pips" if node else "1.2 Pips (MOCK)"
    ff_label  = "✅ CLEAR" if not news_blocked else "❌ LOCK"
    ff_class  = "gate-passed" if not news_blocked else "gate-failed"
    cr_label  = "✅ STABLE" if not corr_blocked else "❌ OVERLAP"
    cr_class  = "gate-passed" if not corr_blocked else "gate-failed"
    dl_class  = "gate-passed" if not daily_circuit_lock else "gate-failed"
    td_class  = "gate-passed" if not total_circuit_lock else "gate-failed"

    st.markdown(f"""
    <div class='panel-box mono'>
        Killzone: <span class='{kz_class}'>{kz_label}</span><br>
        FF Gate: <span class='{ff_class}'>{ff_label}</span><br>
        Spread: <span class='gate-passed'>{spr_label}</span><br>
        Correlation: <span class='{cr_class}'>{cr_label}</span><br>
        Daily Circuit: <span class='{dl_class}'>${daily_pnl_sum:.2f} / -3R</span><br>
        Max DD Cap: <span class='{td_class}'>${total_pnl_sum:.2f} / 5%</span>
    </div>
    """, unsafe_allow_html=True)

    if news_blocked: st.error(f"⚠️ {news_reason}")
    if corr_blocked: st.warning(f"🔗 {corr_reason}")

    allowed_risk = prop_capital * (risk_pct / 100.0)
    st.markdown(f"""
    <div class='panel-box mono' style='text-align:center;'>
        Risk Budget: <span style='color:#ff5a5f;'>${allowed_risk:.2f}</span><br>
        Lot Size: <span style='color:#00ebc7;font-weight:bold;'>{final_lot} Lot</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='panel-box mono' style='border:1px solid #00ebc7;background:#091a18;text-align:center;'>
        <span style='color:#00ebc7;font-weight:bold;'>🚀 AUTONOMOUS DISPATCH ACTIVE</span><br>
        <span style='color:#b2b5be;'>SMC Eşiği: 75+ Pts<br>Sistem otonom tarar ve emri mühürler.</span>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# PERFORMANS METRİKLERİ
# ─────────────────────────────────────────
st.markdown("---")
st.markdown("##### 📒 Live Performance Overview & Advanced Metrics")

metrics = analytics.calculate_advanced_risk_metrics(df_ledger, initial_capital=prop_capital)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Trades",  metrics["total_trades"])
    st.metric("Win Rate",      f"%{metrics['win_rate']}")
with m2:
    st.metric("Sharpe Ratio",  metrics["sharpe"])
    st.metric("Sortino Ratio", metrics["sortino"])
with m3:
    st.metric("Profit Factor", metrics["profit_factor"])
    st.metric("Calmar Ratio",  metrics["calmar"])
with m4:
    st.metric("Max DD ($)",    f"${metrics['max_drawdown_usd']}")
    st.metric("Streak W/L",    f"+{metrics['win_streak']} / -{metrics['loss_streak']}")

# ── Equity Curve ──────────────────────────────────────────────────────────
if len(metrics["equity_curve"]) > 2:
    eq_fig = go.Figure()
    eq_fig.add_trace(go.Scatter(
        y=metrics["equity_curve"],
        mode="lines", name="Equity",
        line=dict(color="#00ebc7", width=2),
        fill="tozeroy", fillcolor="rgba(0,235,199,0.05)"
    ))
    eq_fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0c0d12", plot_bgcolor="#131722",
        height=200, margin=dict(l=5, r=5, t=5, b=5),
        xaxis_title=None, yaxis_title="Equity ($)"
    )
    st.plotly_chart(eq_fig, use_container_width=True)

# ── Ledger ───────────────────────────────────────────────────────────────
st.subheader("📑 Internal Ledger Vault")
st.dataframe(df_ledger.iloc[::-1], use_container_width=True)

csv_data = analytics.export_ledger_to_audit_csv(df_ledger)
if csv_data and not csv_data.startswith("EXPORT_ERROR"):
    st.download_button(
        label="📥 DOWNLOAD VERIFIED AUDIT CSV",
        data=csv_data,
        file_name="nexus_verified_ledger.csv",
        mime="text/csv"
    )
elif csv_data.startswith("EXPORT_ERROR"):
    st.error(csv_data)
