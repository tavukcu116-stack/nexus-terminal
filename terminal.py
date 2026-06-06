# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v63.1 - SHIELDED FRONTEND)
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import backend_core as core
from datetime import datetime, timezone

st.set_page_config(page_title="NEXUS DISPATCHER v63.1", layout="wide", page_icon="🏛️")

# 🏛️ AKILLI RAM DURUM MAKİNESİ (Sinyal Tekrar ve Spam Koruması)
if "last_signal_asset" not in st.session_state: st.session_state.last_signal_asset = None
if "last_signal_price" not in st.session_state: st.session_state.last_signal_price = 0.0
if "last_signal_time" not in st.session_state: st.session_state.last_signal_time = datetime.min.replace(tzinfo=timezone.utc)

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; font-weight: 600; }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if st.sidebar.button("♻️ Force Flush Cache & Scan", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Önbellek temizlendi, piyasa sıfırdan süzülüyor abi!")
    st.rerun()

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v63.1 — SMC DISPATCHER</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Pure 5-Conjunction Pure Retest Signal Terminal</p>", unsafe_allow_html=True)

# SADECE 3 ASİL MAJÖR PARİTE TARANIYOR ABI
WATCHLIST = ["EUR/USD", "GBP/USD", "XAU/USD"]

matrix_results = {}
for asset in WATCHLIST:
    node = core.extract_quant_smc_matrix(asset)
    if node is None: continue
    matrix_results[asset] = node
    
    # 🚨 AKTİF OPERASYONEL FİLTRE VE TELEGRAM ENJEKSİYON ALANI
    if node["bias"] != "WAIT":
        spread_pips, _, _ = core.get_live_spread_data(asset)
        now = datetime.now(timezone.utc)
        
        is_allowed = True
        
        # 1. Aktif Spread Filtresi (Makas 3.5 Pips'i geçerse sinyal otonom durdurulur abi)
        if spread_pips > 3.5:
            is_allowed = False
            matrix_results[asset]["action"] = f"BLOCKED: HIGH SPREAD ({spread_pips} Pips)"
            
        # 2. Aktif Gerçek Haber Filtresi
        if core.check_economic_news_barrier(asset):
            is_allowed = False
            matrix_results[asset]["action"] = "BLOCKED: FOREX FACTORY HIGH IMPACT NEWS TIMELINE"
            
        # 3. Aynı Sinyal Tekrar Koruması (Aynı yönde 60 dk içinde mükerrer mesaj engeli)
        if (st.session_state.last_signal_asset == asset and 
            abs(st.session_state.last_signal_price - node["price"]) < 0.0005 and 
            (now - st.session_state.last_signal_time).total_seconds() / 60 < 60):
            is_allowed = False
            matrix_results[asset]["action"] = "BLOCKED: MÜKERRER SPAM PROTECTION ACTIVE"

        # Her şey temiz ve kaliteliyse Telegram'a fırlat abi!
        if is_allowed and node["score"] >= 75:
            success = core.send_telegram_signal_report(
                asset=asset, bias=node["bias"], entry=node["price"],
                sl=node["sl_p"], tp1=node["tp1_p"], tp2=node["tp2_p"],
                score=node["score"], reasons=node["reasons"]
            )
            if success:
                st.session_state.last_signal_asset = asset
                st.session_state.last_signal_price = node["price"]
                st.session_state.last_signal_time = now

# Canlı Matrix Arayüz Tablosu
st.subheader("⚡ Live Conjunction Status Matrix")
screener_rows = []
for k, v in matrix_results.items():
    screener_rows.append({
        "Asset / Parite": k,
        "Live Price": f"{v['price']:.5f}" if "USD" in k else f"{v['price']:.2f}",
        "SMC Retest Vector": v["bias"],
        "Structure Profile": v["structure"],
        "Quant Score": f"{v['score']}/100" if v['score'] > 0 else "0/100",
        "Dinamik Math RR": f"1 : {v['rr']}" if v['rr'] > 0 else "0.0",
        "Dispatcher Core State": v["action"]
    })
if screener_rows: st.dataframe(pd.DataFrame(screener_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# Grafik Alanı
st.subheader("📈 Interactive Candlestick Matrix & Zone Triggers")
tabs = st.tabs(WATCHLIST)
for i, asset in enumerate(WATCHLIST):
    with tabs[i]:
        if asset not in matrix_results: st.warning(f"{asset} verisi bekliyor..."); continue
        node = matrix_results[asset]
        df = node["df"]
        
        col_left, col_right = st.columns([3, 1])
        with col_left:
            fig = go.Figure(data=[go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], rising_line_color='#10B981', falling_line_color='#EF4444')])
            
            zone_target = node["ob"] if node["ob"] else node["fvg"]
            if zone_target:
                z_color = "rgba(16, 185, 129, 0.15)" if "BULLISH" in zone_target["type"] else "rgba(239, 68, 68, 0.15)"
                fig.add_shape(type="rect", x0=df['datetime'].iloc[-25], x1=df['datetime'].iloc[-1], y0=zone_target["bottom"], y1=zone_target["top"], fillcolor=z_color, line_width=0)
            
            fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=400, margin=dict(l=5,r=5,t=5,b=5))
            st.plotly_chart(fig, use_container_width=True)
            
        with col_right:
            trend_tag = "BULLISH" if node["bias"] == "BUY" else "BEARISH" if node["bias"] == "SELL" else "WAIT"
            wr, pf = core.run_historical_backtest_matrix(df, trend_tag)
            
            st.metric("SMC Simulated Win Rate", f"%{wr}")
            st.metric("SMC Simulated Profit Factor", f"{pf}x")
            
            if node["bias"] != "WAIT":
                st.success(f"🎯 RETEST PASSED:\n\nVector: {node['bias']} @ {node['price']:.5f}\n\nSL: {node['sl_p']:.5f}\n\nTP1: {node['tp1_p']:.5f}\n\nTP2: {node['tp2_p']:.5f}")
            else:
                st.info(f"State: {node['action']}")
