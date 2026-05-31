# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v54.8 - FRONTEND RESILIENCE)
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import backend_core as core
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=60000, key="nexus_v54_production_frontend_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; font-weight: 600; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    .gate-passed { color: #00ebc7; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ff5a5f; font-family: monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v54.8 — SYSTEM RUNTIME</h2>", unsafe_allow_html=True)

render_asset = st.sidebar.selectbox("🏛️ WATCHLIST SCREENER", ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "NASDAQ", "US30", "BTC/USD", "ETH/USD"])

asset_map = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY", "XAU/USD": "XAU/USD",
    "NASDAQ": "IXIC", "US30": "DJI", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}

node = core.extract_quant_smc_matrix(asset_map[render_asset])
spread_pips, live_bid, live_ask = core.get_live_spread_data(asset_map[render_asset])

# 🛡️ VE KUSURSUZ ÖN YÜZ KALKANI: Veri hafta sonu boş dönerse çökme, kibarca durumu açıkla abi!
if node is None:
    st.markdown(f"""
    <div class='panel-box' style='border-left: 4px solid #ffb74d; background: #1a1510;'>
        <h4 style='color: #ffb74d !important; margin:0;'>📡 DATA STREAM SUSPENDED (PIYASA KAPALI)</h4>
        <p style='font-size:13px; margin-top:5px; color:#b2b5be;'>
            Seçilen varlık <b>{render_asset}</b> için hafta sonu canlı veri akışı kesilmiştir. 
            Sistem arka planda pusuya yatmış olup, Pazartesi günü borsa açılışıyla (Twelve Data Stream tetiklendiğinde) 
            SMC Matrix ve TradingView grafiğiniz otomatik olarak canlanacaktır abi.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Hafta sonu bile açık pozisyonları veritabanından görebilmek için alt paneli açık tutuyoruz abi
    st.markdown("##### 📒 Offline System Standby")
    conn = sqlite3.connect("nexus_v54_vault.db")
    df_ledger = pd.read_sql_query("SELECT * FROM v54_ledger WHERE status != 'OPEN'", conn)
    if not df_ledger.empty:
        st.info(f"Sistem çevrimdışı modda. Toplam Arşivlenmiş İşlem Sayısı: {len(df_ledger)}")
    conn.close()
else:
    # Eğer veri varsa (Hafta içi veya Kripto paritelerinde) normal akış tıkır tıkır çalışır abi
    df = node["df"]
    core.manage_v54_positions(render_asset, df)
    news_blocked, news_reason = core.check_economic_news_timeline(asset_map[render_asset])
    
    conn = sqlite3.connect("nexus_v54_vault.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger WHERE timestamp >= date('now')")
    daily_pnl_sum = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger")
    total_pnl_sum = cursor.fetchone()[0] or 0.0
    
    prop_capital = st.number_input("Account Balance Capital Size ($)", value=10000.0, step=1000.0, key=f"cap_v54_{render_asset}")
    daily_circuit_lock = daily_pnl_sum < -(prop_capital * 0.03)
    total_circuit_lock = total_pnl_sum < -(prop_capital * 0.05)

    col_chart, col_desk = st.columns([3, 1])
    with col_chart:
        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:11px; color:#848e9c; font-family:monospace;'>NEXUS ONLINE MATRIX:</span><br>
            <span style='font-size:24px; font-weight:700;'>{render_asset}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
            Grade: <span style='color:#00ebc7; font-weight:bold;'>{node['q_class']} ({node['score']}/100)</span>
        </div>
        """, unsafe_allow_html=True)
        
        fig = go.Figure(go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close']))
        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        st.markdown("#### 📋 Core Verification")
        st.markdown(f"<div class='panel-box' style='font-size:11px;'>Spread: {spread_pips} Pips<br>Daily PnL: ${daily_pnl_sum:.2f}</div>", unsafe_allow_html=True)
    conn.close()
