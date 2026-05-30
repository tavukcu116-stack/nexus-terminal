import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import backend_core as core
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NEXUS v50 PRO", layout="wide", page_icon="🏛️")
st_autorefresh(interval=15000, key="nexus_global_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #131722 !important; color: #d1d4dc !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.6px; font-weight:600; }
    div[data-testid="stMetric"] { background: #1c2030 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 12px !important; }
    .desk-card { background: #1c2030; border: 1px solid #2a2e39; border-radius: 4px; padding: 15px; margin-bottom: 10px; }
    .gate-passed { color: #26a69a; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ef5350; font-family: monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px;'>🏛️ NEXUS QUANT v50 — INTERFACE</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Modular Institutional SMC Terminal</p>", unsafe_allow_html=True)

ticker_map = {"EUR/USD": "EUR/USD", "XAU/USD (Gold)": "XAU/USD"}
t_eur, t_gold = st.tabs(["EUR/USD", "XAU/USD (Gold)"])

def render_pure_production_desk(m_name, symbol):
    df_15m = core.fetch_raw_market_candles(symbol, "15min")
    df_1h = core.fetch_raw_market_candles(symbol, "1h")
    df_4h = core.fetch_raw_market_candles(symbol, "4h")
    
    if df_15m is None or df_15m.empty:
        st.error(f"Pipeline Connection Refused for {m_name}")
        return
        
    core.manage_enterprise_positions(m_name, df_15m)
    news_blocked, news_reason = core.check_macro_news_impact()
    market_regime, atr_val, dynamic_spread = core.calculate_market_regime(df_15m, symbol)
    htf_bias, last_sh, last_sl, sweep_detected, displacement = core.process_smc_liquidity_matrix(df_15m, df_1h, df_4h)
    
    pdh = df_15m["high"].max()
    pdl = df_15m["low"].min()
    midpoint = (pdh + pdl) / 2
    close_p = df_15m["close"].iloc[-1]
    
    current_hour = datetime.utcnow().hour
    current_session = "ASIA" if current_hour < 7 else "LONDON" if current_hour < 13 else "NEW YORK"
    killzone_safe = (8 <= current_hour < 12) or (13 <= current_hour < 17)

    bias = "WAIT"
    entry, sl, tp1, tp2 = 0.0, 0.0, 0.0, 0.0
    
    if killzone_safe and not news_blocked and htf_bias != "WAIT" and dynamic_spread <= 1.5:
        if htf_bias == "BULLISH" and close_p < midpoint and sweep_detected:
            bias = "BUY"; entry = close_p; sl = last_sl - (atr_val * 0.3); tp1 = midpoint; tp2 = last_sh
        elif htf_bias == "BEARISH" and close_p > midpoint and sweep_detected:
            bias = "SELL"; entry = close_p; sl = last_sh + (atr_val * 0.3); tp1 = midpoint; tp2 = last_sl

    rr_ratio = 0.0
    if entry > 0:
        rr_ratio = abs(entry - tp2) / (abs(entry - sl) + 1e-9)
        if rr_ratio < 1.5: bias = "WAIT"

    col_chart, col_desk = st.columns([3, 1])
    
    with col_chart:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Live Price", f"{close_p}")
        c2.metric("HTF Bias Alignment", htf_bias)
        c3.metric("Market Regime", market_regime)
        c4.metric("Live Spread", f"{dynamic_spread:.1f} Pips")
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_15m['datetime'], open=df_15m['open'], high=df_15m['high'], low=df_15m['low'], close=df_15m['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', name=m_name
        ))
        fig.update_traces(whiskerwidth=0.3)
        
        fig.add_hline(y=pdh, line_color="rgba(255, 235, 59, 0.2)", line_width=1, annotation_text="PDH")
        fig.add_hline(y=pdl, line_color="rgba(255, 235, 59, 0.2)", line_width=1, annotation_text="PDL")
        fig.add_hline(y=last_sh, line_color="#ef5350", line_width=1, line_dash="dot", annotation_text="BSL")
        fig.add_hline(y=last_sl, line_color="#26a69a", line_width=1, line_dash="dot", annotation_text="SSL")

        if bias != "WAIT":
            fig.add_hline(y=entry, line_color="#2962ff", line_width=1.5, annotation_text="ENTRY")
            fig.add_hline(y=sl, line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text="SL")
            fig.add_hline(y=tp2, line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="TP")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', xaxis_rangeslider_visible=False, height=520, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        st.markdown("#### ⚙️ Gateways")
        st.markdown(f"""
        <div class='desk-card' style='font-family: monospace; font-size:11px;'>
            Economic Filter: <span class='{"gate-passed" if not news_blocked else "gate-failed"}'>{news_reason}</span><br>
            Active Session: <span class='gate-passed'>{current_session}</span><br>
            Killzone Gate: <span class='{"gate-passed" if killzone_safe else "gate-failed"}'>{"OPEN" if killzone_safe else "CLOSED"}</span>
        </div>
        """, unsafe_allow_html=True)
        
        prop_capital = st.number_input("Account Balance ($)", value=10000.0, step=1000.0, key=f"cap_{m_name}")
        risk_pct = st.number_input("Risk Per Position (%)", value=1.0, step=0.1, key=f"risk_{m_name}")
        
        allowed_risk_usd = prop_capital * (risk_pct / 100.0)
        pip_distance = abs(entry - sl) * (10000 if "Gold" not in m_name else 10)
        calculated_lot = allowed_risk_usd / (pip_distance * 10 + 1e-9) if pip_distance > 0 else 0.1
        calculated_lot = max(0.01, round(calculated_lot, 2))
        
        st.markdown(f"""
        <div class='desk-card' style='font-family: monospace; font-size:12px; text-align:center;'>
            Allocated Loss: <span style='color:#ef5350;'>${allowed_risk_usd:.2f}</span><br>
            Lot Sizing: <span style='color:#26a69a; font-weight:bold;'>{calculated_lot} Lot</span>
        </div>
        """, unsafe_allow_html=True)
        
        conn = core.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM enterprise_journal WHERE asset = ? AND status = 'OPEN'", (m_name,))
        active_trade_count = cursor.fetchone()[0]
        
        if bias != "WAIT" and active_trade_count == 0:
            if st.button("Seal Core Execution", key=f"btn_ex_{m_name}"):
                cursor.execute(
                    "INSERT INTO enterprise_journal (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, max_seen, session) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)",
                    (datetime.now().strftime("%H:%M:%S"), m_name, bias, entry, sl, midpoint, tp2, calculated_lot, 0.0, entry, current_session)
                )
                conn.commit()
                st.toast("Position locked into SQLite Vault.", icon="🏛️")
                
        st.markdown("##### 📊 Institutional Analytics")
        df_db = pd.read_sql_query("SELECT * FROM enterprise_journal WHERE status != 'OPEN'", conn)
        conn.close()
        
        if not df_db.empty:
            closed_pnl = df_db["pnl"]
            wins = len(df_db[closed_pnl > 0])
            winrate = (wins / len(df_db)) * 100
            
            avg_win = closed_pnl[closed_pnl > 0].mean() if len(df_db[closed_pnl > 0]) > 0 else 1.0
            avg_loss = abs(closed_pnl[closed_pnl < 0].mean()) if len(df_db[closed_pnl < 0]) > 0 else 1.0
            
            expectancy = (winrate/100 * avg_win) - ((1 - winrate/100) * avg_loss)
            p_factor = closed_pnl[closed_pnl > 0].sum() / (abs(closed_pnl[closed_pnl < 0].sum()) + 1e-9)
            
            st.metric("Pure Winrate", f"%{winrate:.1f}")
            st.metric("Mathematical Expectancy", f"${expectancy:.2f}")
            st.metric("Profit Factor", f"{p_factor:.2f}")
            
            df_db["equity"] = prop_capital + closed_pnl.cumsum()
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(y=df_db["equity"], mode='lines+markers', line=dict(color='#26a69a', width=1.5)))
            fig_eq.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', height=130, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.caption("Production ledger database is empty.")

with t_eur: render_pure_production_desk("EUR/USD", ticker_map["EUR/USD"])
with t_gold: render_pure_production_desk("XAU/USD (Gold)", ticker_map["XAU/USD (Gold)"])
                         
