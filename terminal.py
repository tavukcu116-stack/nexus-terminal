# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v64.0 - PURE OPERATIONS TERMINAL)
# ==========================================
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone
import backend_core as core
import analytics_engine as analytics
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NEXUS EXECUTIVE v64.0", layout="wide", page_icon="🏛️")

# ⏳ GLOBAL KOTA DOSTU REFRESH (60 Saniyede Bir Canlı Tarama)
st_autorefresh(interval=60000, key="nexus_v64_pure_refresh")

# RAM Bellek Üzerinde Sinyal Geçmişi ve Spam Koruma Hafızası abi
if "signal_history" not in st.session_state: st.session_state.signal_history = []
if "last_signal_asset" not in st.session_state: st.session_state.last_signal_asset = None
if "last_signal_price" not in st.session_state: st.session_state.last_signal_price = 0.0
if "last_signal_time" not in st.session_state: st.session_state.last_signal_time = datetime.min.replace(tzinfo=timezone.utc)

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; font-weight: 600; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 12px !important; }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    .status-online { color: #00ebc7; font-weight: bold; font-family: monospace; }
    .status-offline { color: #ff5a5f; font-weight: bold; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# ÖNBELLEK TEMİZLEME MEKANİZMASI (Zorunlu Kurtarıcı Buton)
if st.sidebar.button("♻️ Clear Cache & Re-Scan", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Önbellek temizlendi, sıfırdan taranıyor abi!")
    st.rerun()

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v64.0 — EXECUTIVE DESK</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Pure Retest Signal Suite & Conjunction Grid</p>", unsafe_allow_html=True)

# 🏛️ SADECE SENİN İSTEDİĞİN 3 AKTİF PARİTE MATRIXI
WATCHLIST = ["EUR/USD", "GBP/USD", "XAU/USD"]

# 🏛️ TELEGRAM DURUMU DENETLEYİCİSİ
tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
tg_chat = os.getenv("TELEGRAM_CHAT_ID")
tg_status_html = "<span class='status-online'>ONLINE (Ateşlemeye Hazır)</span>" if tg_token and tg_chat else "<span class='status-offline'>OFFLINE (Eksik Key)</span>"

st.sidebar.markdown(f"**Telegram Durumu:** {tg_status_html}", unsafe_allow_html=True)

matrix_results = {}
screener_rows = []

for asset in WATCHLIST:
    node = core.extract_quant_smc_matrix(asset)
    if node is None:
        screener_rows.append({"Aktif Pariteler": asset, "Trend Yönü": "WAIT", "SMC Skor": "0/100", "Son Sinyal": "WAIT", "Core Durumu": "NO DATA / LIMIT"})
        continue
        
    matrix_results[asset] = node
    now = datetime.now(timezone.utc)
    
    # Koruma bariyerleri sorgusu
    spread_pips, _, _ = core.get_live_spread_data(asset)
    is_allowed = True
    
    if spread_pips > 3.5 or core.check_economic_news_barrier(asset):
        is_allowed = False
        node["action"] = "BLOCKED BY SPREAD/NEWS GUARD"
        
    if (st.session_state.last_signal_asset == asset and 
        abs(st.session_state.last_signal_price - node["price"]) < 0.0005 and 
        (now - st.session_state.last_signal_time).total_seconds() / 60 < 60):
        is_allowed = False
        node["action"] = "BLOCKED: COOLDOWN ACTIVE"

    # Sinyal Tetik Kapısı ve Hafıza Enjeksiyonu abi
    if is_allowed and node["bias"] != "WAIT" and node["score"] >= 75:
        success = core.send_telegram_signal_report(
            asset=asset, bias=node["bias"], entry=node["price"],
            sl=node["sl_p"], tp1=node["tp1_p"], tp2=node["tp2_p"],
            score=node["score"], reasons=node["reasons"]
        )
        if success:
            st.session_state.last_signal_asset = asset
            st.session_state.last_signal_price = node["price"]
            st.session_state.last_signal_time = now
            
            # Analitik motoru beslemesi için RAM listesine ekleme yapıyoruz abi
            st.session_state.signal_history.append({
                "timestamp": now, "asset": asset, "bias": node["bias"],
                "price": node["price"], "rr": node["rr"], "score": node["score"]
            })

    # 3. TERMINAL.PY İÇİN SADECE SENİN İSTEDİĞİN METRİK SATIRI
    # Pariteler, Son Sinyal, SMC Skor, Trend Yönü (reasons içinde HTF trendi yazar abi)
    htf_trend_text = "WAIT"
    for r in node["reasons"]:
        if "HTF Trend" in r or "Confirmed" in r: htf_trend_text = r.split(":")[1].strip() if ":" in r else r
        
    screener_rows.append({
        "Aktif Pariteler": asset,
        "Trend Yönü": htf_trend_text,
        "SMC Skor": f"{node['score']}/100",
        "Son Sinyal": f"{node['bias']} @ {node['price']:.5f}" if node['bias'] != "WAIT" else "WAIT (PUSUDA)",
        "Core Durumu": node["action"]
    })

# Ekrana Esas Tabloyu Basıyoruz abi
st.subheader("⚡ Live Executive Conjunction Matrix")
st.dataframe(pd.DataFrame(screener_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# 🏛️ 2. ANALYTICS ENGINE BAĞLANTILI MATRİKS SHARDS
st.subheader("📊 Enterprise Performance Metrics (Pure Stats)")
stats = analytics.calculate_pure_metrics(st.session_state.signal_history)

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1: st.metric("Win Rate (Başarı Yüzdesi)", f"%{stats['win_rate']}")
with col_s2: st.metric("Ortalama RR Rasyosu", f"1 : {stats['avg_rr']}")
with col_s3: st.metric("Total Signals Generated", len(st.session_state.signal_history), "Hafızadaki Sinyaller")

# Son 30 Sinyal Bölmesi
st.markdown("#### 📜 Last 30 Signals Monitor")
if stats["last_30_signals"]:
    st.dataframe(pd.DataFrame(stats["last_30_signals"]), use_container_width=True, hide_index=True)
else:
    st.info("Sistem şu anda canlı borsa mumlarını süzüyor abi, kriterler eşleştiğinde ilk sinyal buraya mühürlenecek.")

# Aylık Performans Dağılım Bölmesi
st.markdown("#### 📅 Monthly Performance Journal")
if stats["monthly_performance"]:
    st.json(stats["monthly_performance"])
else:
    st.caption("Aylık veri birikimi bekleniyor abi.")
