# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v65.1 - IMPORTS FIXED)
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import backend_core as core
import analytics_engine as analytics
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
import os  # 🏛️ İŞTE EKSİK OLAN VE HATAYI ÇÖZEN ASİL KÜTÜPHANE ABİ!

st.set_page_config(page_title="NEXUS EXECUTIVE v65.1", layout="wide", page_icon="🏛️")

# Canlı Otomatik Tarama (60 Saniye)
st_autorefresh(interval=60000, key="nexus_v65_final_refresh")

if "signal_history" not in st.session_state: st.session_state.signal_history = []
if "last_signal_asset" not in st.session_state: st.session_state.last_signal_asset = None
if "last_signal_price" not in st.session_state: st.session_state.last_signal_price = 0.0
if "last_signal_time" not in st.session_state: st.session_state.last_signal_time = datetime.min.replace(tzinfo=timezone.utc)

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; font-weight: 600; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 12px !important; }
    .status-online { color: #00ebc7; font-weight: bold; font-family: monospace; }
    .status-offline { color: #ff5a5f; font-weight: bold; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

if st.sidebar.button("♻️ Clear Cache & Re-Scan", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Önbellek sıfırlandı abi!")
    st.rerun()

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v65.1 — EXECUTIVE DESK</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Fault-Tolerant Pure Retest Signal Suite</p>", unsafe_allow_html=True)

WATCHLIST = ["EUR/USD", "GBP/USD", "XAU/USD"]

tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
tg_chat = os.getenv("TELEGRAM_CHAT_ID")
tg_status_html = "<span class='status-online'>ONLINE</span>" if tg_token and tg_chat else "<span class='status-offline'>OFFLINE</span>"
st.sidebar.markdown(f"**Telegram Status:** {tg_status_html}", unsafe_allow_html=True)

screener_rows = []

for asset in WATCHLIST:
    try:
        node = core.extract_quant_smc_matrix(asset)
        
        if node is None:
            screener_rows.append({"Aktif Pariteler": asset, "Trend Yönü": "WAIT", "SMC Skor": "0/100", "Son Sinyal": "WAIT", "Core Durumu": "DATA FETCH LIMIT / NULL"})
            continue
            
        now = datetime.now(timezone.utc)
        spread_pips, _, _ = core.get_live_spread_data(asset)
        
        is_allowed = True
        if spread_pips > 3.5 or core.check_economic_news_barrier(asset):
            is_allowed = False
            node["action"] = "BLOCKED BY SPREAD/NEWS"
            
        if (st.session_state.last_signal_asset == asset and 
            abs(st.session_state.last_signal_price - node["price"]) < 0.0005 and 
            (now - st.session_state.last_signal_time).total_seconds() / 60 < 60):
            is_allowed = False
            node["action"] = "COOLDOWN LOCK"

        if is_allowed and node["bias"] != "WAIT" and node["score"] >= 75:
            success = core.send_telegram_signal_report(
                asset=asset, bias=node["bias"], entry=node["price"],
                sl=node["sl_p"], tp1=node["tp1_p"], tp2=node["tp2_p"],
                score=node["score"], reasons=node.get("reasons", [])
            )
            if success:
                st.session_state.last_signal_asset = asset
                st.session_state.last_signal_price = node["price"]
                st.session_state.last_signal_time = now
                st.session_state.signal_history.append({
                    "timestamp": now, "asset": asset, "bias": node["bias"],
                    "price": node["price"], "rr": node["rr"], "score": node["score"]
                })

        htf_trend_text = "WAIT"
        for r in node.get("reasons", []):
            if "HTF Trend" in r: htf_trend_text = r.split(":")[1].strip() if ":" in r else r

        screener_rows.append({
            "Aktif Pariteler": asset,
            "Trend Yönü": htf_trend_text,
            "SMC Skor": f"{node['score']}/100",
            "Son Sinyal": f"{node['bias']} @ {node['price']:.5f}" if node['bias'] != "WAIT" else "WAIT (PUSU)",
            "Core Durumu": node["action"]
        })
    except Exception as e:
        screener_rows.append({"Aktif Pariteler": asset, "Trend Yönü": "ERROR", "SMC Skor": "0/100", "Son Sinyal": "ERROR", "Core Durumu": f"RUNTIME CAP: {str(e)}"})

# Tablo Çıktısı
if screener_rows:
    st.dataframe(pd.DataFrame(screener_rows), use_container_width=True, hide_index=True)

st.markdown("---")

st.subheader("📊 Enterprise Performance Metrics (Pure Stats)")
stats = analytics.calculate_pure_metrics(st.session_state.signal_history)

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1: st.metric("Win Rate", f"%{stats['win_rate']}")
with col_s2: st.metric("Ortalama RR", f"1 : {stats['avg_rr']}")
with col_s3: st.metric("Total Signals", len(st.session_state.signal_history))

st.markdown("#### 📜 Last 30 Signals Monitor")
if stats["last_30_signals"]:
    st.dataframe(pd.DataFrame(stats["last_30_signals"]), use_container_width=True, hide_index=True)
else:
    st.info("Piyasa taranıyor abi, kriterler tam eşleştiğinde ilk sinyal buraya düşecek.")
