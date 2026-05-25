import streamlit as st
import app.engine as engine
import requests
import time

# Sayfa Ayarları (Bembeyaz ve Kurumsal Tema)
st.set_page_config(page_title="NEXUS AI CLOUD TERMINAL", layout="wide")

TELEGRAM_TOKEN = "8834309699:AAEjA7F4OmbIQHfd9769Lz640GweHPYoStI"
TELEGRAM_CHAT_ID = "1183450421"

def send_to_telegram(raw_analysis, ai_story):
    clean_name = raw_analysis["symbol"].replace("=X", "").replace("^", "").replace(".IS", "").replace("=F", "")
    if clean_name == "GC": clean_name = "ALTIN (XAUUSD)"
    elif clean_name == "SI": clean_name = "GÜMÜŞ (XAGUSD)"
    elif clean_name == "GSPC": clean_name = "S&P 500"
    
    tg_msg = f"🏛️ *NEXUS AI BULUT ALARMI (7/24)*\n\n" \
             f"🔥 *SETUP GRADE: {raw_analysis['grade']}* (YÜKSEK KALİTE)\n" \
             f"🎯 Enstrüman: {clean_name}\n" \
             f"📈 Yön: {raw_analysis['direction']}\n" \
             f"⚡ Güven: %{raw_analysis['confidence']}\n" \
             f"💎 R:R Oranı: 1:{raw_analysis['risk_reward']}\n" \
             f"🎯 Giriş Aralığı: {raw_analysis['entry_range']}\n" \
             f"🛑 Stop Loss: {raw_analysis['stop_loss']}\n" \
             f"🎯 Take Profit: {raw_analysis['take_profit']}\n\n" \
             f"📝 *Analiz:* {ai_story}"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": tg_msg, "parse_mode": "Markdown"})
    except: pass

# Üst Başlık
st.markdown("<h1 style='text-align: center; color: #1a1a1a; font-family: sans-serif;'>🏛️ NEXUS AI OTONOM CLOUD TERMINAL</h1>", unsafe_allow_html=True)
st.write("---")

PAZARLAR = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "ALTIN (XAUUSD)": "GC=F",
    "GÜMÜŞ (XAGUSD)": "SI=F",
    "S&P 500 (SPX500)": "^GSPC",
    "NASDAQ 100": "^IXIC",
    "BIST 100": "XU100.IS"
}

st.sidebar.header("🎛️ BULUT RADAR KONTROLÜ")
otomatik_mod = st.sidebar.toggle("🔄 7/24 Otomatik Taramayı Başlat", value=False)
tarama_araligi = st.sidebar.slider("⏱️ Tarama Sıklığı (Dakika)", min_value=5, max_value=60, value=15)

if otomatik_mod:
    st.success(f"🚀 Bulut Radarı Aktif! Sistem her {tarama_araligi} dakikada bir tüm piyasayı arka planda tarıyor...")
    status_box = st.empty()
    
    while otomatik_mod:
        for isim, sembol in PAZARLAR.items():
            status_box.info(f"🔍 Şu an taranıyor: {isim}...")
            try:
                data = engine.process_terminal_analysis(sembol, "USD")
                
                # Sadece yüksek kaliteli (A+ veya A) fırsatları Telegram'a fırlatır
                if not data["no_trade"] and data["grade"] in ["A+", "A"]:
                    ai_story = f"{isim} pazarında kurumsal Order Block ve FVG seviyeleri test edildi. Trend yönünde likidite yapısı onaylandı."
                    send_to_telegram(data, ai_story)
                    st.toast(f"🔥 {isim} Kurulumu Telegram'a fırlatıldı!", icon="💰")
            except:
                pass
        
        status_box.success(f"✅ Tüm piyasa tarandı. Bir sonraki tarama döngüsü bekleniyor...")
        time.sleep(tarama_araligi * 60)
else:
    st.info("👈 Soldaki menüden '7/24 Otomatik Taramayı Başlat' butonunu açarak bulut robotunu devreye alabilirsin.")