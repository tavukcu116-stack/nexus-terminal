# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v50.0 - FIX EDITION)
# ==========================================
import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timezone
import sqlite3
from streamlit_autorefresh import st_autorefresh

# ⏳ AUTO REFRESH (15 Saniyede bir arka planı göz kırpmadan yeniler abi)
st_autorefresh(interval=15000, key="nexus_enterprise_refresh")

# ==========================================
# 🎨 MINIMALIST TRADINGVIEW DARK STYLE SHEET
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] {
        background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 10px !important;
    }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 12px; margin-bottom: 10px; }
    .critical-node { border: 1px solid #ef5350; background: rgba(239,83,80,0.03); padding: 10px; border-radius: 4px; color: #ef5350; font-family: monospace; font-size:12px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🗄️ INTERNAL DATABASE ENGINE (SQLITE ARCHITECTURE)
# ==========================================
DB_FILE = "nexus_vault.db"

def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, asset TEXT, type TEXT, entry REAL, sl REAL, tp REAL, lot REAL, pnl REAL, status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_database()

# ==========================================
# 📡 STABLE BUFFERED STREAM & CACHE MODULE
# ==========================================
TWELVE_DATA_API_KEY = "YOUR_TWELVE_DATA_API_KEY"

if "http_session" not in st.session_state:
    st.session_state.http_session = requests.Session()

@st.cache_data(ttl=30)
def fetch_raw_market_candles(symbol, interval="15min", outputsize="80"):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_API_KEY}"
        r = st.session_state.http_session.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"}).json()
        if "values" not in r: return None
        df = pd.DataFrame(r["values"])
        for col in ["open", "high", "low", "close"]: df[col] = df[col].astype(float)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df.iloc[::-1].reset_index(drop=True)
    except:
        return None

# ==========================================
# 🧠 COGNITIVE SMC CORE CORE ENGINE
# ==========================================
def extract_pure_smc_matrix(symbol):
    df_4h = fetch_raw_market_candles(symbol, "4h", "20")
    df_1h = fetch_raw_market_candles(symbol, "1h", "20")
    df_15m = fetch_raw_market_candles(symbol, "15min", "80")
    
    if df_15m is None or len(df_15m) < 40: return None
    
    df_15m['hour'] = df_15m['datetime'].dt.hour
    idx = len(df_15m) - 1
    
    close_p = df_15m["close"].iloc[idx]
    high_p = df_15m["high"].iloc[idx]
    low_p = df_15m["low"].iloc[idx]
    
    htf_bias = "WAIT"
    if df_4h is not None and df_1h is not None:
        ma_4h = df_4h["close"].rolling(10).mean().iloc[-1]
        ma_1h = df_1h["close"].rolling(10).mean().iloc[-1]
        if df_4h["close"].iloc[-1] > ma_4h and df_1h["close"].iloc[-1] > ma_1h: htf_bias = "BULLISH"
        elif df_4h["close"].iloc[-1] < ma_4h and df_1h["close"].iloc[-1] < ma_1h: htf_bias = "BEARISH"

    sh, sl = [], []
    for i in range(4, len(df_15m) - 4):
        if df_15m["high"].iloc[i] == max(df_15m["high"].iloc[i-4 : i+5]): sh.append((i, df_15m["high"].iloc[i], df_15m["datetime"].iloc[i]))
        if df_15m["low"].iloc[i] == min(df_15m["low"].iloc[i-4 : i+5]): sl.append((i, df_15m["low"].iloc[i], df_15m["datetime"].iloc[i]))
        
    last_sh = sh[-1] if sh else (idx-10, df_15m["high"].max(), df_15m["datetime"].iloc[idx-10])
    last_sl = sl[-1] if sl else (idx-15, df_15m["low"].min(), df_15m["datetime"].iloc[idx-15])
    
    pdh = df_15m["high"].max()
    pdl = df_15m["low"].min()
    midpoint = (pdh + pdl) / 2
    
    body_sizes = abs(df_15m["close"] - df_15m["open"])
    avg_body = body_sizes.tail(20).mean()
    displacement = body_sizes.iloc[idx] > avg_body * 1.6
    
    current_hour = datetime.utcnow().hour
    killzone_safe = (8 <= current_hour < 12) or (13 <= current_hour < 17)
    
    sweep_detected = False
    if high_p > last_sh[1] and close_p < last_sh[1]: sweep_detected = True
    elif low_p < last_sl[1] and close_p > last_sl[1]: sweep_detected = True

    active_ob = None
    if sweep_detected and displacement:
        for i in range(idx-10, idx):
            if df_15m["close"].iloc[i] < df_15m["open"].iloc[i]:
                active_ob = {"type": "BULLISH OB", "y0": df_15m["low"].iloc[i], "y1": df_15m["high"].iloc[i], "t0": df_15m["datetime"].iloc[i]}
            else:
                active_ob = {"type": "BEARISH OB", "y0": df_15m["low"].iloc[i], "y1": df_15m["high"].iloc[i], "t0": df_15m["datetime"].iloc[i]}

    active_fvg = None
    for i in range(idx-10, idx):
        gap_bull = df_15m["low"].iloc[i] - df_15m["high"].iloc[i-2]
        gap_bear = df_15m["low"].iloc[i-2] - df_15m["high"].iloc[i]
        if gap_bull > (close_p * 0.0003) and df_15m["low"].iloc[i:idx+1].min() > df_15m["high"].iloc[i-2]:
            active_fvg = {"type": "BULLISH FVG", "y0": df_15m["high"].iloc[i-2], "y1": df_15m["low"].iloc[i], "t0": df_15m["datetime"].iloc[i-2]}
        elif gap_bear > (close_p * 0.0003) and df_15m["high"].iloc[i:idx+1].max() < df_15m["low"].iloc[i-2]:
            active_fvg = {"type": "BEARISH FVG", "y0": df_15m["low"].iloc[i], "y1": df_15m["high"].iloc[i-2], "t0": df_15m["datetime"].iloc[i-2]}

    bias = "WAIT"
    entry, sl, tp, rr_ratio = 0.0, 0.0, 0.0, 0.0
    atr = (df_15m["high"] - df_15m["low"]).rolling(14).mean().iloc[-1]
    
    if killzone_safe and htf_bias != "WAIT":
        if htf_bias == "BULLISH" and close_p < midpoint:
            retest_fvg = (active_fvg is not None and close_p <= active_fvg["y1"])
            retest_ob = (active_ob is not None and close_p <= active_ob["y1"])
            if retest_fvg or retest_ob or sweep_detected:
                bias = "BUY"; entry = close_p; sl = last_sl[1] - (atr * 0.3); tp = last_sh[1]
        elif htf_bias == "BEARISH" and close_p > midpoint:
            retest_fvg = (active_fvg is not None and close_p >= active_fvg["y0"])
            retest_ob = (active_ob is not None and close_p >= active_ob["y0"])
            if retest_fvg or retest_ob or sweep_detected:
                bias = "SELL"; entry = close_p; sl = last_sh[1] + (atr * 0.3); tp = last_sl[1]

    if entry > 0:
        rr_ratio = abs(entry - tp) / (abs(entry - sl) + 1e-9)
        if rr_ratio < 1.5: bias = "WAIT"

    return {
        "df": df_15m, "price": close_p, "midpoint": midpoint, "last_sh": last_sh, "last_sl": last_sl,
        "pdh": pdh, "pdl": pdl, "ob": active_ob, "fvg": active_fvg, "bias": bias,
        "entry": entry, "sl": sl, "tp": tp, "rr": rr_ratio, "htf": htf_bias, "kz": killzone_safe
    }

# ==========================================
# 📊 AUTOMATED ONSITE PAPER TRADING REALITY MOTOR
# ==========================================
def process_live_execution_tracking(asset_name, current_df):
    if current_df is None or current_df.empty: return
    last_candle = current_df.iloc[-1]
    c_high = last_candle["high"]
    c_low = last_candle["low"]
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.connect().cursor() if hasattr(sqlite3.connect(DB_FILE), 'connect') else conn.cursor()
    
    cursor.execute("SELECT id, type, entry, sl, tp, lot FROM journal WHERE asset = ? AND status = 'OPEN'", (asset_name,))
    open_trades = cursor.fetchall()
    
    for trade in open_trades:
        t_id, t_type, t_entry, t_sl, t_tp, t_lot = trade
        closed = False
        final_pnl = 0.0
        outcome = "OPEN"
        
        if t_type == "BUY":
            if c_low <= t_sl:
                closed = True; final_pnl = (t_sl - t_entry) * t_lot * 10000; outcome = "STOP LOSS"
            elif c_high >= t_tp:
                closed = True; final_pnl = (t_tp - t_entry) * t_lot * 10000; outcome = "TAKE PROFIT"
        elif t_type == "SELL":
            if c_high >= t_sl:
                closed = True; final_pnl = (t_entry - t_sl) * t_lot * 10000; outcome = "STOP LOSS"
            elif c_low <= t_tp:
                closed = True; final_pnl = (t_entry - t_tp) * t_lot * 10000; outcome = "TAKE PROFIT"
                
        if closed:
            cursor.execute("UPDATE journal SET pnl = ?, status = ? WHERE id = ?", (final_pnl, outcome, t_id))
            
    conn.commit()
    conn.close()

# ==========================================
# 📊 ANA GÖRSELLEŞTİRME PANELİ
# ==========================================
def render_pure_production_desk(m_name, symbol):
    smc = extract_pure_smc_matrix(symbol)
    if smc is None:
        st.error(f"{m_name} Buffer stream failed.")
        return
        
    df = smc["df"]
    process_live_execution_tracking(m_name, df)
    
    if not smc["kz"]: 
        st.markdown("<div class='critical-node'>⏸️ EXECUTION SUSPENDED — OUTSIDE RECOGNIZED KILLZONE HOURS</div><br>", unsafe_allow_html=True)
    
    col_chart, col_desk = st.columns([3, 1])
    
    with col_chart:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Live Execution Price", f"{smc['price']}")
        c2.metric("HTF Alignment Bias", smc['htf'])
        c3.metric("Calculated RR Ratio", f"1:{smc['rr']:.2f}" if smc['rr'] > 0 else "0.0")
        c4.metric("Current Regime", "STRUCTURE ALIGNED" if smc['bias'] != "WAIT" else "CONGESTION")
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', name=m_name
        ))
        fig.update_traces(whiskerwidth=0.3)
        
        fig.add_hline(y=smc['pdh'], line_color="rgba(255, 235, 59, 0.2)", line_width=1, annotation_text="PDH")
        fig.add_hline(y=smc['pdl'], line_color="rgba(255, 235, 59, 0.2)", line_width=1, annotation_text="PDL")
        
        fig.add_shape(type="line", x0=smc['last_sh'][2], x1=df['datetime'].iloc[-1], y0=smc['last_sh'][1], y1=smc['last_sh'][1], line=dict(color="#ef5350", width=1, dash="dot"))
        fig.add_shape(type="line", x0=smc['last_sl'][2], x1=df['datetime'].iloc[-1], y0=smc['last_sl'][1], y1=smc['last_sl'][1], line=dict(color="#26a69a", width=1, dash="dot"))

        if smc["ob"]:
            ob_color = "rgba(38, 166, 154, 0.04)" if "BULLISH" in smc["ob"]["type"] else "rgba(239, 83, 80, 0.04)"
            fig.add_shape(type="rect", x0=smc["ob"]["t0"], x1=df['datetime'].iloc[-1], y0=smc["ob"]["y0"], y1=smc["ob"]["y1"], fillcolor=ob_color, line_width=0)

        if smc["fvg"]:
            fvg_color = "rgba(41, 98, 255, 0.03)" if "BULLISH" in smc["fvg"]["type"] else "rgba(255, 109, 0, 0.03)"
            fig.add_shape(type="rect", x0=smc["fvg"]["t0"], x1=df['datetime'].iloc[-1], y0=smc["fvg"]["y0"], y1=smc["fvg"]["y1"], fillcolor=fvg_color, line_width=0)

        if smc["bias"] != "WAIT":
            fig.add_hline(y=smc["entry"], line_color="#2962ff", line_width=1.5, annotation_text="ENTRY")
            fig.add_hline(y=smc["sl"], line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text="SL")
            fig.add_hline(y=smc["tp"], line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="TP")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=500, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        st.markdown("#### ⚙️ Execution Module")
        sig_color = "#26a69a" if smc["bias"] == "BUY" else ("#ef5350" if smc["bias"] == "SELL" else "#848e9c")
        
        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:11px; color:#848e9c; font-family:monospace;'>DECISION SIGNAL:</span><br>
            <span style='font-size:16px; font-weight:bold; color:{sig_color};'>{smc['bias']} STRUCTURE</span>
        </div>
        """, unsafe_allow_html=True)
        
        prop_balance = st.number_input("Prop Size ($)", value=10000.0, step=1000.0, key=f"p_bal_{m_name}")
        risk_pct = st.number_input("Max Risk Per Trade (%)", value=1.0, step=0.1, key=f"p_risk_{m_name}")
        
        allowed_risk_usd = prop_balance * (risk_pct / 100.0)
        pip_distance = abs(smc["entry"] - smc["sl"]) * (10000 if "Gold" not in m_name else 10)
        calculated_lot = allowed_risk_usd / (pip_distance * 10 + 1e-9) if pip_distance > 0 else 0.1
        calculated_lot = max(0.01, round(calculated_lot, 2))
        
        st.markdown(f"""
        <div class='panel-box' style='font-family: monospace; font-size:11px;'>
            Risk Outflow: <span style='color:#ef5350;'>${allowed_risk_usd:.2f}</span><br>
            Automated Sizing: <span style='color:#26a69a;'>{calculated_lot} Lot</span>
        </div>
        """, unsafe_allow_html=True)
        
        # 🔑 AD-ÇAKIŞMA GÜVENLİK ANAHTARI (Dinamik key ataması kilitleri açar abi)
        trade_mode = st.checkbox("Paper Trading Mode Active", value=True, key=f"chk_active_{m_name}")
        
        if smc["bias"] != "WAIT" and trade_mode:
            if st.button(f"Execute Institutional Order", key=f"btn_prod_{m_name}"):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO journal (timestamp, asset, type, entry, sl, tp, lot, pnl, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')",
                    (datetime.now().strftime("%H:%M:%S"), m_name, smc["bias"], smc["entry"], smc["sl"], smc["tp"], calculated_lot, 0.0)
                )
                conn.commit()
                conn.close()
                st.toast("Order executed into SQLite Vault.", icon="🏛️")
                
        st.markdown("##### 📒 Vault Ledger Analytics")
        conn = sqlite3.connect(DB_FILE)
        df_history = pd.read_sql_query("SELECT * FROM journal", conn)
        conn.close()
        
        if not df_history.empty:
            closed_trades = df_history[df_history["status"] != "OPEN"]
            open_count = len(df_history[df_history["status"] == "OPEN"])
            
            # Sadece bu sekmedeki pariteye ait olan verileri süzüyoruz abi analitik karışmasın diye
            df_asset = closed_trades[closed_trades["asset"] == m_name]
            
            if not df_asset.empty:
                wins = len(df_asset[df_asset["pnl"] > 0])
                total_wr = (wins / len(df_asset)) * 100
                net_pnl = df_asset["pnl"].sum()
                
                gross_profits = df_asset[df_asset["pnl"] > 0]["pnl"].sum()
                gross_losses = abs(df_asset[df_asset["pnl"] < 0]["pnl"].sum())
                profit_factor = gross_profits / gross_losses if gross_losses > 0 else gross_profits
                
                st.metric("Winrate Factor", f"%{total_wr:.1f}", key=f"metric_wr_{m_name}")
                st.metric("Net Accumulation PnL", f"${net_pnl:.2f}", key=f"metric_pnl_{m_name}")
                st.metric("Profit Factor", f"{profit_factor:.2f}", key=f"metric_pf_{m_name}")
                
                df_asset = df_asset.copy()
                df_asset["equity"] = prop_balance + df_asset["pnl"].cumsum()
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(y=df_asset["equity"], mode='lines+markers', line=dict(color='#26a69a', width=2), name='Equity'))
                fig_eq.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', height=140, margin=dict(l=5, r=5, t=5, b=5))
                st.plotly_chart(fig_eq, use_container_width=True)
            
            st.caption(f"Active Monitoring: {open_count} open trades.")
            st.dataframe(df_history[df_history["asset"] == m_name].tail(2)[["type", "pnl", "status"]], use_container_width=True, key=f"view_df_{m_name}")
        else:
            st.caption("SQLite ledger is currently vacant.")

# ==========================================
# 🏛 ========================================== 🏛
# ==========================================
st.markdown("<h2 style='margin-bottom:0px; font-weight: 700; color: #ffffff;'>🏛️ NEXUS QUANT v49</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Professional Pure SMC Terminal Node</p>", unsafe_allow_html=True)

ticker_map = {
    "EUR/USD": "EUR/USD", "XAU/USD (Gold)": "XAU/USD"
}

t_eur, t_gold = st.tabs(["EUR/USD", "XAU/USD (Gold)"])

# ✅ BURASI BİRBİRİYLE TAM EŞİTLENDİ MUSTAFA ABİ:
with t_eur: render_pure_production_desk("EUR/USD", ticker_map["EUR/USD"])
with t_gold: render_pure_production_desk("XAU/USD (Gold)", ticker_map["XAU/USD (Gold)"])
