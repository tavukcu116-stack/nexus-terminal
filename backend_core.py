# ==========================================
# 📄 DOSYA: backend_core.py (NEXUS QUANT v65.0 - SAFENET CORE)
# ==========================================
import os
import requests
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "MOCK_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_clean_candles(symbol, interval="15min", outputsize="100"):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_KEY}"
        r = requests.get(url, timeout=5).json()
        if "code" in r or "status" in r and r.get("status") == "error": return None
        if "values" in r:
            df = pd.DataFrame(r["values"])
            for col in ["open", "high", "low", "close"]: df[col] = df[col].astype(float)
            df['datetime'] = pd.to_datetime(df['datetime'])
            if len(df) < 50: return None
            return df.dropna().drop_duplicates(subset=["datetime"]).iloc[::-1].reset_index(drop=True)
    except: pass

    try:
        y_sym = f"{symbol.replace('/', '')}=X"
        url = f"https://query1.financeapp.yahoo.com/v8/finance/chart/{y_sym}?interval=15m&range=3d"
        res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).json()
        result = res["chart"]["result"][0]
        df = pd.DataFrame({
            "datetime": pd.to_datetime(result["timestamp"], unit='s'),
            "open": result["indicators"]["quote"][0]["open"],
            "high": result["indicators"]["quote"][0]["high"],
            "low": result["indicators"]["quote"][0]["low"],
            "close": result["indicators"]["quote"][0]["close"]
        })
        if len(df) >= 50: return df.dropna().reset_index(drop=True)
    except: pass
    return None

def get_live_spread_data(symbol):
    try:
        url = f"https://api.twelvedata.com/quotes?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        r = requests.get(url, timeout=4).json()
        if "bid" in r and "ask" in r:
            bid, ask = float(r["bid"]), float(r["ask"])
            multiplier = 10 if "XAU" in symbol else 10000
            return round(abs(ask - bid) * multiplier, 2), bid, ask
    except: pass
    return 1.2, 0.0, 0.0

def check_economic_news_barrier(symbol):
    try:
        url = "https://www.forexfactory.com/ffcal_xml_thisweek.xml"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200: return False
        root = ET.fromstring(r.content)
        now_utc = datetime.now(timezone.utc)
        
        active_currency = "USD"
        for c in ["EUR", "GBP"]:
            if c in symbol: active_currency = c
            
        for event in root.findall('event'):
            if event.find('currency').text == active_currency and event.find('impact').text == "High":
                dt, tm = event.find('date').text, event.find('time').text
                event_time = datetime.strptime(f"{dt} {tm}", "%m-%d-%Y %I:%M%p").replace(tzinfo=timezone.utc)
                if event_time - timedelta(minutes=30) <= now_utc <= event_time + timedelta(minutes=30):
                    return True
        return False
    except: return False

def send_telegram_signal_report(asset, bias, entry, sl, tp1, tp2, score, reasons):
    if not TG_TOKEN or not TG_CHAT_ID: return False
    signal_tag = "👑 PREMIUM SMC SETUP" if score >= 85 else "⚡ NORMAL SMC SETUP"
    reasons_str = "\n".join([f"- {r}" for r in reasons])
    
    msg = (
        f"🏛️ *NEXUS SIGNAL MATRIX v65.0*\n\n"
        f"⚠️ *[{signal_tag}]*\n\n"
        f"💱 *Asset / Parite:* {asset}\n"
        f"🚀 *Action Vector:* `{bias} (RETEST GİRİŞ)`\n\n"
        f"📍 *Entry Price:* {entry:.5f}\n"
        f"🛑 *Stop Loss:* {sl:.5f}\n"
        f"🎯 *Target TP1 (1.5x):* {tp1:.5f}\n"
        f"🎯 *Target TP2 (3.0x Final):* {tp2:.5f}\n\n"
        f"📊 *SMC Score:* `{score}/100` (Minimum RR >= 1:2)\n\n"
        f"🧠 *Signal Confluence (Gerekçe):*\n{reasons_str}\n\n"
        f"🔒 _Zırhlı Üretim Filtresi Başarıyla Tamamlandı._"
    )
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
        return True
    except: return False

def analyze_advanced_trend_structure(df_htf):
    if df_htf is None or len(df_htf) < 30: return "WAIT", 0.0, 0.0, 0.0
    highs, lows = df_htf["high"].values, df_htf["low"].values
    
    sh = [highs[i] for i in range(2, len(df_htf)-2) if highs[i] == max(highs[i-2:i+3])]
    sl = [lows[i] for i in range(2, len(df_htf)-2) if lows[i] == min(lows[i-2:i+3])]
    
    last_sh = sh[-1] if sh else highs.max()
    last_sl = sl[-1] if sl else lows.min()
    eq = (last_sh + last_sl) / 2
    
    if len(sh) < 2 or len(sl) < 2: return "WAIT", last_sh, last_sl, eq
    if sh[-1] > sh[-2] and sl[-1] > sl[-2]: return "BULLISH", last_sh, last_sl, eq
    if sh[-1] < sh[-2] and sl[-1] < sl[-2]: return "BEARISH", last_sh, last_sl, eq
    return "WAIT", last_sh, last_sl, eq

def extract_quant_smc_matrix(symbol):
    df_4h = fetch_clean_candles(symbol, "4h", "60")
    df_1h = fetch_clean_candles(symbol, "1h", "60")
    df_15m = fetch_clean_candles(symbol, "15min", "100")
    
    if df_4h is None or df_1h is None or df_15m is None: return None
    
    idx = len(df_15m) - 1
    close_p, high_p, low_p = df_15m["close"].iloc[idx], df_15m["high"].iloc[idx], df_15m["low"].iloc[idx]
    atr = (df_15m["high"] - df_15m["low"]).rolling(14).mean().iloc[-1]

    hist_vol = (df_15m["high"] - df_15m["low"]).rolling(50).mean().iloc[-1]
    if atr < (hist_vol * 0.75):
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "LOW VOLATILITY BLOCKED", "df": df_15m, "ob": None, "fvg": None, "reasons": []}

    utc_hour = datetime.now(timezone.utc).hour
    if not (7 <= utc_hour <= 19):
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "KILLZONE STANDBY (07-19 UTC)", "df": df_15m, "ob": None, "fvg": None, "reasons": []}

    reasons = []
    score = 0

    trend_4h, pdh, pdl, eq_level = analyze_advanced_trend_structure(df_4h)
    trend_1h, _, _, _ = analyze_advanced_trend_structure(df_1h)
    
    market_zone = "PREMIUM" if close_p > eq_level else "DISCOUNT"

    if trend_4h == "WAIT" or trend_4h != trend_1h:
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "HTF TREND MISALIGNMENT", "df": df_15m, "ob": None, "fvg": None, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone, "reasons": []}
    
    score += 20
    reasons.append(f"HTF Trend: {trend_4h}")

    sh_15 = [df_15m["high"].iloc[i] for i in range(4, idx-4) if df_15m["high"].iloc[i] == max(df_15m["high"].iloc[i-4:i+5])]
    sl_15 = [df_15m["low"].iloc[i] for i in range(4, idx-4) if df_15m["low"].iloc[i] == min(df_15m["low"].iloc[i-4:i+5])]
    last_sh = sh_15[-1] if sh_15 else pdh
    last_sl = sl_15[-1] if sl_15 else pdl

    sweep_detected = (high_p > last_sh and close_p < last_sh) or (low_p < last_sl and close_p > last_sl)
    if not sweep_detected:
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "AWAITING LIQUIDITY SWEEP", "df": df_15m, "ob": None, "fvg": None, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone, "reasons": []}
    score += 20
    reasons.append("Liquidity Sweep Confirmed")

    displacement = abs(close_p - df_15m["open"].iloc[idx]) > (atr * 0.9)
    structure_type = "BOS BULLISH" if displacement and close_p > last_sh else "BOS BEARISH" if displacement and close_p < last_sl else "RANGE"
    
    if structure_type == "RANGE":
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "NO DISPLACEMENT BREAKOUT", "df": df_15m, "ob": None, "fvg": None, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone, "reasons": []}
    score += 20
    reasons.append(f"Structure: {structure_type}")

    active_ob, active_fvg = None, None
    for i in range(idx-25, idx-1):
        if trend_4h == "BULLISH":
            if df_15m["close"].iloc[i] < df_15m["open"].iloc[i] and df_15m["close"].iloc[i+1] > df_15m["open"].iloc[i+1]:
                future_lows = df_15m["low"].iloc[i+2:idx+1]
                if len(future_lows) == 0 or not (future_lows < df_15m["low"].iloc[i]).any():
                    active_ob = {"type": "BULLISH OB", "top": df_15m["high"].iloc[i], "bottom": df_15m["low"].iloc[i]}
            if df_15m["low"].iloc[i+2] - df_15m["high"].iloc[i] > (atr * 0.4):
                active_fvg = {"type": "BULLISH FVG", "top": df_15m["low"].iloc[i+2], "bottom": df_15m["high"].iloc[i]}
        elif trend_4h == "BEARISH":
            if df_15m["close"].iloc[i] > df_15m["open"].iloc[i] and df_15m["close"].iloc[i+1] < df_15m["open"].iloc[i+1]:
                future_highs = df_15m["high"].iloc[i+2:idx+1]
                if len(future_highs) == 0 or not (future_highs > df_15m["high"].iloc[i]).any():
                    active_ob = {"type": "BEARISH OB", "top": df_15m["high"].iloc[i], "bottom": df_15m["low"].iloc[i]}
            if df_15m["low"].iloc[i] - df_15m["high"].iloc[i+2] > (atr * 0.4):
                active_fvg = {"type": "BEARISH FVG", "top": df_15m["low"].iloc[i], "bottom": df_15m["high"].iloc[i+2]}

    if not active_ob and not active_fvg:
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "NO CONFLUENCE ZONE", "df": df_15m, "ob": None, "fvg": None, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone, "reasons": []}

    bias = "WAIT"
    retest_passed = False
    
    if trend_4h == "BULLISH" and market_zone == "DISCOUNT":
        if active_ob and low_p <= active_ob["top"] and close_p >= active_ob["bottom"]:
            bias = "BUY"; retest_passed = True; reasons.append("OB Retest Passed")
        elif active_fvg and low_p <= active_fvg["top"] and close_p >= active_fvg["bottom"]:
            bias = "BUY"; retest_passed = True; reasons.append("FVG Retest Passed")
    elif trend_4h == "BEARISH" and market_zone == "PREMIUM":
        if active_ob and high_p >= active_ob["bottom"] and close_p <= active_ob["top"]:
            bias = "SELL"; retest_passed = True; reasons.append("OB Retest Passed")
        elif active_fvg and high_p >= active_fvg["bottom"] and close_p <= active_fvg["top"]:
            bias = "SELL"; retest_passed = True; reasons.append("FVG Retest Passed")

    if not retest_passed:
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "AWAITING ZONE RETEST", "df": df_15m, "ob": active_ob, "fvg": active_fvg, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone, "reasons": []}

    score += 40
    q_class = "PREMIUM" if score >= 85 else "NORMAL"

    sl_p = tp1_p = tp2_p = 0.0
    zone_target = active_ob if active_ob else active_fvg
    if bias == "BUY":
        sl_p = zone_target["bottom"] - (atr * 0.1)
        risk = abs(close_p - sl_p)
        tp1_p = close_p + (risk * 1.5); tp2_p = close_p + (risk * 3.0)
    elif bias == "SELL":
        sl_p = zone_target["top"] + (atr * 0.1)
        risk = abs(sl_p - close_p)
        tp1_p = close_p - (risk * 1.5); tp2_p = close_p - (risk * 3.0)

    calculated_rr = round(abs(tp2_p - close_p) / (abs(close_p - sl_p) + 1e-9), 1)
    if calculated_rr < 2.0:
        return {"bias": "WAIT", "score": 0, "q_class": "WAIT", "action": "REJECTED: RR TOO LOW", "df": df_15m, "ob": active_ob, "fvg": active_fvg, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone, "reasons": []}

    return {
        "df": df_15m, "price": close_p, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone,
        "sh": last_sh, "sl": last_sl, "bias": bias, "structure": structure_type, "ob": active_ob, "fvg": active_fvg,
        "sl_p": sl_p, "tp1_p": tp1_p, "tp2_p": tp2_p, "rr": calculated_rr, "score": score, "q_class": q_class,
        "action": "SIGNAL TRIGGERED", "reasons": reasons
        }
    
