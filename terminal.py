import streamlit as str_plat
import time
import requests

# Sayfa Genişlik Ayarı
str_plat.set_page_config(page_title="NEXUS AI AUTOMATED TERMINAL", layout="wide")

str_plat.title("🏛️ NEXUS AI INSTITUTIONAL MASTER CORE")
str_plat.subheader("Otonom Bulut Terminali - 7/24 Canlı Devriye")

# Sol Menü Ayarları
with str_plat.sidebar:
    str_plat.header("⚙️ Terminal Kontrol Paneli")
    otonom_tarama = str_plat.toggle("🔄 7/24 Otomatik Taramayı Başlat", value=True)
    tarama_araligi = str_plat.number_input("Tarama Sıklığı (Dakika)", min_value=5, max_value=60, value=15)

# Telegram Gönderim Fonksiyonu (Senin Şablonun)
def telegram_firlat(enstruman, yon, giris_1, giris_2, sl, tp):
    token = "7334751187:AAFb_J0O69iBIsZ8_E1N_ZtZpCg2xV9Wd9A"  # Senin Bot Tokenin
    chat_id = "1183450421"  # Senin Chat ID numaran
    
    mesaj = f"""━━━━━━━━━━━━━━
🏛️ NEXUS AI BULUT ALARMI ━━━━━━━━━━━━━━
🔥 SETUP GRADE: A+
🏦 Institutional Score: 9.4/10

🎯 Enstrüman: {enstruman}
📈 Yön: {yon} (Satış Yönlü ve Likidite Onaylı)
⚡ Güven: %92
💎 R:R Oranı: 1:3.0

🌍 Session: NY Open / Overlap
📊 Market Rejimi: Trending (Displacement)
📊 Trend Gücü: Güçlü Ayı (Bearish Momentum)
🧠 HTF Uyumu: H4 ve H1 Trendi Aşağı Yönlü

📌 Setup Türü: Order Block Mitigation
🎯 Entry Type: FVG Optimal Trade Entry (OTE)

💧 Likidite Hedefi: Sell Side Liquidity Swept
🌊 Volatilite: ATR Genişlemesi Mevcut
📰 Haber Riski: Temiz (Önümüzdeki 2 saat yüksek etki haber yok)

🎯 Giriş Aralığı: {giris_1:.2f} - {giris_2:.2f}
🛑 Stop Loss: {sl:.2f}
🎯 Take Profit: {tp:.2f}

📝 Analiz:
{enstruman} pazarında kurumsal Order Block ve FVG seviyeleri test edildi. Trend yönünde likidite yapısı onaylandı. Fiat üst bölgedeki Premium (Pahalılık) alanında yer alan inditigated (hafifletilmemiş) Order Block alanından kurumsal reddini yedi. 1:3.0 korumalı kurumsal kurulum aktif.
━━━━━━━━━━━━━━"""
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mesaj,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

# Simülasyon Devriye Motoru
if otonom_tarama:
    str_plat.success("Tüm piyasalar taranıyor... Kurumsal izler takip ediliyor.")
    
    # Test Amaçlı İlk Çalışmada Hemen Gönderim Tetikleme
    if "ilk_calisma" not in str_plat.session_state:
        str_plat.session_state["ilk_calisma"] = True
        telegram_firlat("ALTIN (XAUUSD)", "BEARISH", 4521.89876, 4524.50163, 4532.96097, 4493.91786)
        telegram_firlat("GÜMÜŞ (XAGUSD)", "BEARISH", 76.15373, 76.24427, 76.53853, 75.1804)
        str_plat.info("İlk test sinyalleri yeni şablonla Telegram'a fırlatıldı!")
else:
    str_plat.warning("Otonom tarama şu an kapalı. Başlatmak için sol menüyü açın.")
