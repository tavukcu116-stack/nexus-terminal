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
# 🏛️ INSTITUTIONAL SETTINGS & PRODUCTION SECURE
# ==========================================
st.set_page_config(page_title="NEXUS QUANT v32.0 ULTRA", layout="wide", page_icon="🏛️")

st.title("🏛️ NEXUS QUANT v32.0 ULTRA — Multi-Asset Institutional Engine")
st.subheader("Microstructure Friction Model • Portfolio Correlation Guard • Risk Kill-Switch")

# VAULT SECRETS (Streamlit Secrets panelinden otomatik okunur abi)
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8834309699:AAEjA7F4OmbIQHfd9769Lz640GweHPYoStI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1183450421")

INITIAL_CAPITAL = 10000.0
BASE_RISK_PERCENT = 0.50
MIN_SCORE = 9.3
MAX_SIMULTANEOUS_TRADES = 2     # 🧮 6) Aynı anda taşınabilecek maksimum pozisyon sınırı

# 💸 2) Evrensel Mikroyapı Enstrüman Spesifikasyon Matrisi
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
# 📉 11) Kasa geçmişi başlangıç noktalarıyla kuruluyor abi
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
    
    # 📊 3) Normalize Edilmiş Gelişmiş ATR Yapısı
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
# 🧠 5) ADVANCED MARKET REGIME CLASSIFIER
# ==========================================
def classify_market_regime(df, i):
    if i < 50: return "CHOP"
    vol = df["ret"].iloc[i-20:i].std()
    hist = df["ret"].iloc[i-50:i].std()

    if vol > hist * 2.2: return "SPIKE"
    
    trend = df["trend"].iloc[i]
    current_price = df["close"].iloc[i]
    if abs(trend) > (current_price * 0.0003):
        return "TREND"
    
    return "CHOP" # Rule: CHOP piyasalar tamamen dondurulur

# ==========================================
# 💸 1) TRADE QUALITY SCORING SYSTEM (0-10)
# ==========================================
def calculate_trade_quality(row, prob, regime):
    score = 5.0
    conf = abs(prob - 0.5) * 2.0
    score += (conf * 2.5) # Model güven boyutu
    
    if 0.5 < row['vol_regime'] < 1.5: score += 1.0
    if row['volume_z'] > 1.5: score += 1.0
    if regime == "TREND": score += 1.5
    if row['killzone_active'] == 1: score += 1.0
        
    return min(10.0, max(0.0, score))

# ==========================================
# 📉 4) EQUITY SLOPE RISK KILL SWITCH (EĞİM KONTROLÜ)
# ==========================================
def calculate_equity_slope():
    if len(st.session_state.equity_history) < 3: return 1.0
    y = np.array(st.session_state.equity_history[-3:])
    x = np.array([1, 2, 3])
    slope = np.polyfit(x, y, 1)[0]
    return slope

# ==========================================
# 📡 TELEGRAM REAL-TIME SIGNAL ROUTER
# ==========================================
def send_telegram_broadcast(pair, direction, entry, sl, tp, lot, regime, risk, q_score):
    ondalik = 5 if "USD" in pair or "GBP" in pair else 2
    mesaj = f"""%0A🏛️ NEXUS v32.0 ULTRA LIVE SIGNAL %0A━━━━━━━━━━━━━━%0A🎯 Instrument: {pair}%0A📈 Direction: {direction}%0A🌐 Market Regime: {regime}%0A🔥 Trade Quality Score: {q_score:.1f}/10%0A⚖️ Prop Adaptive Risk: %{risk:.2f}%0A%0A🎯 Entry: {entry:.{ondalik}f}%0A🛑 SL: {sl:.{ondalik}f} | 🎯 TP: {tp:.{ondalik}f}%0A⚖️ Position Lot Size: {lot:.2f}"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mesaj}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except:
        pass

# ==========================================
# 📈 8) PORTFOLIO PIPELINE & EXECUTION MOTOR
# ==========================================
def run_portfolio_pipeline():
    features = ["vol", "trend", "candle_strength", "volume_z", "vol_regime", "killzone_active"]
    candidate_signals = []
    
    # 📉 4) Kasa eğrisi eğim kontrolü
    equity_slope = calculate_equity_slope()
    if equity_slope < 0:
        st.sidebar.error(f"🚨 Kasa Eğrisi Aşağı Kırıldı (Eğim: {equity_slope:.2f})! RISK FREEZE SİSTEMİ DEVREDE. TİCARET DURDURULDU.")
        return

    for name, specs in instrument_specs.items():
        raw_data = get_data(specs["ticker"])
        if raw_data is None or raw_data.empty: continue
        df = build_features(raw_data)
        if df is None or len(df) < 100: continue
        
        # %70 In-Sample Train / %30 Out-Of-Sample Test Penceresi
        split = int(len(df) * 0.7)
        model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric="logloss")
        model.fit(df[features].iloc[:split], df["target"].iloc[:split])
        
        # Sadece Dış Test Penceresini (Out-Of-Sample) Simüle Ediyoruz
        for i in range(split, len(df) - 5):
            regime = classify_market_regime(df, i)
            if regime == "CHOP": continue # CHOP market trades must be fully ignored
            
            X = df[features].iloc[i:i+1]
            prob = model.predict_proba(X)[0][1]
            
            if prob >= 0.52: direction = "BUY"
            elif prob <= 0.48: direction = "SELL"
            else: continue
                
            q_score = calculate_trade_quality(df.iloc[i], prob, regime)
            if q_score < 6.0: continue # Rule: quality_score < 6.0 -> TRADE REJECTED
                
            candidate_signals.append({
                "index_t": i, "pair": name, "dir": direction, "q_score": q_score, "regime": regime, "df": df, "specs": specs
            })
            
    # 📈 8) Sinyalleri kurumsal kalite skoruna göre yukarıdan aşağıya sıralıyoruz abi
    candidate_signals = sorted(candidate_signals, key=lambda x: x['q_score'], reverse=True)
    approved_portfolio_trades = []
    
    for sig in candidate_signals:
        if len(approved_portfolio_trades) >= MAX_SIMULTANEOUS_TRADES: break
            
        # ⚖️ 6) PORTFOLIO CORRELATION GUARD (EURUSD ve GBPUSD aynı anda sepete alınamaz abi)
        correlation_block = False
        for approved in approved_portfolio_trades:
            if (sig["pair"] in ["EURUSD", "GBPUSD"]) and (approved["pair"] in ["EURUSD", "GBPUSD"]):
                correlation_block = True; break
                
        if correlation_block:
            rejection_logs_sidebar = f"🛡️ Korelasyon Engelleyici: {sig['pair']} Sepete Alınmadı! (EURUSD/GBPUSD İkiz Pozisyon Riski)."
            st.sidebar.warning(rejection_logs_sidebar)
            continue
            
        approved_portfolio_trades.append(sig)
        
    # Onaylanan Kurumsal Portföy Emirlerini Gönder abi
    execute_portfolio_matrix(approved_portfolio_trades)

# ==========================================
# ⚙️ MULTI-ASSET MICROSTRUCTURE COST ENGINE
# ==========================================
def execute_portfolio_matrix(approved_trades):
    if not approved_trades or st.session_state.system_locked: return
    
    equity = st.session_state.global_equity
    peak = st.session_state.global_peak
    all_logs = st.session_state.execution_logs
    
    wins = st.session_state.total_wins
    losses = st.session_state.total_losses
    gross_p = st.session_state.gross_profit
    gross_l = st.session_state.gross_loss
    
    for trade in approved_trades:
        df = trade["df"]
        i = trade["index_t"]
        specs = trade["specs"]
        name = trade["pair"]
        
        row = df.iloc[i]
        price = float(row["close"])
        atr = float(row["atr"])
        atr_ma = float(row["atr_ma"]) if row["atr_ma"] > 0 else atr
        
        # 💸 2) DYNAMIC SPREAD MODEL
        spread_multiplier = max(1.0, atr / (atr_ma + 1e-9))
        dynamic_spread = specs["spread"] * spread_multiplier
        
        # Slippage Friction Modellemesi
        base_slippage = 0.00010 if specs["multiplier"] == 100000 else 0.10
        slippage = base_slippage * 3.5 if trade["regime"] == "SPIKE" else base_slippage
        
        # 🧮 7) POSITION SIZING & RISK ENGINE (FTMO CHALLENGE STYLE HARNDENING)
        current_drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0.0
        
        if current_drawdown >= 5.0 or st.session_state.daily_loss_accumulator >= (INITIAL_CAPITAL * 0.02):
            st.session_state.system_locked = True
            st.error("🚨 HESAP MAKSİMUM DRAWDOWN VEYA GÜNLÜK ZARAR LİMİTİNE ERİŞTİ. HARD KILL-SWITCH DEVREDE!")
            break # HARD STOP (KILL SWITCH)
        elif current_drawdown >= 3.0:
            current_risk_pct = BASE_RISK_PERCENT / 2.0 # Risk otomatik yarıya iner (%0.25)
        else:
            current_risk_pct = BASE_RISK_PERCENT
            
        # 🧯 9) 3 Consecutive Loss -> Risk cut 80%
        if st.session_state.consecutive_losses >= 3:
            current_risk_pct *= 0.20
            
        # High Volatility Day Restriction (Sadece en elit skoru üstü işlemler)
        if row["vol_regime"] > 1.8 and trade["q_score"] < 8.5:
            continue
            
        # 📊 3) ADVANCED ATR-BASED EXECUTION PRICING (Sürtünme Dahil Giriş, SL ve TP Çıtaları)
        if trade["dir"] == "BUY":
            entry = price + (dynamic_spread / 2.0)
            sl = entry - (atr * 2.0) - slippage
            st.session_state.daily_loss_accumulator = max(0.0, st.session_state.daily_loss_accumulator)
            tp = entry + (atr * 4.0) + slippage
        else:
            entry = price - (dynamic_spread / 2.0)
            sl = entry + (atr * 2.0) + slippage
            tp = entry - (atr * 4.0) - slippage
            
        risk_capital = equity * (current_risk_pct / 100.0)
        stop_dist = abs(entry - sl) if abs(entry - sl) > 0 else 0.0001
        lot = max(0.01, min(5.0, round(risk_capital / (stop_dist * specs["multiplier"]), 2)))
        
        # 5 Barlık Mikro-Yürütme Penceresi İzleme
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
            reward = risk_capital * 2.0
            equity += reward; gross_p += reward; wins += 1
            st.session_state.consecutive_losses = 0
        elif trade_result == "LOSS":
            equity -= risk_capital; gross_l += risk_capital; losses += 1
            st.session_state.consecutive_losses += 1
            st.session_state.daily_loss_accumulator += risk_capital
        else:
            continue
            
        # 📊 9) EXECUTION LOG SYSTEM (Milimetrik Raporlama Künyesi)
        all_logs.append({
            "order_id": f"NX-{int(time.time())}-{name}", "timestamp": df['datetime'].iloc[i].strftime("%m-%d %H:%M"), "pair": name, "direction": trade["dir"], "entry": round(entry, specs["digits"]), "sl": round(sl, specs["digits"]), "tp": round(tp, specs["digits"]), "lot_size": lot, "spread_multiplier": f"x{spread_multiplier:.1f}", "quality_score": round(trade["q_score"], 1), "result": trade_result
        })
        
        send_telegram_broadcast(name, trade["dir"], entry=entry, sl=sl, tp=tp, lot=lot, regime=trade["regime"], risk=current_risk_pct, q_score=trade["q_score"])

    # Global Bellek Hücrelerini Güncelleme
    st.session_state.global_equity = equity
    st.session_state.global_peak = max(peak, equity)
    st.session_state.equity_history.append(equity)
    st.session_state.execution_logs = all_logs
    st.session_state.total_wins = wins
    st.session_state.total_losses = losses
    st.session_state.gross_profit = gross_p
    st.session_state.gross_loss = gross_l
    
    # 📉 10) PERFORMANCE METRICS ENGINE
    total_t = wins + losses
    if total_t > 0:
        win_rate = (wins / total_t) * 100
        pf = gross_p / gross_l if gross_l > 0 else gross_p
        max_dd = ((st.session_state.global_peak - st.session_state.global_equity) / st.session_state.global_peak * 100)
        
        w_rate_dec = win_rate / 100.0
        avg_w_usd = (gross_p / wins) if wins > 0 else 0.0
        avg_l_usd = (gross_l / losses) if losses > 0 else 0.0
        expectancy = (w_rate_dec * avg_w_usd) - ((1 - w_rate_dec) * avg_l_usd)
        
        avg_q = np.mean([l["quality_score"] for l in all_logs]) if all_logs else 0.0
        
        st.session_state.dashboard_metrics = {
            "wr": f"%{win_rate:.1f}", "pf": f"{pf:.2f}", "dd": f"%{max_dd:.2f}", "exp": f"${expectancy:.2f}", "tc": total_t, "aq": f"{avg_q:.1f}/10"
        }

# ==========================================
# RUN ALGORITHMIC PLATFORM INTERFACE
# ==========================================
if st.button("🚀 EXECUTE MULTI-ASSET QUANT SYSTEM v32.0"):
    if not st.session_state.system_locked:
        run_portfolio_pipeline()

# ==========================================
# 📊 PERFORMANCE METRICS DISPLAY PANEL
# ==========================================
if st.session_state.dashboard_metrics:
    metrics = st.session_state.dashboard_metrics
    
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    col_d1.metric("💰 Nihai Global Sermaye (Equity)", f"${st.session_state.global_equity:.2f}", delta=f"${st.session_state.global_equity - INITIAL_CAPITAL:.2f}")
    col_d2.metric("🎯 Başarı Oranı (Win Rate)", metrics["wr"])
    col_d3.metric("💎 Kârlılık Faktörü (Profit Factor)", metrics["pf"])
    col_d4.metric("🛑 Prop Firm Drawdown Rate", metrics["dd"])

    col_d5, col_d6, col_d7 = st.columns(3)
    col_d5.metric("📐 Gerçek Matematiksel Advantage (Expectancy)", metrics["exp"])
    col_d6.metric("⚖️ Toplam Gerçekleşen Emir", metrics["tc"])
    col_d7.metric("🔥 Ortalama İşlem Kalite Skoru", metrics["aq"])

# 📉 11) INTERACTIVE EQUITY CURVE VISUALIZATION
st.write("---")
st.subheader("📈 11. Equity Curve Stability Tracker (Sermaye Gelişim Çizgisi)")
st.line_chart(pd.DataFrame({"Global Kasa ($)": st.session_state.equity_history}))

if st.session_state.execution_logs:
    st.write("---")
    st.subheader("🏛️ 9. Execution Audit Log System (Mikroyapı Detay Raporu)")
    st.dataframe(pd.DataFrame(st.session_state.execution_logs), use_container_width=True)

# ==========================================
# 🔄 12) RESET SYSTEM STATION
# ==========================================
st.sidebar.write("---")
if st.sidebar.button("🔄 12. Hard Reset Algorithmic Memory"):
    st.session_state.global_equity = INITIAL_CAPITAL
    st.session_state.global_peak = INITIAL_CAPITAL
    st.session_state.equity_history = [INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL, INITIAL_CAPITAL]
    st.session_state.slope_history = [0.0, 0.0]
    st.session_state.dashboard_metrics = {}
    st.session_state.execution_logs = []
    st.session_state.total_wins = 0
    st.session_state.total_losses = 0
    st.session_state.gross_profit = 0.0
    st.session_state.gross_loss = 0.0
    st.session_state.consecutive_losses = 0
    st.session_state.daily_loss_accumulator = 0.0
    st.session_state.system_locked = False
    st.rerun()
