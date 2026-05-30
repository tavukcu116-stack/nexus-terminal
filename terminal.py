# ==========================================
# 📄 DOSYA: terminal.py (NEXUS FRONTEND INTERFACE)
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import backend_core as core
from streamlit_autorefresh import st_autorefresh

# ⏳ AUTO REFRESH LOOP
st_autorefresh(interval=15000, key="nexus_v53_frontend_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #1f222e !important; border-radius: 4px !important; padding: 10px !important; }
    .panel-box { background: #131722; border: 1px solid #1f222e; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    .gate-passed { color: #00ebc7; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ff5a5f; font-family: monospace; font-weight: bold; }
    .status-wait { color: #ffb74d; font-family: monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v53 — ULTIMATE DESK</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Pure Multi-Asset Screener & Quantitative Risk Node</p>", unsafe_allow_html=True)

# 15) MULTI-ASSET WATCHLIST GRUBU ENJEKSİYONU
render_asset = st.sidebar.selectbox("🏛️ PRODUCTION SCREENER GROUP", ["EUR/USD", "XAU/USD", "GBP/USD", "USD/JPY", "NASDAQ", "US30", "BTC/USD", "ETH/USD"])

asset_map = {
    "EUR/USD": "EUR/USD", "XAU/USD": "XAU/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY",
    "NASDAQ": "IXIC", "US30": "DJI", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}

node = core.process_smc_intelligence(asset_map[render_asset])
live_spread = core.calculate_live_spread(asset_map[render_asset])

if node is None:
    st.error(f"Screener stream synchronization error for {render_asset}.")
else:
    df = node["df"]
    core.manage_v53_positions(render_asset, df)
    news_blocked, news_reason = core.get_macro_news_lock(asset_map[render_asset])
    
    # 17) REALTIME RISK CIRCUIT BREAKERS (-3% Daily / -5% Max Drawdown)
    conn = sqlite3.connect("nexus_v53_vault.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pnl) FROM v53_ledger WHERE timestamp >= date('now')")
    daily_pnl_sum = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(pnl) FROM v53_ledger")
    total_pnl_sum = cursor.fetchone()[0] or 0.0
    
    prop_capital = st.number_input("Prop Capital Account Size ($)", value=10000.0, step=1000.0, key=f"cp_{render_asset}")
    daily_lock = daily_pnl_sum < -(prop_capital * 0.03)
    total_lock = total_pnl_sum < -(prop_capital * 0.05)
    
    # 10) KORELASYON MOTORU (Yön Kümeleme Engeli)
    cursor.execute("SELECT asset, type FROM v53_ledger WHERE status = 'OPEN'")
    active_runs = cursor.fetchall()
    correlation_blocked = False
    if len(active_runs) > 0 and render_asset == "XAU/USD":
        for r in active_runs:
            if r[0] == "EUR/USD": correlation_blocked = True

    col_chart, col_desk = st.columns([3, 1])
    
    with col_chart:
        # 20) 🌟 NİHAİ COGNITIVE ANALİZ SONUCU PANELİ (Tam İstediğin Kusursuz Matris Şablonu)
        rr_quality = "NORMAL" if node["rr"] < 2 else "HIGH QUALITY" if node["rr"] < 3 else "A+ SETUP"
        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:11px; color:#848e9c; font-family:monospace;'>NEXUS AUTOMATED SPECIFICATION MATRIX:</span><br>
            <span style='font-size:24px; font-weight:700; color:#ffffff;'>{render_asset}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
            Setup Score: <span style='color:#00ebc7; font-weight:bold;'>{node['score']}/100</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Bias: <span style='color:#2962ff; font-weight:bold;'>{node['bias']}</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Structure: <span style='color:#ffb74d; font-weight:bold;'>{node['structure']}</span><br>
            <span style='font-size:12px; font-family:monospace; color:#b2b5be;'>
                Zone Layout: {node['zone']} | Entry Area: {node['price']:.5f} | SL: {node['sl_p']:.5f} | TP1 (BE): {node['tp1_p']:.5f} | TP2 (Target): {node['tp2_p']:.5f} | Expected RR: {node['rr']:.2f} ({rr_quality})
            </span><br>
            <div style='margin-top:8px; font-size:16px; letter-spacing:1px;' class='{"gate-passed" if node["action"] == "ENTRY READY" else "status-wait"}'>ACTION VECTOR: {node['action']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 📈 TRADINGVIEW HIGH-SPEED MATPLOTLIB RECONSTRUCTION GRAPH
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', name=render_asset
        ))
        fig.update_traces(whiskerwidth=0.3)
        
        # 9) PREMIUM / DISCOUNT RENKLİ ALAN GÖRSEL OVERLAY KATMANI
        fig.add_hrect(y0=node['eq'], y1=node['pdh'], fillcolor="rgba(239, 83, 80, 0.015)", line_width=0, annotation_text="PREMIUM AREA", annotation_position="top left")
        fig.add_hrect(y0=node['pdl'], y1=node['eq'], fillcolor="rgba(38, 166, 154, 0.015)", line_width=0, annotation_text="DISCOUNT AREA", annotation_position="bottom left")
        
        # Tarihi Seans Havuz Çizgileri
        fig.add_hline(y=node['pdh'], line_color="rgba(255, 235, 59, 0.15)", line_width=1, annotation_text="PDH Liquidity Pool")
        fig.add_hline(y=node['pdl'], line_color="rgba(255, 235, 59, 0.15)", line_width=1, annotation_text="PDL Liquidity Pool")
        
        # 2) FVG & 3) OB DİNAMIK KUTU ÇİZİMLERİ
        if node["ob"]:
            ob_color = "rgba(38, 166, 154, 0.05)" if "BULLISH" in node["ob"]["type"] else "rgba(239, 83, 80, 0.05)"
            fig.add_shape(type="rect", x0=node["ob"]["time"], x1=df['datetime'].iloc[-1], y0=node["ob"]["bottom"], y1=node["ob"]["top"], fillcolor=ob_color, line_width=0)
        if node["fvg"]:
            fvg_color = "rgba(41, 98, 255, 0.04)" if "BULLISH" in node["fvg"]["type"] else "rgba(255, 109, 0, 0.04)"
            fig.add_shape(type="rect", x0=node["fvg"]["time"], x1=df['datetime'].iloc[-1], y0=node["fvg"]["bottom"], y1=node["fvg"]["top"], fillcolor=fvg_color, line_width=0)

        if node["bias"] != "WAIT":
            fig.add_hline(y=node["sl_p"], line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text="SL LIMIT")
            fig.add_hline(y=node["tp2_p"], line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="FINAL TARGET")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=520, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        # 6) TRADE CHECKLIST PANELİ
        st.markdown("#### 📋 Verification Gates")
        st.markdown(f"""
        <div class='panel-box' style='font-family:monospace; font-size:11px; line-height:1.7;'>
            SMC Target Session: <span class='{"gate-passed" if node["kz"] else "gate-failed"}'>{"✅ "+node['session'] if node["kz"] else "❌ OUTSIDE TIME"}</span><br>
            Macro Economic Lock: <span class='{"gate-passed" if not news_blocked else "gate-failed"}'>{"✅ CLEAR" if not news_blocked else "❌ LOCKED"}</span><br>
            Live Quote Spread: <span class='{"gate-passed" if live_spread <= 1.5 else "gate-failed"}'>{live_spread:.1f} Pips</span><br>
            Correlation Matrix: <span class='{"gate-passed" if not correlation_blocked else "gate-failed"}'>{"✅ STABLE" if not correlation_blocked else "❌ OVERLAP"}</span><br>
            Daily Drawdown Safeguard: <span class='{"gate-passed" if not daily_lock else "gate-failed"}'>${daily_pnl_sum:.2f} / 3%</span><br>
            Total Drawdown Safeguard: <span class='{"gate-passed" if not total_lock else "gate-failed"}'>${total_pnl_sum:.2f} / 5%</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Risk Dağıtım Konsolu
        risk_pct = st.number_input("Risk Unit (%)", value=1.0, step=0.1, key=f"rk_v53_{render_asset}")
        allowed_risk_usd = prop_capital * (risk_pct / 100.0)
        p_dist = abs(node["price"] - node["sl_p"]) * (10, 10000 if "USD" in render_asset and "XAU" not in render_asset else 10)[1]
        final_lot = allowed_risk_usd / (p_dist * 10 + 1e-9) if p_dist > 0 else 0.1
        final_lot = max(0.01, round(final_lot, 2))
        
        # 13) SETUP ARCHIVE DISPATCHER (Mühürleme Butonu)
        if node["bias"] != "WAIT" and not daily_lock and not total_lock:
            if st.button("DISPATCH ORDER LAYER", key=f"btn_v53_{render_asset}"):
                cursor.execute(
                    "INSERT INTO v53_ledger (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, score, session, regime, setup_zone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'OPEN', ?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M"), render_asset, node["bias"], node["price"], node["sl_p"], node["tp1_p"], node["tp2_p"], final_lot, node["score"], node["session"], node["structure"], node["zone"])
                )
                conn.commit()
                st.toast("Setup dispatched and screenshot variables archived.", icon="🏛️")
                
        # 14) ARCHIVE & 15) FORWARD TESTS & 16) EQUITY CURVE METRICS PANEL
        st.markdown("##### 📒 Performance Metrics Room")
        df_ledger = pd.read_sql_query("SELECT * FROM v53_ledger WHERE status != 'OPEN'", conn)
        b_wr, b_pf, b_exp = core.run_historical_backtest(df)
        
        if not df_ledger.empty:
            closed_pnl = df_ledger["pnl"].values
            wins = len(df_ledger[df_ledger["pnl"] > 0])
            wr = (wins / len(df_ledger)) * 100
            p_factor = closed_pnl[closed_pnl > 0].sum() / (abs(closed_pnl[closed_pnl < 0].sum()) + 1e-9)
            
            # Sharpe, Sortino, Calmar Kriterleri
            std = np.std(closed_pnl) if len(closed_pnl) > 1 else 1.0
            down_std = np.std(closed_pnl[closed_pnl < 0]) if len(closed_pnl[closed_pnl < 0]) > 1 else 1.0
            
            equity_curve = prop_capital + np.cumsum(closed_pnl)
            peaks = np.maximum.accumulate(equity_curve)
            max_dd = ((peaks - equity_curve) / peaks).max() if len(peaks) > 0 else 0.01
            
            sharpe = (np.mean(closed_pnl) / std) * np.sqrt(252) if std > 0 else 0.0
            sortino = (np.mean(closed_pnl) / down_std) * np.sqrt(252) if down_std > 0 else 0.0
            calmar = (np.mean(closed_pnl).sum() / (max_dd + 1e-9))

            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[WALK-FORWARD PERFORMANCE]</b><br>
                Win Rate: <span style='color:#00ebc7;'>%{wr:.1f}</span> | PF: {p_factor:.2f}<br>
                Max Drawdown: <span style='color:#ff5a5f;'>%{max_dd*100:.2f}</span><br>
                Sharpe: {sharpe:.2f} | Sortino: {sortino:.2f} | Calmar: {calmar:.2f}
            </div>
            """, unsafe_allow_html=True)
            
            # 16) REALTIME EQUITY CURVE CHART
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(y=equity_curve, mode='lines+markers', line=dict(color='#00ebc7', width=2)))
            fig_eq.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', height=110, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[3-YEAR HISTORICAL BACKTEST]</b><br>
                Est Winrate: <span style='color:#00ebc7;'>%{b_wr:.1f}</span><br>
                Profit Factor: {b_pf:.2f}<br>
                Expectancy: {b_exp:.2f} Pips<br>
                <span style='color:#848e9c; font-size:10px;'>Awaiting forward validation execution paths...</span>
            </div>
            """, unsafe_allow_html=True)

    conn.close()
            
