# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v56.3 - FINAL FIXED KEYWORDS)
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import sqlite3
from datetime import datetime
import backend_core as core
import analytics_engine as analytics
from streamlit_autorefresh import st_autorefresh

# 1. 🏛️ STREAMLIT PAGE CONFIG & THEME LOCKUP
st.set_page_config(page_title="NEXUS QUANT v56.3", layout="wide", page_icon="🏛️")

# ⏳ GLOBAL FRONTEND AUTO-REFRESH (60 Saniye Akıllı Kota Kalkanı)
st_autorefresh(interval=60000, key="nexus_v56_clean_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; font-weight: 600; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 10px !important; }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    .gate-passed { color: #00ebc7; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ff5a5f; font-family: monospace; font-weight: bold; }
    .status-wait { color: #ffb74d; font-family: monospace; font-weight: bold; }
    .status-online { color: #10B981; font-weight: bold; }
    .status-offline { color: #EF4444; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ⚡ CACHE TEMİZLEME MOTORU (Zorunlu Kurtarıcı Buton)
if st.sidebar.button("♻️ FORCE FLUSH (CACHE TEMİZLE)"):
    st.cache_data.clear()
    st.sidebar.success("Ön bellek temizlendi abi!")
    st.rerun()

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v56.3 — AUTONOMOUS RUNTIME</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Enterprise Quantitative Suite & Live Data Stream Matrix</p>", unsafe_allow_html=True)

# ==========================================
# 💱 8 PARİTELİK ORİJİNAL KORUNAN WATCHLIST SCREENER
# ==========================================
render_asset = st.sidebar.selectbox(
    "🏛️ PRODUCTION WATCHLIST SCREENER", 
    ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "NASDAQ", "US30", "BTC/USD", "ETH/USD"]
)

asset_map = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY", "XAU/USD": "XAU/USD",
    "NASDAQ": "IXIC", "US30": "DJI", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}

# Sunucu Sermaye/Kasa Ayarları
prop_capital = st.number_input("Account Balance Capital Size ($)", value=10000.0, step=1000.0, key=f"capital_v56_{render_asset}")
risk_pct = st.sidebar.slider("İşlem Başı Risk (%R)", 0.25, 5.0, 1.0, 0.25)

# Veri Akış Sorguları
node = core.extract_quant_smc_matrix(asset_map[render_asset])
spread_pips, live_bid, live_ask = core.get_live_spread_data(asset_map[render_asset])
news_blocked, news_reason = core.check_economic_news_timeline(asset_map[render_asset])

# Veritabanı ve Risk Bağlantıları
conn = sqlite3.connect("nexus_v54_vault.db")
cursor = conn.cursor()
cursor.execute("SELECT SUM(pnl) FROM v54_ledger WHERE timestamp >= date('now')")
daily_pnl_sum = cursor.fetchone()[0] or 0.0
cursor.execute("SELECT SUM(pnl) FROM v54_ledger")
total_pnl_sum = cursor.fetchone()[0] or 0.0

# Gerçek Bariyer Denetimleri
corr_blocked, corr_reason = core.check_live_circuit_barriers(render_asset, prop_capital)
daily_circuit_lock = daily_pnl_sum <= -(prop_capital * 0.03) or (corr_blocked and "DAILY" in corr_reason)
total_circuit_lock = total_pnl_sum < -(prop_capital * 0.05)

# 🛠️ ATTRIBUTE ERROR ÇÖZÜMÜ: Argümanlar keyword eşleşmesiyle mühürlendi abi!
if node:
    final_lot = core.calculate_position_size(
        capital=prop_capital,
        risk_pct=risk_pct,
        price=node["price"],
        sl_p=node["sl_p"],
        asset=render_asset
    )
else:
    final_lot = 0.01

# ANA EKRAN DÜZENİ (ÇİFT SÜTUN)
col_chart, col_desk = st.columns([3, 1])

with col_chart:
    if node is None:
        st.markdown(f"""
        <div class='panel-box' style='border-left: 4px solid #ffb74d; background: #1a1510; margin-bottom:15px;'>
            <span style='font-size:24px; font-weight:700; color:#ffb74d;'>{render_asset}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
            SMC Status: <span style='color:#ffb74d; font-weight:bold;'>STANDBY (PİYASA KAPALI OLABİLİR)</span><br>
            <span style='font-size:12px; font-family:monospace; color:#b2b5be;'>
                Canlı borsa verisi bekleniyor veya seans dışı işlem yapılıyor abi. Veri aktığı an grafik otonom canlanacaktır.
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        fig_placeholder = go.Figure()
        fig_placeholder.update_layout(
            template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', height=400,
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            annotations=[dict(text="Awaiting Operational Market Data Stream...", showarrow=False, font=dict(size=14, color="#848e9c"))]
        )
        st.plotly_chart(fig_placeholder, use_container_width=True)
    else:
        df = node["df"]
        core.manage_v54_positions(render_asset, df)
        
        # Otonom tetiği arkada çalıştır abi
        core.manage_v55_autonomous_engine(render_asset, node, final_lot, daily_circuit_lock, total_circuit_lock, corr_blocked, news_blocked, prop_capital)

        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:11px; color:#848e9c; font-family:monospace;'>NEXUS HIGH-FREQUENCY AUTOMATED CORE MATRIX:</span><br>
            <span style='font-size:24px; font-weight:700; color:#ffffff;'>{render_asset}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
            Setup Grade: <span style='color:#00ebc7; font-weight:bold;'>{node['q_class']} ({node['score']}/100 pts)</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Bias Mode: <span style='color:#2962ff; font-weight:bold;'>{node['bias']}</span><br>
            <span style='font-size:12px; font-family:monospace; color:#b2b5be;'>
                SMC Zone: {node['zone']} | Structure: {node['structure']} | SL: {node['sl_p']:.5f} | TP1 (1.5x): {node['tp1_p']:.5f} | TP2 (3.0x Final): {node['tp2_p']:.5f} | Math RR: {node['rr']:.1f}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        fig = go.Figure(data=[go.Candlestick(
            x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price Action"
        )])

        if node["fvg"]:
            f_color = "rgba(16, 185, 129, 0.15)" if "BULLISH" in node["fvg"]["type"] else "rgba(239, 68, 68, 0.15)"
            fig.add_shape(type="rect", x0=df['datetime'].iloc[-20], y0=node["fvg"]["bottom"], x1=df['datetime'].iloc[-1], y1=node["fvg"]["top"], line_width=0, fillcolor=f_color)

        if node["ob"]:
            ob_color = "rgba(59, 130, 246, 0.2)" if "BULLISH" in node["ob"]["type"] else "rgba(245, 158, 11, 0.2)"
            fig.add_shape(type="rect", x0=node["ob"]["time"], y0=node["ob"]["bottom"], x1=df['datetime'].iloc[-1], y1=node["ob"]["top"], line=dict(dash="dot", width=1, color="blue"), fillcolor=ob_color)

        fig.add_hline(y=node["pdh"], line_color="purple", line_dash="dash", annotation_text="PDH")
        fig.add_hline(y=node["pdl"], line_color="purple", line_dash="dash", annotation_text="PDL")
        fig.add_hline(y=node["eq"], line_color="cyan", line_dash="dot", annotation_text="Equilibrium")

        if node["bias"] != "WAIT":
            fig.add_hline(y=node["sl_p"], line_color="red", line_width=2, annotation_text="STRUCTURAL SL")
            fig.add_hline(y=node["tp1_p"], line_color="green", line_dash="dash", annotation_text="TARGET TP1")
            fig.add_hline(y=node["tp2_p"], line_color="darkgreen", line_width=2, annotation_text="TARGET TP2")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=450, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

with col_desk:
    st.markdown("#### 📋 Matrix Verification")
    kz_status = "✅ OPEN" if (node and node["kz"]) else "❌ CLOSED (OFFLINE)" if node is None else "❌ CLOSED"
    spr_val = f"{spread_pips:.1f} Pips" if node else "1.2 Pips (MOCK)"
    
    st.markdown(f"""
    <div class='panel-box' style='font-family:monospace; font-size:11px; line-height:1.7;'>
        Institutional Killzone: <span class='{"gate-passed" if (node and node["kz"]) else "status-wait" if node is None else "gate-failed"}'>{kz_status}</span><br>
        Forex Factory Gate: <span class='{"gate-passed" if not news_blocked else "gate-failed"}'>{"✅ CLEAR" if not news_blocked else "❌ LOCK"}</span><br>
        Live Quote Spread: <span class='gate-passed'>{spr_val}</span><br>
        Correlation Matrix: <span class='{"gate-passed" if not corr_blocked else "gate-failed"}'>{"✅ STABLE" if not corr_blocked else "❌ OVERLAP"}</span><br>
        Daily Loss Circuit: <span class='{"gate-passed" if not daily_circuit_lock else "gate-failed"}'>${daily_pnl_sum:.2f} / -3R</span><br>
        Maximum Drawdown Cap: <span class='{"gate-passed" if not total_circuit_lock else "gate-failed"}'>${total_pnl_sum:.2f} / 5%</span>
    </div>
    """, unsafe_allow_html=True)
    
    if news_blocked: st.error(f"⚠️ {news_reason}")
    if corr_blocked: st.warning(f"🔗 {corr_reason}")

    allowed_risk_usd = prop_capital * (risk_pct / 100.0)
    st.markdown(f"""
    <div class='panel-box' style='font-family: monospace; font-size:11px; text-align:center;'>
        Allocated Loss Budget: <span style='color:#ff5a5f;'>${allowed_risk_usd:.2f}</span><br>
        Calculated Core Size: <span style='color:#00ebc7; font-weight:bold;'>{final_lot} Lot</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class='panel-box' style='border: 1px solid #00ebc7; background: #091a18; text-align:center;'>
        <span style='color:#00ebc7; font-size:11px; font-weight:bold; font-family:monospace;'>🚀 AUTONOMOUS DISPATCH ACTIVE</span><br>
        <span style='color:#b2b5be; font-size:10px; font-family:monospace;'>SMC Score Barajı: 75+ Pts<br>Sistem piyasayı otonom tarar ve yüksek ihtimalli emri kendi mühürler.</span>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 📒 PERFORMANCE & LEDGER VAULT
# ==========================================
st.markdown("---")
st.markdown("##### 📒 Live Performance Overview & Advanced Metrics")
df_ledger = pd.read_sql_query("SELECT * FROM v54_ledger", conn)
metrics = analytics.calculate_advanced_risk_metrics(df_ledger, initial_capital=prop_capital)

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric("Total Trades Closed", metrics["total_trades"])
    st.metric("Win Rate", f"%{metrics['win_rate']}")
with m_col2:
    st.metric("Sharpe Ratio", metrics["sharpe"])
    st.metric("Sortino Ratio", metrics["sortino"])
with m_col3:
    st.metric("Profit Factor", metrics["profit_factor"])
    st.metric("Calmar Ratio", metrics["calmar"])
with m_col4:
    st.metric("Max Drawdown ($)", f"${metrics['max_drawdown_usd']}")
    st.metric("Win/Loss Streak", f"+{metrics['win_streak']} / -{metrics['loss_streak']}")

st.subheader("📑 Internal Ledger Vault Data Log")
st.dataframe(df_ledger.iloc[::-1], use_container_width=True)

csv_data = analytics.export_ledger_to_audit_csv(df_ledger)
if csv_data:
    st.download_button(label="📥 DOWNLOAD VERIFIED AUDIT CSV", data=csv_data, file_name="nexus_verified_ledger.csv", mime="text/csv")

conn.close()
