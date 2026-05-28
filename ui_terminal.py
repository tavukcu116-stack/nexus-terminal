# ui_terminal.py
import streamlit as st
import redis
import json
import time
import plotly.graph_objects as go

# Sayfa Genişlik ve Başlık Yapılandırması
st.set_page_config(page_title="NEXUS ENTERPRISE MONITOR", layout="wide")
st.title("🏛️ NEXUS QUANT - INDUSTRIAL DECOUPLED UI")
st.markdown("<p style='color:#6C727F;'>Redis Cache Layer State Watchdog Framework</p>", unsafe_allow_html=True)

# Senkron Redis Bağlantısı (UI, motorun hızını asla kesemez)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

try:
    # Ana motorun Redis'e yazdığı en güncel durumu çek
    raw_state = r.get("nexus_live_state")
    
    if raw_state:
        state = json.loads(raw_state)
        
        # Grid Bilgi Kartları (Metrics Ribbon)
        m1, m2, m3 = st.columns(3)
        m1.metric("Live Engine Price", f"${state['price']:.2f}")
        m2.metric("Active Killzone Block", state['active_session'])
        m3.metric("True MSS Bullish State", "ACTIVE" if state['mss_bullish'] else "STANDBY")
        
        # Basit ve Hızlı Hız Göstergesi Grafiği
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = state['price'],
            title = {'text': "Binance Futures Feed Price"},
            gauge = {'axis': {'range': [state['price']-150, state['price']+150]}}
        ))
        fig.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption(f"Backend Core Last Heartbeat UTC: {state['timestamp']}")
    else:
        st.warning("Waiting for Backend Core Engine to publish event states to Redis cache...")
        
except redis.exceptions.ConnectionError:
    st.error("🚨 CRITICAL ERROR: UI Terminal disconnected from Redis Cache Layer. Ensure Redis server is active.")

# Saniyede 1 Kez Ekranı Yenile (UI Thread'i, Veri Akışını Etkilemez)
time.sleep(1.0)
st.rerun()
