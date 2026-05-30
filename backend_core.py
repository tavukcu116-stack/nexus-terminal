import os
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "nexus_vault.db"
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "MOCK_KEY")

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def init_enterprise_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, asset TEXT, type TEXT, entry REAL, sl REAL, 
            tp1 REAL, tp2 REAL, lot REAL, pnl REAL, status TEXT, max_seen REAL, session TEXT
        )
    """)
    conn.commit()
    conn.close()

init_enterprise_db()

def check_macro_news_impact():
    try:
        url = f"https://api.twelvedata.com/economic_calendar?apikey={TWELVE_DATA_KEY}"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla"}).json()
        if "economic_calendar" in r:
            critical_events = ["CPI", "NFP", "FOMC", "Interest Rate", "Powell"]
            for event in r["economic_calendar"][:15]:
                if any(crit in event["event"] for crit in critical_events) and event["importance"] == "High":
                    return True, f"BLOCK: HIGH IMPACT NEWS RISK ({event['event']})"
        return False, "NEWS GATES CLEAR"
    except:
        return False, "NEWS OFFLINE - SAFE DEFAULTS"

def calculate_market_regime(df, symbol):
    if df is None or len(df) < 30: return "RANGE", 0.0005, 0.4
    close = df["close"]
    ma_fast = close.rolling(10).mean().iloc[-1]
    ma_slow = close.rolling(30).mean().iloc[-1]
    regime = "TREND" if abs(ma_fast - ma_slow) > (close.iloc[-1] * 0.0008) else "RANGE"
    atr = (df["high"] - df["low"]).rolling(14).mean().iloc[-1]
    
    try:
        spread_url = f"https://api.twelvedata.com/quotes?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        sq = requests.get(spread_url, timeout=4).json()
        bid = float(sq.get("bid", close.iloc[-1]))
        ask = float(sq.get("ask", close.iloc[-1]))
        spread = abs(ask - bid) * (10000 if "USD" in symbol and "XAU" not in symbol else 10)
    except:
        spread = 0.4
        
    return regime, atr, spread

def process_smc_liquidity_matrix(df_15m, df_1h, df_4h):
    if df_15m is None or len(df_15m) < 40: return "WAIT", 0, 0, False, False
    idx = len(df_15m) - 1
    close_p = df_15m["close"].iloc[idx]
    high_p = df_15m["high"].iloc[idx]
    low_p = df_15m["low"].iloc[idx]
    
    htf_bias = "WAIT"
    if df_4h is not None and df_1h is not None:
        if df_4h["close"].iloc[-1] > df_4h["close"].rolling(10).mean().iloc[-1] and df_1h["close"].iloc[-1] > df_1h["close"].rolling(10).mean().iloc[-1]:
            htf_bias = "BULLISH"
        elif df_4h["close"].iloc[-1] < df_4h["close"].rolling(10).mean().iloc[-1] and df_1h["close"].iloc[-1] < df_1h["close"].rolling(10).mean().iloc[-1]:
            htf_bias = "BEARISH"

    sh, sl = [], []
    for i in range(4, len(df_15m) - 4):
        if df_15m["high"].iloc[i] == max(df_15m["high"].iloc[i-4 : i+5]): sh.append(df_15m["high"].iloc[i])
        if df_15m["low"].iloc[i] == min(df_15m["low"].iloc[i-4 : i+5]): sl.append(df_15m["low"].iloc[i])
        
    last_sh = sh[-1] if sh else df_15m["high"].max()
    last_sl = sl[-1] if sl else df_15m["low"].min()
    
    sweep_detected = (high_p > last_sh and close_p < last_sh) or (low_p < last_sl and close_p > last_sl)
    body_avg = abs(df_15m["close"] - df_15m["open"]).tail(20).mean()
    displacement = abs(close_p - df_15m["open"].iloc[idx]) > body_avg * 1.6
    
    return htf_bias, last_sh, last_sl, sweep_detected, displacement

def manage_enterprise_positions(asset, current_df):
    if current_df is None or current_df.empty: return
    last_candle = current_df.iloc[-1]
    current_price = last_candle["close"]
    c_high = last_candle["high"]
    c_low = last_candle["low"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, entry, sl, tp2, lot, max_seen FROM enterprise_journal WHERE asset = ? AND status = 'OPEN'", (asset,))
    trades = cursor.fetchall()
    
    for t in trades:
        t_id, t_type, entry, sl, tp2, lot, max_seen = t
        closed = False
        pnl = 0.0
        status = "OPEN"
        
        if t_type == "BUY":
            new_max = max(max_seen, current_price)
            if current_price > max_seen:
                cursor.execute("UPDATE enterprise_journal SET max_seen = ? WHERE id = ?", (new_max, t_id))
            if c_low <= sl:
                closed = True; pnl = (sl - entry) * lot * (100 if "XAU" in asset else 10000); status = "CLOSED_SL"
            elif c_high >= tp2:
                closed = True; pnl = (tp2 - entry) * lot * (100 if "XAU" in asset else 10000); status = "CLOSED_TP"
        elif t_type == "SELL":
            new_max = min(max_seen, current_price) if max_seen > 0 else current_price
            if current_price < max_seen or max_seen == 0:
                cursor.execute("UPDATE enterprise_journal SET max_seen = ? WHERE id = ?", (new_max, t_id))
            if c_high >= sl:
                closed = True; pnl = (entry - sl) * lot * (100 if "XAU" in asset else 10000); status = "CLOSED_SL"
            elif c_low <= tp2:
                closed = True; pnl = (entry - tp2) * lot * (100 if "XAU" in asset else 10000); status = "CLOSED_TP"
                
        if closed:
            cursor.execute("UPDATE enterprise_journal SET pnl = ?, status = ? WHERE id = ?", (pnl, status, t_id))
            
    conn.commit()
    conn.close()
  
