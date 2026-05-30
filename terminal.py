# ==========================================
# 📄 DOSYA: terminal.py (NEXUS UI v52.0 - PRODUCTION)
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timezone
import backend_core as core
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NEXUS QUANT v52", layout="wide", page_icon="🏛️")
st_autorefresh(interval=15000, key="nexus_global_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 10px !important; }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 12px; margin-bottom: 10px; }
    .gate-passed { color: #26a69a; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ef5350; font-family: monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v52 — PRODUCTION DESK</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Enterprise Quantitative Walk-Forward Node</p>", unsafe_allow_html=True)

ticker_map = {"EUR/USD": "EUR/USD", "XAU/USD (Gold)": "XAU/USD"}
t_eur, t_gold = st.tabs(["EUR/USD", "XAU/USD (Gold)"])

def render_quantitative_terminal(m_name, symbol):
    df_15m = core.fetch_raw_market_candles(symbol, "15min")
    df_1h = core.fetch_raw_market_candles(symbol, "1h")
    df_4h = core.fetch_raw_market_candles(symbol, "4h")
    
    if df_15m is None or df_15m.empty:
        st.error(f"Live Node Pipeline Refused Connection for {m_name}")
        return
        
    # Canlı açık işlemleri takip eden motoru tetikle abi
    core.manage_enterprise_positions(m_name, df_15m)
    
    news_blocked, news_reason = core.check_macro_news_impact(symbol)
    market_regime, atr_val, dynamic_spread = core.calculate_market_regime(df_15m, symbol)
    structure, last_sh, last_sl, market_zone, eq_level, zone_score = core.process_smc_liquidity_matrix(df_15m)
    
    close_p = df_15m["close"].iloc[-1]
    pdh = df_15m["high"].max()
    pdl = df_15m["low"].min()
    
    # Seans ve Killzone Zamanlama Süzgeci (UTC)
    current_hour = datetime.utcnow().hour
    current_session = "ASIA" if current_hour < 7 else "LONDON" if current_hour < 13 else "NEW YORK"
    killzone_safe = (8 <= current_hour < 12) or (13 <= current_hour < 17)

    # 🔗 KORELASYON FİLTRESİ MATRIX
    conn = core.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT asset, type FROM enterprise_journal WHERE status = 'OPEN'")
    active_trades = cursor.fetchall()
    
    correlation_blocked = False
    if len(active_trades) > 0 and m_name == "XAU/USD (Gold)":
        for t in active_trades:
            if t[0] == "EUR/USD": correlation_blocked = True

    # 🔒 3) GÜNLÜK VE TOPLAM DRAWDOWN RISK KİLİTLERİ (Kural İhlal Kalkanı)
    cursor.execute("SELECT SUM(pnl) FROM enterprise_journal WHERE timestamp >= date('now')")
    daily_pnl_sum = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(pnl) FROM enterprise_journal")
    total_pnl_sum = cursor.fetchone()[0] or 0.0
    
    # Eğer günlük zarar %3'ü veya toplam drawdown %5'i aşarsa sistemi tamamen kilitle abi!
    prop_capital = st.number_input("Account Balance Size ($)", value=10000.0, step=1000.0, key=f"cap_{m_name}")
    daily_risk_lock = daily_pnl_sum < -(prop_capital * 0.03)
    total_dd_lock = total_pnl_sum < -(prop_capital * 0.05)
    
    bias = "WAIT"
    entry, sl, tp1, tp2 = 0.0, 0.0, 0.0, 0.0
    
    if killzone_safe and not news_blocked and not correlation_blocked and not daily_risk_lock and not total_dd_lock:
        if "BULLISH" in structure and market_zone == "DISCOUNT":
            bias = "BUY"; entry = close_p; sl = last_sl - (atr_val * 0.2); tp1 = eq_level; tp2 = last_sh
        elif "BEARISH" in structure and market_zone == "PREMIUM":
            bias = "SELL"; entry = close_p; sl = last_sh + (atr_val * 0.2); tp1 = eq_level; tp2 = last_sl

    col_chart, col_desk = st.columns([3, 1])
    
    with col_chart:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Live Stream Price", f"{close_p}")
        c2.metric("SMC Context / Score", f"{structure} ({zone_score} pts)")
        c3.metric("Premium / Discount", market_zone)
        c4.metric("Live Spread", f"{dynamic_spread:.1f} Pips")
        
        # 📈 OPTIMIZED CANDLESTICK VIEWPORT
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
            fig.add_hline(y=tp1, line_color="rgba(38, 166, 154, 0.5)", line_width=1, line_dash="dot", annotation_text="PARTIAL TP1 (BE)")
            fig.add_hline(y=tp2, line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="FINAL TP2")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=520, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        st.markdown("#### ⚙️ Guard & Risk Gateway")
        st.markdown(f"""
        <div class='panel-box' style='font-family: monospace; font-size:11px;'>
            Economic Calendar: <span class='{"gate-passed" if not news_blocked else "gate-failed"}'>{news_reason}</span><br>
            Correlation Block: <span class='{"gate-passed" if not correlation_blocked else "gate-failed"}'>{"CLEAR" if not correlation_blocked else "LOCKED"}</span><br>
            Daily Drawdown: <span class='{"gate-passed" if not daily_risk_lock else "gate-failed"}'>${daily_pnl_sum:.2f} / 3%</span><br>
            Total Drawdown: <span class='{"gate-passed" if not total_dd_lock else "gate-failed"}'>${total_pnl_sum:.2f} / 5%</span><br>
            Current Session: <span class='gate-passed'>{current_session}</span>
        </div>
        """, unsafe_allow_html=True)
        
        risk_pct = st.number_input("Risk Per Position (%)", value=1.0, step=0.1, key=f"risk_{m_name}")
        allowed_risk_usd = prop_capital * (risk_pct / 100.0)
        pip_distance = abs(entry - sl) * (10000 if "Gold" not in m_name else 10)
        calculated_lot = allowed_risk_usd / (pip_distance * 10 + 1e-9) if pip_distance > 0 else 0.1
        calculated_lot = max(0.01, round(calculated_lot, 2))
        
        st.markdown(f"""
        <div class='panel-box' style='font-family: monospace; font-size:12px; text-align:center;'>
            Allocated USD: <span style='color:#ef5350;'>${allowed_risk_usd:.2f}</span><br>
            SMC Target Size: <span style='color:#26a69a; font-weight:bold;'>{calculated_lot} Lot</span>
        </div>
        """, unsafe_allow_html=True)
        
        # 📁 SETUP ARŞİVLEME VE EMİR KİLİDİ
        cursor.execute("SELECT COUNT(*) FROM enterprise_journal WHERE asset = ? AND status = 'OPEN'", (m_name,))
        active_trade_count = cursor.fetchone()[0]
        
        if bias != "WAIT" and active_trade_count == 0 and not daily_risk_lock and not total_dd_lock:
            if st.button("Seal Core Order", key=f"btn_ex_{m_name}"):
                cursor.execute(
                    "INSERT INTO enterprise_journal (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, max_seen, session, execution_type, score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'OPEN', ?, ?, 'FORWARD', ?)",
                    (datetime.now().strftime("%H:%M:%S"), m_name, bias, entry, sl, tp1, tp2, calculated_lot, entry, current_session, zone_score)
                )
                conn.commit()
                st.toast("Setup archived into SQLite vault.", icon="🏛️")
                
        # 📊 TEK PANELDE GELİŞMİŞ PERFORMANS ANALİTİĞİ (WALK-FORWARD & GEÇMİŞ ENGINE)
        st.markdown("##### 🏛️ Walk-Forward Performance Matrix")
        df_history = pd.read_sql_query("SELECT * FROM enterprise_journal WHERE status != 'OPEN'", conn)
        
        # Arka plandaki gerçek geçmiş backtest motorunu koştur abi
        b_wr, b_pf, b_dd, b_exp = core.run_historical_backtest_engine(df_15m)
        
        if not df_history.empty:
            closed_pnl = df_history["pnl"].values
            wins = len(df_history[df_history["pnl"] > 0])
            total_wr = (wins / len(df_history)) * 100
            p_factor = closed_pnl[closed_pnl > 0].sum() / (abs(closed_pnl[closed_pnl < 0].sum()) + 1e-9)
            
            # Gelişmiş Finansal Rasyolar (Sharpe, Sortino, Calmar)
            std_dev = np.std(closed_pnl) if len(closed_pnl) > 1 else 1.0
            downside_std = np.std(closed_pnl[closed_pnl < 0]) if len(closed_pnl[closed_pnl < 0]) > 1 else 1.0
            
            equity_curve = prop_capital + np.cumsum(closed_pnl)
            peaks = np.maximum.accumulate(equity_curve)
            max_dd = ((peaks - equity_curve) / peaks).max() if len(peaks) > 0 else 0.01
            
            sharpe = (np.mean(closed_pnl) / std_dev) * np.sqrt(252) if std_dev > 0 else 0.0
            sortino = (np.mean(closed_pnl) / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
            calmar = (np.mean(closed_pnl).sum() / (max_dd + 1e-9))
            expectancy = (total_wr/100 * (closed_pnl[closed_pnl > 0].mean() if wins > 0 else 1.0)) - ((1 - total_wr/100) * (abs(closed_pnl[closed_pnl < 0].mean()) if len(closed_pnl[closed_pnl < 0]) > 0 else 1.0))

            # Tablosu
            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[CANLI FORWARD TEST METRIKLERI]</b><br>
                Win Rate: <span style='color:#26a69a;'>%{total_wr:.1f}</span> | PF: {p_factor:.2f}<br>
                Max Drawdown: <span style='color:#ef5350;'>%{max_dd*100:.2f}</span><br>
                Expectancy: ${expectancy:.2f}<br>
                Sharpe: {sharpe:.2f} | Sortino: {sortino:.2f} | Calmar: {calmar:.2f}
            </div>
            """, unsafe_allow_html=True)
            
            # 🎲 MONTE CARLO STRES TESTİ GRAFİĞİ
            st.markdown("##### 🎲 Monte Carlo Risk Path")
            sim_paths = core.compute_monte_carlo(closed_pnl)
            fig_mc = go.Figure()
            for s in range(min(12, sim_paths.shape[1])):
                fig_mc.add_trace(go.Scatter(y=sim_paths[:, s], mode='lines', line=dict(width=1), opacity=0.3, showlegend=False))
            fig_mc.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', height=120, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_mc, use_container_width=True)
        else:
            # Canlı işlem yoksa arka plandaki gerçek geçmiş backtest sonuçlarını bas abi ekrana!
            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[HISTORICAL 3-YEAR BACKTEST MATRIX]</b><br>
                Historical WR: <span style='color:#26a69a;'>%{b_wr:.1f}</span> | PF: {b_pf:.2f}<br>
                Historical DD: <span style='color:#ef5350;'>%{b_dd*100:.2f}</span><br>
                Expectancy: ${b_exp:.2f}<br>
                <span style='color:#848e9c; font-size:10px;'>Awaiting forward walk trades...</span>
            </div>
            """, unsafe_allow_html=True)

    conn.close()

with t_eur: render_quantitative_terminal("EUR/USD", ticker_map["EUR/USD"])
with t_gold: render_quantitative_terminal("XAU/USD (Gold)", ticker_map["XAU/USD (Gold)"])
            
