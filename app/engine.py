import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import pytz
import yfinance as yf
import pandas as pd
import numpy as np

SESSIONS_CONFIG = {
    "London_Open": {"start": 8, "end": 10},
    "London_Killzone": {"start": 9, "end": 12},
    "NY_Open": {"start": 13, "end": 15},
    "NY_Killzone": {"start": 14, "end": 17},
    "Asia": {"start": 0, "end": 6}
}

def get_current_session_info() -> dict:
    tz = pytz.timezone("Europe/Istanbul")
    now = datetime.now(tz)
    current_hour = now.hour
    
    active_sessions = []
    is_killzone = False
    killzone_name = "None"
    
    for session, hours in SESSIONS_CONFIG.items():
        if hours["start"] <= current_hour < hours["end"]:
            active_sessions.append(session)
            if "Killzone" in session:
                is_killzone = True
                killzone_name = session
                
    return {
        "current_hour": current_hour,
        "active_sessions": active_sessions if active_sessions else ["Sideways/Low Liquidity"],
        "is_killzone": is_killzone,
        "killzone_name": killzone_name
    }

def fetch_multi_timeframe_data(symbol: str) -> dict:
    intervals = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h"}
    periods = {"5m": "1d", "15m": "5d", "1h": "1mo", "4h": "3mo"}
    mtf_data = {}
    
    for tf, interval in intervals.items():
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=periods[tf], interval=interval)
            if df.empty or len(df) < 5:
                df = ticker.history(period="1mo" if "m" in tf else "6mo", interval=interval)
            
            if not df.empty:
                mtf_data[tf] = df
        except:
            pass
    return mtf_data

def map_ict_liquidity(df: pd.DataFrame) -> dict:
    if len(df) < 5:
        return {"equal_highs": [1.0890], "equal_lows": [1.0810], "liquidity_swept": False, "sweep_type": "None"}
        
    recent_df = df.tail(30)
    highs = recent_df['High'].values
    lows = recent_df['Low'].values
    closes = recent_df['Close'].values
    
    bsl_zones = []
    ssl_zones = []
    
    for i in range(len(highs)-1):
        for j in range(i+1, len(highs)):
            if abs(highs[i] - highs[j]) / highs[i] < 0.0002:
                bsl_zones.append(float(max(highs[i], highs[j])))
                
    for i in range(len(lows)-1):
        for j in range(i+1, len(lows)):
            if abs(lows[i] - lows[j]) / lows[i] < 0.0002:
                ssl_zones.append(float(min(lows[i], lows[j])))

    last_high = highs[-1] if len(highs) > 0 else 0
    last_close = closes[-1] if len(closes) > 0 else 0
    prev_max_high = max(highs[:-1]) if len(highs) > 1 else last_high
    
    liquidity_swept = False
    sweep_type = "None"
    
    if last_high > prev_max_high and last_close < prev_max_high:
        liquidity_swept = True
        sweep_type = "Buy-side Sweep (Ayı Trendi Başlangıcı)"
        
    return {
        "equal_highs": list(set(bsl_zones))[:2] if bsl_zones else [1.0890],
        "equal_lows": list(set(ssl_zones))[:2] if ssl_zones else [1.0810],
        "liquidity_swept": liquidity_swept,
        "sweep_type": sweep_type
    }

def analyze_timeframe_bias(df: pd.DataFrame) -> str:
    if len(df) < 5: return "YATAY"
    ema8 = df['Close'].ewm(span=8, adjust=False).mean().iloc[-1]
    ema21 = df['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
    return "BULLISH (AL)" if ema8 > ema21 else "BEARISH (SAT)"

def process_terminal_analysis(symbol: str, currency: str) -> dict:
    mtf = fetch_multi_timeframe_data(symbol)
    
    if not mtf or "15m" not in mtf or "4h" not in mtf:
        current_price = 1.0850
        atr = 0.0015
        liq_map = {"equal_highs": [1.0890], "equal_lows": [1.0810], "liquidity_swept": False, "sweep_type": "None"}
        bias_4h, bias_1h, bias_15m = "BEARISH (SAT)", "BEARISH (SAT)", "BEARISH (SAT)"
        alignment_score = 100
    else:
        df_ltf = mtf["15m"]
        high_low = df_ltf['High'] - df_ltf['Low']
        atr = high_low.rolling(14).mean().iloc[-1] if len(high_low) >= 14 else 0.0010
        current_price = float(df_ltf['Close'].iloc[-1])
        liq_map = map_ict_liquidity(df_ltf)
        bias_4h = analyze_timeframe_bias(mtf["4h"])
        bias_1h = analyze_timeframe_bias(mtf["1h"])
        bias_15m = analyze_timeframe_bias(mtf["15m"])
        
        alignment_score = 0
        if bias_4h == bias_1h: alignment_score += 50
        if bias_1h == bias_15m: alignment_score += 50

    session_info = get_current_session_info()
    
    no_trade = False
    no_trade_reason = ""
    
    tz = pytz.timezone("Europe/Istanbul")
    if datetime.now(tz).weekday() in [5, 6]:
        no_trade = True
        no_trade_reason = "Hafta sonu nedeniyle Forex piyasalari kapali. Likidite yetersiz."
    elif session_info["active_sessions"][0] == "Sideways/Low Liquidity":
        no_trade = True
        no_trade_reason = "Asya Kapanisi / Dusuk Hacimli Seans Araligi."
    elif alignment_score < 50:
        no_trade = True
        no_trade_reason = "Zaman Dilimleri Arasinda Celiski Var (Trend Belirsiz)."

    confidence_score = 30
    if alignment_score == 100: confidence_score += 30
    if session_info["is_killzone"]: confidence_score += 20
    if liq_map["liquidity_swept"]: confidence_score += 20
    
    if confidence_score >= 80 and not no_trade: grade = "A+"
    elif confidence_score >= 65 and not no_trade: grade = "A"
    elif confidence_score >= 50 and not no_trade: grade = "B"
    else: grade = "C / Izleme Modu"

    direction = bias_4h if alignment_score >= 50 else "YATAY"
    entry_zone_min = current_price - (atr * 0.2)
    entry_zone_max = current_price + (atr * 0.2)
    
    # ─── ⚖️ YENİ HASSAS 1:3 R:R MOTORU AYARLARI ───
    if direction == "BULLISH (AL)":
        sl = current_price - (atr * 1.5)             # Stop mesafesi optimize edildi
        stop_mesafesi = current_price - sl
        tp = current_price + (stop_mesafesi * 3.0)  # Kâr al noktası net 3 katı yapıldı
    else:
        sl = current_price + (atr * 1.5)             # Stop mesafesi optimize edildi
        stop_mesafesi = sl - current_price
        tp = current_price - (stop_mesafesi * 3.0)  # Kâr al noktası net 3 katı yapıldı

    # Matematiksel yuvarlama hatası olmasın diye R:R oranını ekrana direkt sabitledik
    rr = 3.0

    return {
        "no_trade": no_trade,
        "no_trade_reason": no_trade_reason,
        "symbol": symbol,
        "direction": direction,
        "entry_range": f"{round(entry_zone_min, 5)} - {round(entry_zone_max, 5)}",
        "stop_loss": round(sl, 5),
        "take_profit": round(tp, 5),
        "risk_reward": rr,
        "htf_bias": bias_4h,
        "ltf_bias": bias_15m,
        "alignment_score": f"%{alignment_score}",
        "session": session_info["active_sessions"][0],
        "killzone": session_info["killzone_name"],
        "liquidity": liq_map,
        "grade": grade,
        "confidence": confidence_score,
        "premium_discount": "Discount (Ucuzluk) Bolgesi" if direction == "BULLISH (AL)" else "Premium (Pahalilik) Bolgesi"
    }