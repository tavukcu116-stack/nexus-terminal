from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.engine as engine
import requests

app = FastAPI(title="Institutional AI Forex Terminal Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TELEGRAM_TOKEN = "8834309699:AAEjA7F4OmbIQHfd9769Lz640GweHPYoStI"
TELEGRAM_CHAT_ID = "1183450421"

def generate_ai_narrative(data: dict) -> str:
    if data["no_trade"]:
        return f"🚨 KURUMSAL RİSK UYARISI: Sinyal motoru koruma moduna geçti. Sebebi: {data['no_trade_reason']}"
               
    narrative = f"🏛️ YÖNETİCİ ÖZETİ ({data['symbol']}): " \
                f"Büyük Oyuncuların Yönü (4H HTF) şu an tamamen {data['direction']} eğiliminde olup, " \
                f"Küçük Zaman Dilimi (15M LTF) ile {data['alignment_score']} oranında uyum göstermektedir. " \
                f"Fiyat şu an {data['premium_discount']} içinde konumlanmış durumda."
    return narrative

@app.get("/api/analyze")
def get_analysis(symbol: str = "EURUSD=X", currency: str = "USD"):
    # Gelen sembol isteğine göre isim temizliği yapıyoruz
    if symbol == "NASDAQ":
        target_symbol = "^IXIC"
    elif symbol == "BIST100":
        target_symbol = "XU100.IS"
    else:
        target_symbol = symbol

    raw_analysis = engine.process_terminal_analysis(target_symbol, currency)
    ai_story = generate_ai_narrative(raw_analysis)
    raw_analysis["ai_narrative"] = ai_story
    
    clean_name = target_symbol.replace("=X", "").replace("^", "").replace(".IS", "")
    
    tg_msg = f"🏛️ *AI TRADING TERMINAL RAPORU*\n\n"
    if raw_analysis["no_trade"]:
        tg_msg += f"❌ *İŞLEM ENGELLENDİ (NO TRADE)*\n📌 Nedeni: {raw_analysis['no_trade_reason']}"
    else:
        tg_msg += f"🔥 *SETUP KALİTESİ: {raw_analysis['grade']}*\n" \
                  f"🎯 Enstrüman: {clean_name}\n" \
                  f"📈 Yön: {raw_analysis['direction']}\n" \
                  f"⚡ Güven Skoru: {raw_analysis['confidence']}/100\n" \
                  f"💎 R:R Oranı: 1:{raw_analysis['risk_reward']}\n\n" \
                  f"📝 *Analiz Hikayesi:*\n_{ai_story}_"
                  
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": tg_msg, "parse_mode": "Markdown"})
    except:
        pass
        
    return raw_analysis