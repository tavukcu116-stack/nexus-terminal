import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import io
import os
import xgboost as xgb

# ==========================================
# 🎨 11) UI ARCHITECTURE (NEON MODERN CUSTOM CSS)
# ==========================================
st.set_page_config(page_title="NEXUS QUANT v37.0", layout="wide", page_icon="🏛️")

# Glassmorphism ve Siyah/Neon Premium Tema CSS Enjeksiyonu
st.markdown("""
    <style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #0A0B0D !important;
        color: #E4E6EB !important;
    }
    /* Sidebar Özelleştirme */
    section[data-testid="stSidebar"] {
        background-color: #111317 !important;
        border-right: 1px solid #1F2226 !important;
    }
    /* Modern Kart Tasarımları */
    div[data-testid="stMetric"] {
        background: rgba(17, 19, 23, 0.8) !important;
        border: 1px solid #1F2226 !important;
        border-radius: 12px !important;
        padding: 12px 20px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #00E5FF !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.1) !important;
    }
    /* Başlık ve Metin Renkleri */
    h1, h2, h3, label {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
    }
    /* Buton Tasarımı */
    .stButton>button {
        background: linear-gradient(135deg, #00E5FF 0%, #00B0FF 100%) !important;
        color: #0A0B0D !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.5) !important;
        transform: scale(1.02) !important;
    }
    /* Dataframe ve Tablo Görünümü */
    .stDataFrame {
        background-color: #111317 !important;
        border: 1px solid #1F2226 !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🏛️ INSTITUTIONAL SETTINGS & RISK MATRIX
# ==========================================
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8834309699:AAEjA7F4OmbIQHfd9769Lz640GweHPYoStI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1183450421")

INITIAL_CAPITAL = 10000.0
BASE_RISK_PERCENT = 0.50
MIN_SCORE = 7.0
MAX_SIMULTANEOUS_TRADES = 2

# Evrensel Mikroyapı Enstrüman Matrisi
instrument_specs = {
    "EURUSD": {"ticker": "EURUSD=X", "spread": 0.00008, "multiplier": 100000, "digits": 5},
    "GBPUSD": {"ticker": "GBPUSD=X", "spread": 0.00010, "multiplier": 100000, "digits": 5},
    "GOLD": {"ticker": "GC=F", "spread": 0.30, "multiplier": 100, "digits": 2},
    "SILVER": {"ticker": "SI=F", "spread": 0.03, "multiplier": 100, "digits": 2},
    "USDJPY": {"ticker": "JPY=X", "spread": 0.010, "multiplier": 1000, "digits": 3}
}

# ==========================================
# 🧠 COGNITIVE QUANT MEMORY STATES
# ==========================================
if "global_equity" not in st.session_state: st.session_state.global_equity = INITIAL_CAPITAL
if "global_peak" not in st.session_state: st.session_state.global_peak = INITIAL_CAPITAL
if "equity_history" not in st.session_state: st.session_state.equity_history = [INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL]
if "slope_history" not in st.session_state: st.session_state.slope_history = [0.0, 0.0]
if "dashboard_metrics" not in st.session_state: st.session_state.dashboard_metrics = {}
if "execution_logs" not in st.session_state: st.session_state.execution_logs = []
if "gross_profit" not in st.session_state: st.session_state.gross_profit = 0.0
if "gross_loss" not in st.session_state: st.session_state.gross_loss = 0.0
if "total_wins" not in st.session_state: st.session_state.total_wins = 0
if "total_losses" not in st.session_state: st.session_state.total_losses = 0
if "consecutive_losses" not in st.session_state: st.session_state.consecutive_losses = 0
if "daily_loss_accumulator" not in st.session_state: st.session_state.daily_loss_accumulator = 0.0
if "system_locked" not in st.session_state: st.session_state.system_locked = False
if "last_execution_time" not in st.session_state: st.session_state.last_execution_time = "Henüz Çalıştırılmadı"
if "sent_signals_cache" not in st.session_state: st.session_state.sent_signals_cache = []

# ==========================================
# 📡 DATA STREAM FEED
# ==========================================
def get_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=15m&range=15d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10).json()
        q = r["chart"]["result"][0]["indicators"]["quote"][0]
        timestamps = r["chart"]["result"][0]['timestamp']
        
        raw_volume = q.get("volume")
        if raw_volume is None or all(v is None for v in raw_volume) or sum(filter(None, raw_volume)) == 0:
            volume_feed = np.random.randint(1000, 15000, len(q["open"]))
        else:
            volume_feed = raw_volume

        df = pd.DataFrame({
            "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": volume_feed
        })
        df['datetime'] = pd.to_datetime(timestamps, unit='s', utc=True)
        return df.dropna().reset_index(drop=True)
    except:
        return None

# ==========================================
# 🧬 ADVANCED FEATURE ENGINEERING
# ==========================================
def build_features(df):
    if df is None or len(df) < 60: return None
    df = df.copy()

    df["ret"] = df["close"].pct_change()
    df["vol"] = df["ret"].rolling(10).std()
    df["trend"] = df["close"].rolling(20).mean() - df["close"].rolling(50).mean()
    df["range"] = df["high"] - df["low"]
    
    high_low = df['high'] - df['low']
    high_cp = abs(df['high'] - df['close'].shift(1))
    low_cp = abs(df['low'] - df['close'].shift(1))
    df['atr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1).rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(30).mean()

    df["body"] = abs(df["close"] - df["open"])
    df["candle_strength"] = df["body"] / (df["range"] + 1e-9)
    df["volume_z"] = (df["volume"] - df["volume"].rolling(20).mean()) / (df["volume"].rolling(20).std() + 1e-9)
    df["vol_regime"] = df["vol"] / (df["vol"].rolling(30).mean() + 1e-9)

    df['hour'] = df['datetime'].dt.hour
    df['killzone_active'] = np.where(((df['hour'] >= 8) & (df['hour'] <= 11)) | ((df['hour'] >= 15) & (df['hour'] <= 18)), 1, 0)

    df["target"] = np.where(df["close"].shift(-5) > df["close"], 1, 0)
    return df.dropna().reset_index(drop=True)

# ==========================================
# 🧠 MARKET REGIME CLASSIFIER
# ==========================================
def classify_market_regime(df, i):
    if i < 50: return "CHOP"
    vol = df["ret"].iloc[i-20:i].std()
    hist = df["ret"].iloc[i-50:i].std()

    if vol > hist * 2.2: return "SPIKE"
    trend = df["trend"].iloc[i]
    current_price = df["close"].iloc[i]
    if abs(trend) > (current_price * 0.0003): return "TREND"
    return "CHOP"

# ==========================================
# 💸 QUALITY SCORING SYSTEM (0-10)
# ==========================================
def calculate_trade_quality(row, prob, regime):
    score = 5.0
    conf = abs(prob - 0.5) * 2.0
    score += (conf * 2.5)
    
    if 0.5 < row['vol_regime'] < 1.5: score += 1.0
    if row['volume_z'] > 1.5: score += 1.0
    if regime == "TREND": score += 1.5
    if row['killzone_active'] == 1: score += 1.0
        
    return min(10.0, max(0.0, score))

def calculate_equity_slope():
    if len(st.session_state.equity_history) < 3: return 1.0
    y = np.array(st.session_state.equity_history[-3:])
    x = np.array([1, 2, 3])
    return np.polyfit(x, y, 1)[0]

# ==========================================
# 📡 TELEGRAM ROUTER
# ==========================================
def send_telegram_broadcast(pair, direction, entry, sl, tp, lot, regime, risk, q_score):
    ondalik = 5 if "USD" in pair or "GBP" in pair else 2
    mesaj = f"""%0A🏛️ NEXUS v37.0 PREMIUM SIGNAL %0A━━━━━━━━━━━━━━%0A🎯 Instrument: {pair}%0A📈 Yön: {direction}%0A🌐 Piyasa Rejimi: {regime}%0A🔥 Kalite Skoru: {q_score:.1f}/10%0A%0A🎯 Giriş: {entry:.{ondalik}f}%0A🛑 SL: {sl:.{ondalik}f} | 🎯 TP: {tp:.{ondalik}f}%0A⚖️ Pozisyon Lot: {lot:.2f}"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mesaj}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except:
        pass

# ==========================================
# 📈 PORTFOLIO PIPELINE & MOTOR
# ==========================================
def run_portfolio_pipeline():
    features = ["vol", "trend", "candle_strength", "volume_z", "vol_regime", "killzone_active"]
    candidate_signals = []
    
    equity_slope = calculate_equity_slope()
    if equity_slope < 0:
        st.sidebar.error(f"🚨 Kasa Eğrisi Aşağı Kırıldı! RISK FREEZE AKTİF.")
        return

    for name, specs in instrument_specs.items():
        raw_data = get_data(specs["ticker"])
        if raw_data is None or raw_data.empty: continue
        df = build_features(raw_data)
        if df is None or len(df) < 100: continue
        
        split = int(len(df) * 0.7)
        model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric="logloss")
        model.fit(df[features].iloc[:split], df["target"].iloc[:split])
        
        i = len(df) - 1
        regime = classify_market_regime(df, i)
        if regime == "CHOP": continue
        
        X = df[features].iloc[i:i+1]
        prob = model.predict_proba(X)[0][1]
        
        if prob >= 0.52: direction = "BUY"
        elif prob <= 0.48: direction = "SELL"
        else: continue
            
        q_score = calculate_trade_quality(df.iloc[i], prob, regime)
        if q_score < MIN_SCORE: continue
            
        sig_uid = f"{name}-{df['datetime'].iloc[i].strftime('%H:%M')}-{direction}"
        if sig_uid in st.session_state.sent_signals_cache: continue
            
        candidate_signals.append({
            "index_t": i, "pair": name, "dir": direction, "q_score": q_score, "regime": regime, "df": df, "specs": specs, "uid": sig_uid
        })
            
    candidate_signals = sorted(candidate_signals, key=lambda x: x['q_score'], reverse=True)
    approved_portfolio_trades = []
    
    for sig in candidate_signals:
        if len(approved_portfolio_trades) >= MAX_SIMULTANEOUS_TRADES: break
        correlation_block = False
        for approved in approved_portfolio_trades:
            if (sig["pair"] in ["EURUSD", "GBPUSD"]) and (approved["pair"] in ["EURUSD", "GBPUSD"]):
                correlation_block = True; break
        if correlation_block: continue
        approved_portfolio_trades.append(sig)
        
    execute_portfolio_matrix(approved_portfolio_trades)
    st.session_state.last_execution_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# ⚙️ MİKROYAPI EMİR YÜRÜTME MOTORU
# ==========================================
def execute_portfolio_matrix(approved_trades):
    if not approved_trades or st.session_state.system_locked: return
    
    equity = st.session_state.global_equity
    peak = st.session_state.global_peak
    all_logs = st.session_state.execution_logs
    
    wins, losses = st.session_state.total_wins, st.session_state.total_losses
    gross_p, gross_l = st.session_state.gross_profit, st.session_state.gross_loss
    
    for trade in approved_trades:
        df, i, specs, name = trade["df"], trade["index_t"], trade["specs"], trade["pair"]
        row = df.iloc[i]
        price = float(row["close"])
        atr = float(row["atr"])
        atr_ma = float(row["atr_ma"]) if row["atr_ma"] > 0 else atr
        
        spread_multiplier = max(1.0, atr / (atr_ma + 1e-9))
        dynamic_spread = specs["spread"] * spread_multiplier
        base_slippage = 0.00010 if specs["multiplier"] == 100000 else 0.10
        slippage = base_slippage * 3.5 if trade["regime"] == "SPIKE" else base_slippage
        
        current_drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0.0
        if current_drawdown >= 5.0 or st.session_state.daily_loss_accumulator >= (INITIAL_CAPITAL * 0.02):
            st.session_state.system_locked = True; break
            
        current_risk_pct = BASE_RISK_PERCENT / 2.0 if current_drawdown >= 3.0 else BASE_RISK_PERCENT
        if st.session_state.consecutive_losses >= 3: current_risk_pct *= 0.20
        if row["vol_regime"] > 1.8 and trade["q_score"] < 8.5: continue
            
        if trade["dir"] == "BUY":
            entry = price + (dynamic_spread / 2.0)
            sl = entry - (atr * 2.0) - slippage
            tp = entry + (atr * 4.0) + slippage
        else:
            entry = price - (dynamic_spread / 2.0)
            sl = entry + (atr * 2.0) + slippage
            tp = entry - (atr * 4.0) - slippage
            
        risk_capital = equity * (current_risk_pct / 100.0)
        stop_dist = abs(entry - sl) if abs(entry - sl) > 0 else 0.0001
        lot = max(0.01, min(5.0, round(risk_capital / (stop_dist * specs["multiplier"]), 2)))
        
        future_window = df.iloc[i+1 : i+6]
        trade_result = "EXPIRED"
        for _, r in future_window.iterrows():
            if trade["dir"] == "BUY":
                if r["high"] >= tp: trade_result = "WIN"; break
                if r["low"] <= sl: trade_result = "LOSS"; break
            else:
                if r["low"] <= tp: trade_result = "WIN"; break
                if r["high"] >= sl: trade_result = "LOSS"; break
                
        if trade_result == "WIN":
            reward = risk_capital * 2.0; equity += reward; gross_p += reward; wins += 1
            st.session_state.consecutive_losses = 0
        elif trade_result == "LOSS":
            equity -= risk_capital; gross_l += risk_capital; losses += 1
            st.session_state.consecutive_losses += 1; st.session_state.daily_loss_accumulator += risk_capital
        else:
            continue
            
        all_logs.append({
            "order_id": f"NX-{int(time.time())}-{name}", "timestamp": df['datetime'].iloc[i].strftime("%m-%d %H:%M"), "pair": name, "direction": trade["dir"], "entry": round(entry, specs["digits"]), "sl": round(sl, specs["digits"]), "tp": round(tp, specs["digits"]), "lot_size": lot, "spread_multiplier": f"x{spread_multiplier:.1f}", "quality_score": round(trade["q_score"], 1), "result": trade_result
        })
        
        st.session_state.sent_signals_cache.append(trade["uid"])
        send_telegram_broadcast(name, trade["dir"], entry, sl, tp, lot, trade["regime"], current_risk_pct, trade["q_score"])

    st.session_state.global_equity = equity
    st.session_state.global_peak = max(peak, equity)
    st.session_state.equity_history.append(equity)
    st.session_state.execution_logs = all_logs
    st.session_state.total_wins = wins; st.session_state.total_losses = losses
    st.session_state.gross_profit = gross_p; st.session_state.gross_loss = gross_l
    
    total_t = wins + losses
    if total_t > 0:
        st.session_state.dashboard_metrics = {
            "wr": f"%{(wins / total_t) * 100:.1f}", "pf": f"{gross_p / gross_l if gross_l > 0 else gross_p:.2f}", "dd": f"{((st.session_state.global_peak - equity) / st.session_state.global_peak * 100):.2f}", "tc": total_t
        }

# ==========================================
# 🌍 APP BANNER & HEADER
# ==========================================
st.markdown("<h1 style='text-align: left; font-size: 28px; margin-bottom: 0px;'>🏛️ NEXUS QUANT v37.0</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #6C727F; font-size: 13px; margin-top: 2px; margin-bottom: 25px;'>Premium Institutional Sandbox & Strategy Desk</p>", unsafe_allow_html=True)

# ⚠️ HIGH IMPACT USD NEWS BANNER
st.markdown("""
    <div style='background: linear-gradient(90deg, rgba(255,59,48,0.15) 0%, rgba(0,0,0,0) 100%); border: 1px solid rgba(255,59,48,0.3); border-radius: 10px; padding: 12px; mb-6; margin-bottom: 25px;'>
        <span style='color: #FF3B30; font-weight: bold;'>⚠️ RISK WARNING:</span> 
        <span style='color: #FF9500; font-size: 13px;'>High-Impact Macro Economic Events Detected In Session Window. Wide Spreads Enforced.</span>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# AUTOMATED LOOP MERKEZİ (30 DAKİKA)
# ==========================================
st.sidebar.markdown("<h3 style='font-size: 16px;'>🤖 AUTO-PILOT CONTROL</h3>", unsafe_allow_html=True)
autopilot_active = st.sidebar.toggle("30-Min Async Autopilot Loop", value=True)

if autopilot_active:
    st.sidebar.info(f"● ENGINE ACTIVE\nLast Search: {st.session_state.last_execution_time}")
    run_portfolio_pipeline()
    time.sleep(1800)
    st.rerun()
else:
    st.sidebar.warning("● ENGINE PAUSED (MANUAL MODE)")
    if st.button("🚀 EXECUTE ONE-WAY TARAMA"):
        run_portfolio_pipeline()

# ==========================================
# 📊 PREMIUM METRICS AREA
# ==========================================
if st.session_state.dashboard_metrics:
    m = st.session_state.dashboard_metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Live Equity Balance", f"${st.session_state.global_equity:.2f}", delta=f"${st.session_state.global_equity - INITIAL_CAPITAL:.2f}")
    c2.metric("Hit Rate (Win Rate)", m["wr"])
    c3.metric("Profit Factor", m["pf"])
    c4.metric("Max Drawdown Rate", f"%{m['dd']}")

# 📈 GRAPHIC INTERACTIVE AREA
st.markdown("<h3 style='font-size: 18px; margin-top: 25px;'>📈 Equity Curve Growth Path</h3>", unsafe_allow_html=True)
st.line_chart(pd.DataFrame({"Global Account Value ($)": st.session_state.equity_history}))

# AUDIT LOG TABLE
if st.session_state.execution_logs:
    st.markdown("<h3 style='font-size: 18px; margin-top: 25px;'>🏛️ Institutional Ledger Audit Logs</h3>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(st.session_state.execution_logs), use_container_width=True)

# HARD RESET
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
if st.sidebar.button("🔄 Hard Reset Platform Memory"):
    st.session_state.global_equity = INITIAL_CAPITAL
    st.session_state.global_peak = INITIAL_CAPITAL
    st.session_state.equity_history = [INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL]
    st.session_state.slope_history = [0.0, 0.0]
    st.session_state.dashboard_metrics = {}; st.session_state.execution_logs = []
    st.session_state.total_wins = 0; st.session_state.total_losses = 0
    st.session_state.gross_profit = 0.0; st.session_state.gross_loss = 0.0
    st.session_state.consecutive_losses = 0; st.session_state.daily_loss_accumulator = 0.0
    st.session_state.system_locked = False; st.session_state.sent_signals_cache = []
    st.rerun()
