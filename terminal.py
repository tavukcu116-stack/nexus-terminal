# ==========================================
# 📄 DOSYA: terminal.py (ELITE INTERFACE)
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import backend_core as core
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NEXUS QUANT v51", layout="wide", page_icon="🏛️")
st_autorefresh(interval=15000, key="nexus_global_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.6px; font-weight:600; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 12px !important; }
    .desk-card { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px;'>🏛️ NEXUS QUANT v51 — QUANTITATIVE NODE</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Walk-Forward Analytics & Monte Carlo Engine Active</p>", unsafe_allow_html=True)

ticker_map = {"EUR/USD": "EUR/USD", "XAU/USD (Gold)": "XAU/USD"}
t_eur, t_gold = st.tabs(["EUR/USD", "XAU/USD (Gold)"])

def render_quantitative_production_desk(m_name, symbol):
    df_15m = core.fetch_raw_market_candles(symbol, "15min")
    df_1h = core.fetch_raw_market_candles(symbol, "1h")
    df_4h = core.fetch_raw_market_candles(symbol, "4h")
    
    if df_15m is None or df_15m.empty:
        st.error(f"Live Multi-Feed Node Pipeline Refused Connection for {m_name}")
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
        c1.metric("Live Feed Price", f"{close_p}")
        c2.metric("HTF Structure Align", htf_bias)
        c3.metric("Regime Context", market_regime)
        c4.metric("Dinamik Spread", f"{dynamic_spread:.1f} Pips")
        
        # 📈 HIGH-PERFORMANCE TRADINGVIEW RECONSTRUCTION
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_15m['datetime'], open=df_15m['open'], high=df_15m['high'], low=df_15m['low'], close=df_15m['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', name=m_name
        ))
        fig.update_traces(whiskerwidth=0.3)
        
        fig.add_hline(y=pdh, line_color="rgba(255, 235, 59, 0.2)", line_width=1, annotation_text="PDH")
        fig.add_hline(y=pdl, line_color="rgba(255, 235, 59, 0.2)", line_width=1, annotation_text="PDL")
        fig.add_hline(y=last_sh, line_color="#ef5350", line_width=1, line_dash="dot", annotation_text="BSL LIQ")
        fig.add_hline(y=last_sl, line_color="#26a69a", line_width=1, line_dash="dot", annotation_text="SSL LIQ")

        if bias != "WAIT":
            fig.add_hline(y=entry, line_color="#2962ff", line_width=1.5, annotation_text="ENTRY")
            fig.add_hline(y=sl, line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text="SL")
            fig.add_hline(y=tp2, line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="TP")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=520, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        st.markdown("#### ⚙️ Risk Sizing Console")
        prop_capital = st.number_input("Prop Capital Limit ($)", value=10000.0, step=1000.0, key=f"cap_{m_name}")
        risk_pct = st.number_input("Max Risk Vector (%)", value=1.0, step=0.1, key=f"risk_{m_name}")
        
        allowed_risk_usd = prop_capital * (risk_pct / 100.0)
        pip_distance = abs(entry - sl) * (10000 if "Gold" not in m_name else 10)
        calculated_lot = allowed_risk_usd / (pip_distance * 10 + 1e-9) if pip_distance > 0 else 0.1
        calculated_lot = max(0.01, round(calculated_lot, 2))
        
        st.markdown(f"""
        <div class='desk-card' style='font-family: monospace; font-size:12px; text-align:center;'>
            Outflow Risk: <span style='color:#ef5350;'>${allowed_risk_usd:.2f}</span><br>
            Calculated Size: <span style='color:#26a69a; font-weight:bold;'>{calculated_lot} Lot</span>
        </div>
        """, unsafe_allow_html=True)
        
        conn = core.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM enterprise_journal WHERE asset = ? AND status = 'OPEN'", (m_name,))
        active_trade_count = cursor.fetchone()[0]
        
        if bias != "WAIT" and active_trade_count == 0:
            if st.button("Seal Quantitative Order", key=f"btn_ex_{m_name}"):
                cursor.execute(
                    "INSERT INTO enterprise_journal (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, max_seen, session) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, 'LIVE')",
                    (datetime.now().strftime("%H:%M:%S"), m_name, bias, entry, sl, midpoint, tp2, calculated_lot, 0.0, entry)
                )
                conn.commit()
                st.toast("Dispatched into SQLite Engine.", icon="🏛️")
                
        # 📊 MULTI-FACTOR PERFORMANS METRIKLERI PANELİ (SHARPE, SORTINO, CALMAR & DRAWDOWN)
        st.markdown("##### 🏛️ Advanced Quantitative Metrics")
        df_db = pd.read_sql_query("SELECT * FROM enterprise_journal WHERE status != 'OPEN'", conn)
        conn.close()
        
        if not df_db.empty:
            closed_pnl = df_db["pnl"].values
            wins = len(df_db[df_db["pnl"] > 0])
            winrate = (wins / len(df_db)) * 100
            
            # Gelişmiş Risk Çarpanları Matematiği abi
            avg_win = closed_pnl[closed_pnl > 0].mean() if len(closed_pnl[closed_pnl > 0]) > 0 else 1.0
            avg_loss = abs(closed_pnl[closed_pnl < 0].mean()) if len(closed_pnl[closed_pnl < 0]) > 0 else 1.0
            p_factor = closed_pnl[closed_pnl > 0].sum() / (abs(closed_pnl[closed_pnl < 0].sum()) + 1e-9)
            
            # Sharpe, Sortino ve Calmar Hesaplama Kalıbı (Gerçek Fon Algoritmaları)
            std_dev = np.std(closed_pnl) if len(closed_pnl) > 1 else 1.0
            downside_pnl = closed_pnl[closed_pnl < 0]
            downside_std = np.std(downside_pnl) if len(downside_pnl) > 1 else 1.0
            
            # Maksimum Drawdown Tespiti
            equity_curve = prop_capital + np.cumsum(closed_pnl)
            peaks = np.maximum.accumulate(equity_curve)
            drawdowns = (peaks - equity_curve) / peaks
            max_drawdown = drawdowns.max() if len(drawdowns) > 0 else 0.01
            
            sharpe_ratio = (np.mean(closed_pnl) / std_dev) * np.sqrt(252) if std_dev > 0 else 0.0
            sortino_ratio = (np.mean(closed_pnl) / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
            calmar_ratio = (np.mean(closed_pnl).sum() / (max_drawdown + 1e-9))
            
            st.metric("Sharpe Ratio (Risk Adj.)", f"{sharpe_ratio:.2f}")
            st.metric("Sortino Ratio (Downside)", f"{sortino_ratio:.2f}")
            st.metric("Calmar Ratio (Drawdown)", f"{calmar_ratio:.2f}")
            st.metric("Maximum Drawdown Factor", f"%{max_drawdown*100:.2f}")
            st.metric("Profit Factor (PF)", f"{p_factor:.2f}")

            # 🎲 MONTE CARLO SIMULATION OVERLAY ENGINE
            st.markdown("##### 🎲 Monte Carlo Stress Path")
            sim_paths = core.compute_monte_carlo_simulations(closed_pnl)
            
            fig_mc = go.Figure()
            for s in range(min(15, sim_paths.shape[1])): # Grafik şişmesin diye en keskin 15 kulvarı çiz abi
                fig_mc.add_trace(go.Scatter(y=sim_paths[:, s], mode='lines', line=dict(width=1), opacity=0.3, showlegend=False))
            fig_mc.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', height=140, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_mc, use_container_width=True)
        else:
            st.caption("Production ledger database is empty. Awaiting Walk-Forward forward validation path.")

with t_eur: render_quantitative_production_desk("EUR/USD", ticker_map["EUR/USD"])
with t_gold: render_quantitative_production_desk("XAU/USD (Gold)", ticker_map["XAU/USD (Gold)"])
