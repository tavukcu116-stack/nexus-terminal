# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v58.0 - MASTER FRONTEND)
# ==========================================
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timezone
import os

# Çekirdek motor fonksiyonlarını güvenli bağlama
import backend_core as core

st.set_page_config(page_title="NEXUS QUANT v58.0 - PRODUCTION TERMINAL", layout="wide", page_icon="🏛️")

# CSS Kurumsal Arayüz Zırhı
st.markdown("""
    <style>
    .reportview-container { background: #0A0E17; color: #E2E8F0; }
    .stMetric { background: #111827; border: 1px solid #1F2937; padding: 15px; border-radius: 10px; }
    div[data-testid="stExpander"] { background: #111827; border: 1px solid #1F2937; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# 🏛️ SIDEBAR & AKILLI CACHE TEMİZLEME MEKANİZMASI
with st.sidebar:
    st.title("🏛️ NEXUS CORE v58.0")
    st.caption("High-Frequency Quantitative Execution Engine")
    st.markdown("---")
    
    # 1. Önbellek Temizleme ve Yeniden Başlatma Kalkanı
    if st.button("♻️ Clear Cache & Refresh", use_container_width=True):
        st.cache_data.clear()
        st.success("Önbellek sıfırlandı. Veri akışı yenileniyor abi!")
        st.rerun()
        
    st.markdown("---")
    capital = st.number_input("Sermaye / Capital ($)", min_value=100.0, value=10000.0, step=500.0)
    risk_pct = st.slider("İşlem Başına Risk (%R)", min_value=0.25, max_value=3.0, value=1.0, step=0.25)
    
    st.markdown("---")
    st.info(f"UTC Zamanı: {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

# 🏛️ SADECE SENİN İSTEDİĞİN PARİTE MATRİSİ (BAŞKA HİÇBİR ŞEY YOK)
WATCHLIST = ["EUR/USD", "GBP/USD", "XAU/USD"]

# Kurumsal Veritabanı Okuma Fonksiyonları
def get_ledger_data():
    try:
        conn = sqlite3.connect(core.DB_FILE)
        df = pd.read_sql_query("SELECT * FROM v54_ledger ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def get_logs_data():
    try:
        conn = sqlite3.connect(core.DB_FILE)
        df = pd.read_sql_query("SELECT * FROM nexus_logs ORDER BY id DESC LIMIT 30", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

# Üst Bilgi Paneli (Live Exposure & Drawdown Dashboard)
ledger_df = get_ledger_data()
open_trades = ledger_df[ledger_df["status"] == "OPEN"] if not ledger_df.empty else pd.DataFrame()

total_exposure_usd = open_trades["initial_risk_usd"].sum() if not open_trades.empty else 0.0
exposure_pct = (total_exposure_usd / capital) * 100

st.title("🏛️ NEXUS QUANT - INDUSTRIAL SMC MONITOR")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Total Active Exposure", f"${total_exposure_usd:.2f}", f"{exposure_pct:.2f}% / Max 3%")
with col_m2:
    st.metric("Active Positions", f"{len(open_trades)} Lots", "Global Limit: 3")
with col_m3:
    session_tag, kz_active = core.get_live_market_session_tag()
    st.metric("Current Session", session_tag, "Killzone Active" if kz_active else "Standby Mode")
with col_m4:
    # Günlük Drawdown Denetimi Görselleştirmesi
    try:
        conn = sqlite3.connect(core.DB_FILE)
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM v54_ledger WHERE timestamp >= date('now', 'start of day')")
        day_pnl = c.fetchone()[0] or 0.0
        conn.close()
    except: day_pnl = 0.0
    st.metric("Daily Realized PnL", f"${day_pnl:.2f}", f"Circuit Break: -${(capital*0.03):.2f}")

st.markdown("---")

# 🏛️ MATRİS TARAYICI VE EMİR TETİKLEYİCİ ÇEKİRDEK ÇEVRİM
matrix_results = {}

for asset in WATCHLIST:
    node = core.extract_quant_smc_matrix(asset)
    if node is None:
        matrix_results[asset] = {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "API LIMIT / NO DATA"}
        continue
        
    matrix_results[asset] = node
    
    # Haber, Korelasyon ve Koruma Kalkanı Sorguları
    news_blocked, news_reason = core.check_economic_news_timeline(asset)
    barrier_blocked, barrier_reason = core.check_live_circuit_barriers(asset, capital)
    
    # Lot Hesaplama Motoru Kalibrasyonu
    final_lot = core.calculate_position_size(capital, risk_pct, node["price"], node["sl_p"], asset)
    
    # Otonom Pozisyon ve Emir Yönetim Motorunun Tetiklenmesi
    core.manage_v54_positions(asset, node["df"])
    core.manage_v55_autonomous_engine(asset, node, final_lot, False, False, False, news_blocked, capital)

# Ekrana Canlı Tarayıcı Tablosunu Basma Aşaması
st.subheader("⚡ Live Market Structure Screener Matrix")
screener_rows = []
for k, v in matrix_results.items():
    screener_rows.append({
        "Asset / Parite": k,
        "Live Price": f"{v.get('price', 0.0):.5f}" if "USD" in k else f"{v.get('price', 0.0):.2f}",
        "SMC Bias": v.get("bias"),
        "Structure Status": v.get("structure"),
        "Zone (Premium/Discount)": v.get("zone"),
        "Quant Score": f"{v.get('score', 0)}/100",
        "Quality Class": v.get("q_class"),
        "Dynamic Math RR": f"1 : {v.get('rr', 0.0)}",
        "Execution Stage": v.get("action")
    })
st.dataframe(pd.DataFrame(screener_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# 🏛️ SİNYAL BEYNİYLE %100 UYUMLU DETAYLI GÖRSELLEŞTİRME VE HISTORICAL BACKTEST ALANI
st.subheader("📊 Structural Advanced Interactive Charts & Quantum Backtest")
tabs = st.tabs(WATCHLIST)

for i, asset in enumerate(WATCHLIST):
    with tabs[i]:
        node = matrix_results[asset]
        if node["bias"] == "WAIT" and node.get("price") is None:
            st.warning(f"{asset} için veri sağlayıcı fallback modunda veya limit dolu abi. Sidebar'dan cache temizlemeyi dene.")
            continue
            
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            # Plotly Canlı Grafik Katmanı Enjeksiyonu
            df = node["df"]
            fig = go.Figure(data=[go.Candlestick(
                x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                name='Candlesticks', rising_line_color='#10B981', falling_line_color='#EF4444'
            )])
            
            # Kurumsal Seviye OB ve FVG Alanlarını Grafiğe Mühürleme
            if node.get("ob"):
                fig.add_shape(type="rect", x0=df['datetime'].iloc[-15], x1=df['datetime'].iloc[-1],
                              y0=node["ob"]["bottom"], y1=node["ob"]["top"],
                              fillcolor="rgba(239, 68, 68, 0.15)" if "BEARISH" in node["ob"]["type"] else "rgba(16, 185, 129, 0.15)",
                              line=dict(width=0))
            if node.get("fvg"):
                fig.add_shape(type="rect", x0=node["fvg"]["time"], x1=df['datetime'].iloc[-1],
                              y0=node["fvg"]["bottom"], y1=node["fvg"]["top"],
                              fillcolor="rgba(245, 158, 11, 0.12)", line=dict(width=1, dash="dot", color="#F59E0B"))
            
            fig.update_layout(title=f"{asset} 15M Structural Matrix Chart", theme="seaborn", height=450,
                              xaxis_rangeslider_visible=False, paper_bgcolor="#111827", plot_bgcolor="#111827")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_right:
            st.markdown(f"#### 🏛️ {asset} Historical SMC Backtest Statistics")
            # Çekirdekle %100 Senkronize SMC Backtest Motoru Sonuçları
            wr, pf, _, exp = core.run_historical_backtest_matrix(df)
            
            st.metric("SMC Win Rate (Geriye Dönük)", f"{wr}%")
            st.metric("SMC Profit Factor", f"{pf}x")
            st.metric("Expectancy Per Trade", f"${exp:.2f}")
            
            if node["bias"] != "WAIT":
                st.success(f"🎯 ACTIVE SIGNAL: {node['bias']} @ {node['price']:.5f}\n\nTarget SL: {node['sl_p']:.5f}\n\nTarget TP1: {node['tp1_p']:.5f}\n\nTarget TP2: {node['tp2_p']:.5f}")

st.markdown("---")

# Ledger Defteri ve Siber Denetim Günlüğü Tabloları
col_b1, col_b2 = st.columns([2, 1])
with col_b1:
    st.subheader("📜 Live Decentralized Position Ledger")
    if not ledger_df.empty:
        st.dataframe(ledger_df, use_container_width=True, hide_index=True)
    else:
        st.info("Defterde henüz kayıtlı pozisyon yok abi.")
with col_b2:
    st.subheader("🕵️‍♂️ Cryptographic Audit Logs")
    logs_df = get_logs_data()
    if not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("Sistem temiz, hata logu yok abi.")
