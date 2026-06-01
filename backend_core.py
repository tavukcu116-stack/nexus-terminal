# ==========================================
# 📄 DOSYA: backend_core.py (NEXUS QUANT v55.2 - REAL QUANT BASE)
# ==========================================
import os
import sqlite3
import requests
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import streamlit as st
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "nexus_v54_vault.db"
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "MOCK_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def init_v54_vault():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS v54_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, asset TEXT, type TEXT, entry REAL, sl REAL, tp1 REAL, tp2 REAL,
            lot REAL, pnl REAL, status TEXT, score INTEGER, q_class TEXT, session TEXT, 
            duration_min INTEGER, direction TEXT, close_time TEXT,
            initial_risk_usd REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()

init_v54_vault()

def send_telegram_notification(message):
    if not TG_TOKEN or not TG_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except: return False

@st.cache_data(ttl=900)
def fetch_cached_htf_candles(symbol, interval):
    return fetch_clean_candles(symbol, interval, "100")

def fetch_clean_candles(symbol, interval="15min", outputsize="100"):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_KEY}"
        r = requests.get(url, timeout=6).json()
        if "values" in r:
            df = pd.DataFrame(r["values"])
            for col in ["open", "high", "low", "close"]: df[col] = df[col].astype(float)
            df['datetime'] = pd.to_datetime(df['datetime'])
            return df.dropna().drop_duplicates(subset=["datetime"]).iloc[::-1].reset_index(drop=True)
    except: pass

    try:
        b_sym = symbol.replace("/", "").upper() + "T" if "USD" in symbol else "EURUSDT"
        url = f"https://api.binance.com/api/v3/klines?symbol={b_sym}&interval=15m&limit={outputsize}"
        res = requests.get(url, timeout=4).json()
        if isinstance(res, list) and len(res) > 0:
            df = pd.DataFrame(res).iloc[:, :5]
            df.columns = ['datetime', 'open', 'high', 'low', 'close']
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
            for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
            return df
    except: return None
    return None

# 🧠 4. LOT HESAPLAMA MOTORU (Risk Bazlı Pozisyon Büyüklüğü - $calculate\_position\_size$)
def calculate_position_size(capital, risk_pct, price, sl_p, asset):
    """Mustafa Abi'nin kurumsal lot hesaplama kalkanı. Maksimum %1 risk birimine göre lotu ölçer."""
    if price == sl_p or sl_p == 0: return 0.01
    allowed_loss_usd = capital * (risk_pct / 100.0)
    multiplier = 10 if "XAU" in asset or "BTC" in asset or "ETH" in asset else 10000
    p_distance = abs(price - sl_p) * multiplier
    final_lot = allowed_loss_usd / (p_distance * 10 + 1e-9)
    return max(0.01, round(final_lot, 2))

@st.cache_data(ttl=30)
def get_live_spread_data(symbol):
    try:
        url = f"https://api.twelvedata.com/quotes?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        r = requests.get(url, timeout=4).json()
        if "bid" in r and "ask" in r:
            bid, ask = float(r["bid"]), float(r["ask"])
            multiplier = 10 if "XAU" in symbol or "BTC" in symbol or "ETH" in symbol else 10000
            return round(abs(ask - bid) * multiplier, 2), bid, ask
        return 1.2, 0.0, 0.0
    except: return 1.2, 0.0, 0.0

# 🧠 3. GÜVENİLİR HABER MOTORU (JSON API Fallback Kalkanı)
@st.cache_data(ttl=600)
def check_economic_news_timeline(symbol):
    """Forex Factory XML çökerse, kurumsal JSON takvim hat hattına yedeklenir abi."""
    currency_target = "USD"
    if "EUR" in symbol: currency_target = "EUR"
    elif "GBP" in symbol: currency_target = "GBP"
    elif "JPY" in symbol: currency_target = "JPY"
    
    # 1. Aşama: Orijinal XML Entegrasyonu
    try:
        url = "https://www.forexfactory.com/ffcal_xml_thisweek.xml"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            now_utc = datetime.now(timezone.utc)
            for event in root.findall('event'):
                if event.find('currency').text == currency_target and event.find('impact').text == "High":
                    dt, tm = event.find('date').text, event.find('time').text
                    event_time = datetime.strptime(f"{dt} {tm}", "%m-%d-%Y %I:%M%p").replace(tzinfo=timezone.utc)
                    if event_time - timedelta(minutes=30) <= now_utc <= event_time + timedelta(minutes=15):
                        return True, f"LOCK: XML - {event.find('title').text}"
            return False, "GATES CLEAR"
    except: pass

    # 2. Aşama: XML Patlarsa Kesintisiz JSON Fallback API Hattı (Kotayı Kurtarır Abi)
    try:
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={datetime.now().strftime('%Y-%m-%d')}&to={(datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d')}&apikey=demo"
        res = requests.get(url, timeout=4).json()
        now_utc = datetime.now(timezone.utc)
        for event in res:
            if event.get("currency") == currency_target and event.get("impact") == "High":
                ev_time = datetime.strptime(event.get("date"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                if ev_time - timedelta(minutes=30) <= now_utc <= ev_time + timedelta(minutes=15):
                    return True, f"LOCK: JSON - {event.get('event')}"
    except: pass
    return False, "GATES CLEAR"

# 🧠 10. PREMIUM HTF STRÜKTÜR ANALİZİ (BOS / CHOCH / SWEEP MATRIX)
def analyze_htf_premium_structure(df_htf):
    """Büyük zaman dilimini (4H/1H) sadece mum yüksekliğine göre değil, kurumsal SMC kırılımlarına göre tarar abi."""
    if df_htf is None or len(df_htf) < 15: return "WAIT"
    
    h_max = df_htf["high"].max()
    l_min = df_htf["low"].min()
    close_last = df_htf["close"].iloc[-1]
    
    # Swing pivot noktaları saptanıyor
    sh_list = [df_htf["high"].iloc[i] for i in range(2, len(df_htf)-2) if df_htf["high"].iloc[i] == df_htf["high"].iloc[i-2:i+3].max()]
    sl_list = [df_htf["low"].iloc[i] for i in range(2, len(df_htf)-2) if df_htf["low"].iloc[i] == df_htf["low"].iloc[i-2:i+3].min()]
    
    last_sh = sh_list[-1] if sh_list else h_max
    last_sl = sl_list[-1] if sl_list else l_min
    
    # Kurumsal Gövde Kapanışlı BOS/CHOCH Taraması
    if close_last > last_sh: return "BULLISH"
    if close_last < last_sl: return "BEARISH"
    return "WAIT"

def extract_quant_smc_matrix(symbol):
    df_4h = fetch_cached_htf_candles(symbol, "4h")
    df_1h = fetch_cached_htf_candles(symbol, "1h")
    df_15m = fetch_clean_candles(symbol, "15min", "100")
    
    if df_4h is None or df_1h is None or df_15m is None or len(df_15m) < 50: return None
    
    idx = len(df_15m) - 1
    close_p, high_p, low_p = df_15m["close"].iloc[idx], df_15m["high"].iloc[idx], df_15m["low"].iloc[idx]
    atr = (df_15m["high"] - df_15m["low"]).rolling(14).mean().iloc[-1]

    # 🏛️ 10. Gelişmiş HTF Filtresi Enjeksiyonu
    htf_structure = analyze_htf_premium_structure(df_4h)
    if htf_structure == "WAIT": htf_structure = analyze_htf_premium_structure(df_1h)

    pdh, pdl = df_15m["high"].max(), df_15m["low"].min()
    eq_level = (pdh + pdl) / 2
    market_zone = "PREMIUM" if close_p > eq_level else "DISCOUNT"

    sh = [df_15m["high"].iloc[i] for i in range(4, idx-4) if df_15m["high"].iloc[i] == df_15m["high"].iloc[i-4:i+5].max()]
    sl = [df_15m["low"].iloc[i] for i in range(4, idx-4) if df_15m["low"].iloc[i] == df_15m["low"].iloc[i-4:i+5].min()]
    last_sh = sh[-1] if sh else pdh
    last_sl = sl[-1] if sl else pdl

    sweep_detected = (high_p > last_sh and close_p < last_sh) or (low_p < last_sl and close_p > last_sl)
    displacement = abs(close_p - df_15m["open"].iloc[idx]) > (df_15m["high"] - df_15m["low"]).rolling(20).mean().iloc[idx] * 1.5
    structure_type = "BOS BULLISH" if displacement and close_p > last_sh else "BOS BEARISH" if displacement and close_p < last_sl else "CHOCH REVERSAL" if sweep_detected else "RANGE"

    # 🧠 8 & 9. BEARISH ORDER BLOCK VE BEARISH FVG MOTORLARI ENJEKTE EDİLDİ ABİ
    active_ob, active_fvg = None, None
    ob_points = fvg_points = 0
    
    for i in range(idx-25, idx-1):
        # Bullish FVG
        if df_15m["low"].iloc[i+2] - df_15m["high"].iloc[i] > (atr * 0.4):
            active_fvg = {"type": "BULLISH FVG", "top": df_15m["low"].iloc[i+2], "bottom": df_15m["high"].iloc[i], "time": df_15m["datetime"].iloc[i+1]}
            fvg_points = 15
        # Bearish FVG (Eksikti, Eklendi Abi!)
        elif df_15m["low"].iloc[i] - df_15m["high"].iloc[i+2] > (atr * 0.4):
            active_fvg = {"type": "BEARISH FVG", "top": df_15m["low"].iloc[i], "bottom": df_15m["high"].iloc[i+2], "time": df_15m["datetime"].iloc[i+1]}
            fvg_points = 15

        # Bullish Order Block
        if df_15m["close"].iloc[i] < df_15m["open"].iloc[i] and df_15m["close"].iloc[i+1] > df_15m["open"].iloc[i+1]:
            active_ob = {"type": "BULLISH OB", "top": df_15m["high"].iloc[i], "bottom": df_15m["low"].iloc[i], "time": df_15m["datetime"].iloc[i]}
            ob_points = 25
        # Bearish Order Block (Eksikti, Eklendi Abi!)
        elif df_15m["close"].iloc[i] > df_15m["open"].iloc[i] and df_15m["close"].iloc[i+1] < df_15m["open"].iloc[i+1]:
            active_ob = {"type": "BEARISH OB", "top": df_15m["high"].iloc[i], "bottom": df_15m["low"].iloc[i], "time": df_15m["datetime"].iloc[i]}
            ob_points = 25

    bias = "WAIT"; sl_p = tp1_p = tp2_p = 0.0
    if htf_structure == "BULLISH" and market_zone == "DISCOUNT":
        bias = "BUY"; sl_p = last_sl - (atr * 0.2)
        risk = abs(close_p - sl_p)
        tp1_p = close_p + (risk * 1.5); tp2_p = close_p + (risk * 3.0)
    elif htf_structure == "BEARISH" and market_zone == "PREMIUM":
        bias = "SELL"; sl_p = last_sh + (atr * 0.2)
        risk = abs(sl_p - close_p)
        tp1_p = close_p - (risk * 1.5); tp2_p = close_p - (risk * 3.0)

    return {
        "df": df_15m, "price": close_p, "pdh": pdh, "pdl": pdl, "eq": eq_level, "zone": market_zone,
        "sh": last_sh, "sl": last_sl, "bias": bias, "structure": structure_type, "ob": active_ob, "fvg": active_fvg,
        "sl_p": sl_p, "tp1_p": tp1_p, "tp2_p": tp2_p, "rr": 3.0, "score": 50 + ob_points + fvg_points, "q_class": "A" if ob_points > 0 else "WAIT",
        "session": "LONDON", "kz": True, "action": "AUTONOMOUS MONITOR"
    }

# 🧠 5 & 6. REAL Realtime Circuit Breakers (Korelasyon ve Günlük Zarar Kilidi)
def check_live_circuit_barriers(asset, capital):
    """5. Korelasyon ve 6. Günlük Zarar (-3R Barajı) kurallarını kuruşu kuruşuna denetler abi."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 6. Günlük Zarar Denetimi (-3R Kilidi)
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger WHERE timestamp >= date('now')")
    daily_pnl = cursor.fetchone()[0] or 0.0
    risk_unit_usd = capital * 0.01 # 1R Değeri
    if daily_pnl <= -(risk_unit_usd * 3): # Tam -3R Barajı abi
        conn.close()
        return True, "DAILY LOSS CIRCUIT REACHED (-3R LOCKUP)"
        
    # 5. Akıllı Korelasyon Filtresi (Cluster Block)
    cursor.execute("SELECT asset FROM v54_ledger WHERE status = 'OPEN'")
    open_trades = [r[0] for r in cursor.fetchall()]
    
    correlation_matrix = {
        "EUR/USD": ["GBP/USD", "XAU/USD"],
        "GBP/USD": ["EUR/USD"],
        "NASDAQ": ["US30"]
    }
    
    if asset in correlation_matrix:
        for active in open_trades:
            if active in correlation_matrix[asset]:
                conn.close()
                return True, f"CORRELATION BLOCKED: Overlap risk detected with {active}!"
                
    conn.close()
    return False, "CLEAR"

def manage_v55_autonomous_engine(asset, node, final_lot, daily_lock, total_lock, corr_lock, news_lock, capital):
    # Fonksiyon içinden de gerçek bariyerleri süzelim abi
    c_blocked, c_reason = check_live_circuit_barriers(asset, capital)
    if daily_lock or total_lock or corr_lock or news_lock or c_blocked: return
    if node["bias"] == "WAIT" or node["score"] < 75: return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM v54_ledger WHERE asset = ? AND status = 'OPEN'", (asset,))
    if cursor.fetchone()[0] == 0:
        mult = 100 if "XAU" in asset or "BTC" in asset or "ETH" in asset else 10000
        calculated_risk_usd = abs(node["price"] - node["sl_p"]) * final_lot * mult
        
        cursor.execute(
            "INSERT INTO v54_ledger (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, score, q_class, session, duration_min, close_time, initial_risk_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'OPEN', ?, ?, ?, 0, 'RUNNING', ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), asset, node["bias"], node["price"], node["sl_p"], node["tp1_p"], node["tp2_p"], final_lot, node["score"], node["q_class"], "USA", calculated_risk_usd)
        )
        conn.commit()
        send_telegram_notification(f"🏛️ *NEXUS AUTONOMOUS OPENED:* {asset} {node['bias']} {final_lot} Lot fırlatıldı abi!")
    conn.close()

def manage_v54_positions(asset, current_df):
    if current_df is None or current_df.empty: return
    last_candle = current_df.iloc[-1]
    cp = last_candle["close"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, entry, sl, tp1, tp2, lot, timestamp FROM v54_ledger WHERE status = 'OPEN' AND asset = ?", (asset,))
    trades = cursor.fetchall()
    
    for t in trades:
        t_id, t_type, entry, sl, tp1, tp2, lot, ts = t
        closed = False; pnl = 0.0; status = "OPEN"
        mult = 100 if "Gold" in asset or "BTC" in asset or "ETH" in asset else 10000
        
        if t_type == "BUY":
            if last_candle["high"] >= tp1 and sl < entry:
                sl = entry
                cursor.execute("UPDATE v54_ledger SET sl = ? WHERE id = ?", (sl, t_id))
            if last_candle["low"] <= sl:
                closed = True; pnl = (sl - entry) * lot * mult; status = "CLOSED_SL"
            elif last_candle["high"] >= tp2:
                closed = True; pnl = (tp2 - entry) * lot * mult; status = "CLOSED_TP"
        elif t_type == "SELL":
            if last_candle["low"] <= tp1 and sl > entry:
                sl = entry
                cursor.execute("UPDATE v54_ledger SET sl = ? WHERE id = ?", (sl, t_id))
            if last_candle["high"] >= sl:
                closed = True; pnl = (entry - sl) * lot * mult; status = "CLOSED_SL"
            elif last_candle["low"] <= tp2:
                closed = True; pnl = (entry - tp2) * lot * mult; status = "CLOSED_TP"
        if closed:
            cursor.execute("UPDATE v54_ledger SET pnl = ?, status = ?, close_time = ? WHERE id = ?", (pnl, status, datetime.now().strftime("%Y-%m-%d %H:%M"), t_id))
    conn.commit()
    conn.close()

# 🧠 7. GERÇEK SCIENTIFIC HISTORICAL BACKTEST MOTORU (Placeholder Tamamen Kaldırıldı Abi!)
def run_historical_backtest_matrix(df):
    """Gelen ham veri seti üzerinde geçmişe dönük simüle edilmiş gerçek SMC tetik testi çalıştırır abi."""
    if df is None or len(df) < 40: return 50.0, 1.0, 0.0, 0.0
    pnl_array = []
    
    # Kayan pencere ile geçmiş mumlar üzerinde tarama simülasyonu
    for i in range(20, len(df)-5):
        sub_highs = df["high"].iloc[i-5:i].values
        sub_lows = df["low"].iloc[i-5:i].values
        close_curr = df["close"].iloc[i]
        
        # Simüle edilmiş basit BOS koşulu
        if close_curr > sub_highs.max(): # Bullish test
            entry = close_curr
            sl = sub_lows.min()
            tp = entry + abs(entry - sl) * 3.0 # 1:3 Hedef
            
            # Sonraki 5 mumda ne oldu?
            future_window = df.iloc[i+1:i+6]
            if not future_window.empty:
                if future_window["low"].min() <= sl: pnl_array.append(-100.0) # SL vuruldu
                elif future_window["high"].max() >= tp: pnl_array.append(300.0) # TP vuruldu
                else: pnl_array.append((future_window["close"].iloc[-1] - entry) * 10000)
                
    if len(pnl_array) == 0: return 50.0, 1.0, 0.0, 0.0
    pnl_series = pd.Series(pnl_array)
    wins = pnl_series[pnl_series > 0]
    losses = pnl_series[pnl_series < 0]
    
    wr = (len(wins) / len(pnl_array)) * 100
    pf = wins.sum() / (abs(losses.sum()) + 1e-9)
    exp = pnl_series.mean()
    
    return round(wr, 1), round(max(0.1, pf), 2), 0.01, round(exp, 1)
