import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import json
import os

# ==========================================
# 🏛️ INSTITUTIONAL SETTINGS & PRODUCTION API
# ==========================================
st.set_page_config(page_title="NEXUS QUANT v23", layout="wide", page_icon="🏛️")

st.title("🏛️ NEXUS QUANT v23 — Cloud Production Core")
st.subheader("Finnhub API & SMC Matrix Engine (OB + FVG + BOS)")

TOKEN = "8834309699:AAEjA7F4OmbIQHfd9769Lz640GweHPYoStI"
CHAT_ID = "1183450421"

# FINNHUB VERIFIED API KEY
FINNHUB_API_KEY = "d8b2ft9r01qk20spcvigd8b2ft9r01qk20spcvj0"

BALANCE = 10000
RISK_PERCENT = 0.75
MIN_SCORE = 9.3
MIN_CONFIDENCE = 88
MAX_DAILY_SIGNALS = 2

pariteler = {
    "EURUSD": "OANDA:EUR_USD",
    "GBPUSD": "OANDA:GBP_USD",
    "XAUUSD": "OANDA:XAU_USD",
    "USDJPY": "OANDA:USD_JPY"
}

if "cooldown_dict" not in st.session_state:
    st.session_state.cooldown_dict = {}

if "trade_history" not in st.session_state:
    st.session_state.trade_history = [
        {"timestamp": "2026-05-27 02:00", "pair": "EURUSD", "direction": "BULLISH", "setup": "Bullish OB + FVG", "score": 9.4, "confidence": 90, "entry": 1.08250, "status": "ACTIVE"}
    ]

# ==========================================
# 📡 FINNHUB DATA STREAM ENGINE
# ==========================================
def get_data(ticker, resolution="15", days=5):
    try:
        end_time = int(time.time())
        start_time = end_time - (days * 24 * 60 * 60)
        url = f"https://finnhub.io/api/v1/forex/candle?symbol={ticker}&resolution={resolution}&from={start_time}&to={end_time}&token={FINNHUB_API_KEY}"
        resp = requests.get(url, timeout=10).json()
        
        if resp.get('s') != 'ok':
            return None
            
        return pd.DataFrame({
            'Open': resp['o'], 'High': resp['h'], 'Low': resp['l'], 'Close': resp['c'], 'Volume': resp['v']
        }).dropna().reset_index(drop=True)
    except:
        return None

# ==========================================
# 🧠 SMART MONEY CONCEPTS (SMC) ENGINES
# ==========================================
def detect_order_block(df):
    if len(df) < 35: return False, False, None
    for i in range(len(df) - 3, len(df) - 25, -1):
        body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
        range_hl = df['High'].iloc[i] - df['Low'].iloc[i] or 0.0001
        if (df['Close'].iloc[i] > df['Open'].iloc[i] and df['Low'].iloc[i] <= df['Low'].iloc[max(0, i-15):i+1].min() and body > range_hl * 0.65 and df['Close'].iloc[i+1] > df['High'].iloc[i]):
            return True, False, df['Low'].iloc[i]
        if (df['Close'].iloc[i] < df['Open'].iloc[i] and df['High'].iloc[i] >= df['High'].iloc[max(0, i-15):i+1].max() and df['Close'].iloc[i+1] < df['Low'].iloc[i]):
            return False, True, df['High'].iloc[i]
    return False, False, None

def detect_fvg(df, atr_value):
    if len(df) < 8: return False, False
    dynamic_gap = atr_value * 0.1
    for i in range(len(df) - 1, len(df) - 6, -1):
        if df['Low'].iloc[i] > (df['High'].iloc[i-2] + dynamic_gap) and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]: return True, False
        if df['High'].iloc[i] < (df['Low'].iloc[i-2] - dynamic_gap) and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]: return False, True
    return False, False

def detect_bos(df):
    if len(df) < 21: return False, False
    recent_high = df['High'].iloc[:-1].rolling(20).max().iloc[-1]
    recent_low = df['Low'].iloc[:-1].rolling(20).min().iloc[-1]
    return df['Close'].iloc[-1] > recent_high, df['Close'].iloc[-1] < recent_low

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    return 100 - (100 / (1 + (gain / (loss + 1e-9))))

def send_signal(pair, direction, score, confidence, entry, sl, tp, lot, setup):
    ondalik = 5 if any(x in pair for x in ["EUR","GBP","AUD"]) else 2
    mesaj = f"""%0A🏛️ NEXUS v23.0 CLOUD SİNYAL %0A━━━━━━━━━━━━━━%0A🎯 Pair: {pair}%0A📈 Yön: {direction}%0A🔥 Setup: {setup}%0A🏦 Score: {score:.1f}/10 | Conf: %{confidence}%0A%0A🎯 Entry: {entry:.{ondalik}f}%0A🛑 SL: {sl:.{ondalik}f} | 🎯 TP: {tp:.{ondalik}f}%0A⚖️ Lot Size: {lot:.2f}%0A⏱️ Time: {datetime.now().strftime('%H:%M:%S')}"""
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mesaj}&parse_mode=Markdown", timeout=5)
    except:
        pass

# ==========================================
# 🔍 OTONOM DEVRIYE PIPELINE
# ==========================================
st.info("📡 Finnhub Canlı Veri Odası Aktif. Yarım saatte bir otomatik tarama tetiklenir.")

executed = 0
current_hour = datetime.now().hour
session = "London" if 8 <= current_hour < 15 else "NY" if 15 <= current_hour < 22 else "Asia"

rejection_list = []

for name, ticker in pariteler.items():
    if executed >= MAX_DAILY_SIGNALS: break
    su_an_time = time.time()
    if name in st.session_state.cooldown_dict and su_an_time - st.session_state.cooldown_dict[name] < 10800:
        rejection_list.append(f"🛡️ {name} - Cooldown aktif (3 saat)")
        continue

    df15 = get_data(ticker, "15", days=3)
    df60 = get_data(ticker, "60", days=5)
    df240 = get_data(ticker, "D", days=15)
    
    if df15 is None or df60 is None or df240 is None or df15.empty or df60.empty or df240.empty:
        rejection_list.append(f"❌ {name} - Veri hattı kesintisi")
        continue

    price = float(df15['Close'].iloc[-1])
    atr = (df15['High'] - df15['Low']).rolling(14).mean().iloc[-1] or 0.0010

    bias = "BULLISH" if df240['Close'].ewm(span=9, adjust=False).mean().iloc[-1] > df240['Close'].ewm(span=21, adjust=False).mean().iloc[-1] else "BEARISH"
    h1_bias = "BULLISH" if df60['Close'].ewm(span=9, adjust=False).mean().iloc[-1] > df60['Close'].ewm(span=21, adjust=False).mean().iloc[-1] else "BEARISH"
    rsi = calculate_rsi(df15['Close']).iloc[-1]
    volume_ok = df15['Volume'].iloc[-1] > df15['Volume'].rolling(20).mean().iloc[-1]

    fvg_bull, fvg_bear = detect_fvg(df15, atr)
    bos_bull, bos_bear = detect_bos(df15)
    ob_bull, ob_bear, _ = detect_order_block(df15)

    score = 5.0
    confidence = 60
    setup_type = "Base"

    if bias == h1_bias: score += 2.0; confidence += 14
    if volume_ok: score += 1.3; confidence += 10
    if 42 < rsi < 58: score += 1.1
    if rsi > 73 or rsi < 27: score -= 2.2; setup_type += " [RSI Extreme]"

    if bias == "BULLISH":
        if ob_bull: score += 2.5; confidence += 15; setup_type = "Bullish OB"
        if fvg_bull: score += 2.0; setup_type += " + FVG"
        if bos_bull: score += 1.7; setup_type += " + BOS"
    else:
        if ob_bear: score += 2.5; confidence += 15; setup_type = "Bearish OB"
        if fvg_bear: score += 2.0; setup_type += " + iFVG"
        if bos_bear: score += 1.7; setup_type += " + BOS"

    if session in ["London", "NY"]: score += 0.8

    score = min(10.0, max(0.0, score))
    confidence = min(100, max(0, confidence))

    if score >= MIN_SCORE and confidence >= MIN_CONFIDENCE:
        sl = price - (atr * 2) if bias == "BULLISH" else price + (atr * 2)
        tp = price + (atr * 4) if bias == "BULLISH" else price - (atr * 4)
        stop_dist = abs(price - sl)
        multiplier = 100 if "XAU" in name else 100000
        lot = max(0.01, min(5.0, round((BALANCE * (RISK_PERCENT / 100)) / (stop_dist * multiplier), 2)))

        send_signal(name, bias, score, confidence, price, sl, tp, lot, setup_type)
        st.session_state.cooldown_dict[name] = su_an_time
        st.session_state.trade_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "pair": name, "direction": bias, "setup": setup_type, "score": round(score, 1), "confidence": confidence, "entry": price, "status": "ACTIVE"
        })
        executed += 1
        st.success(f"✅ {name} - Elit Sinyal Üretildi!")
    else:
        rejection_list.append(f"❌ {name} - Filtre Gerisinde Kaldı (Skor: {score:.1f}/10)")

# ====================== PANEL ARA YÜZÜ ======================
st.write("---")
st.subheader("🛡️ Otonom Sinyal Denetleme Matrisi")
for r_log in rejection_list: st.error(r_log)

st.write("---")
st.subheader("📊 Canlı İzleme & Trade Geçmişi")
st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True)

# ====================== YARIM SAATTE BİR YENİLEME MOTORU ======================
st.caption(f"Son Başarılı Tarama: {datetime.now().strftime('%H:%M:%S')}")
# 30 Dakika = 1800 Saniye
st.components.v1.html(f"<script>setTimeout(function(){{ window.parent.location.reload(); }}, 1800000);</script>", height=0, width=0)
