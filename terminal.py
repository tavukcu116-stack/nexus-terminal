# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v54.0 - UI INTERFACE)
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import backend_core as core
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=15000, key="nexus_v54_frontend_refresh")

st.markdown("""
    <style>
    .stApp { background-color: #08090d !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] { background: #11131a !important; border: 1px solid #1f222e !important; border-radius: 4px !important; padding: 10px !important; }
    .panel-box { background: #11131a; border: 1px solid #1f222e; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    .gate-passed { color: #00ebc7; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ff5a5f; font-family: monospace; font-weight: bold; }
    .status-wait { color: #ffb74d; font-family: monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v54 — INSTITUTIONAL TERMINAL</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Pure SMC Engine with Automated Risk of Ruin Circuit Breakers</p>", unsafe_allow_html=True)

# 8) ÇOKLU VARLIK SCREENER'I GROUP
render_asset = st.sidebar.selectbox("🏛️ COGNITIVE WATCHLIST SCREENER", ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "NASDAQ", "US30", "BTC/USD", "ETH/USD"])

asset_map = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY", "XAU/USD": "XAU/USD",
    "NASDAQ": "IXIC", "US30": "DJI", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}

node = core.extract_quant_smc_matrix(asset_map[render_asset])
spread_pips, live_bid, live_ask = core.get_live_spread_data(asset_map[render_asset])

if node is None:
    st.error(f"Screener pipeline synch error for {render_asset}.")
else:
    df = node["df"]
    core.manage_v54_positions(render_asset, df)
    news_blocked, news_reason = core.check_economic_news_timeline(asset_map[render_asset])
    
    # 19) GERÇEK DRAWDOWN DEVRE KESİCİLERİ (%3 Günlük / %5 Toplam Zarar Kontrolü)
    conn = sqlite3.connect("nexus_v54_vault.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger WHERE timestamp >= date('now')")
    daily_pnl = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger")
    total_pnl = cursor.fetchone()[0] or 0.0
    
    prop_capital = st.number_input("Prop Account Capital Limit ($)", value=10000.0, step=1000.0, key=f"cp_{render_asset}")
    daily_circuit_lock = daily_pnl < -(prop_capital * 0.03)
    total_circuit_lock = total_pnl < -(prop_capital * 0.05)
    
    # 15) KORELASYON RISK MOTORU (Aynı Yönde Aşırı Risk Yığılmasını Engelleme)
    cursor.execute("SELECT asset, type FROM v54_ledger WHERE status = 'OPEN'")
    active_runs = cursor.fetchall()
    correlation_lock = False
    if len(active_runs) > 0 and render_asset == "XAU/USD":
        for r in active_runs:
            if r[0] == "EUR/USD": correlation_lock = True # EURUSD açıkken risk bindirmemek için Altını kilitler abi

    col_chart, col_desk = st.columns([3, 1])
    
    with col_chart:
        # 20) ANALİZ SONUCU PANELİ (TAM ANLAŞILIR MATRİS MODELİ ABİ)
        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:11px; color:#848e9c; font-family:monospace;'>NEXUS LIVE QUANT ENGINE STATUS SPECIFICATION:</span><br>
            <span style='font-size:24px; font-weight:700;'>{render_asset}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
            Setup Grade: <span style='color:#00ebc7; font-weight:bold;'>{node['q_class']} ({node['score']}/100 pts)</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Bias State: <span style='color:#2962ff; font-weight:bold;'>{node['bias']}</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Market Structure: <span style='color:#ffb74d; font-weight:bold;'>{node['structure']}</span><br>
            <span style='font-size:12px; font-family:monospace; color:#b2b5be;'>
                SMC Swing Zone: {node['zone']} | Live Spread: {spread_pips:.1f} Pips | SL Target: {node['sl_p']:.5f} | TP1 (BE): {node['tp1_p']:.5f} | TP2 (Final): {node['tp2_p']:.5f} | Math RR: {node['rr']:.2f}
            </span><br>
            <div style='margin-top:8px; font-size:15px; font-family:monospace;' class='{"gate-passed" if node["bias"] != "WAIT" else "status-wait"}'>ACTION VECTOR PLAN: {node['action']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 📈 HIGH-SPEED TRADINGVIEW GRAPH
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', name=render_asset
        ))
        fig.update_traces(whiskerwidth=0.3)
        
        # Premium / Discount Akıllı Seans Alan Görsel Overlay Katmanı
        fig.add_hrect(y0=node['eq'], y1=node['pdh'], fillcolor="rgba(239, 83, 80, 0.015)", line_width=0, annotation_text="PREMIUM AREA", annotation_position="top left")
        fig.add_hrect(y0=node['pdl'], y1=node['eq'], fillcolor="rgba(38, 166, 154, 0.015)", line_width=0, annotation_text="DISCOUNT AREA", annotation_position="bottom left")
        
        # 16) Likidite Havuz Çizgileri
        fig.add_hline(y=node['pdh'], line_color="rgba(255, 235, 59, 0.15)", line_width=1, annotation_text="PDH Pool")
        fig.add_hline(y=node['pdl'], line_color="rgba(255, 235, 59, 0.15)", line_width=1, annotation_text="PDL Pool")
        
        #OB-FVG Kutuları
        if node["ob"]:
            ob_c = "rgba(38, 166, 154, 0.05)" if "BULLISH" in node["ob"]["type"] else "rgba(239, 83, 80, 0.05)"
            fig.add_shape(type="rect", x0=node["ob"]["time"], x1=df['datetime'].iloc[-1], y0=node["ob"]["bottom"], y1=node["ob"]["top"], fillcolor=ob_c, line_width=0)
        if node["fvg"]:
            fvg_c = "rgba(41, 98, 255, 0.04)" if "BULLISH" in node["fvg"]["type"] else "rgba(255, 109, 0, 0.04)"
            fig.add_shape(type="rect", x0=node["fvg"]["time"], x1=df['datetime'].iloc[-1], y0=node["fvg"]["bottom"], y1=node["fvg"]["top"], fillcolor=fvg_c, line_width=0)

        if node["bias"] != "WAIT":
            fig.add_hline(y=node["sl_p"], line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text="SL LIMIT")
            fig.add_hline(y=node["tp2_p"], line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="TP2 FINAL")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#08090d', plot_bgcolor='#08090d', xaxis_rangeslider_visible=False, height=520, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        # 6) TRADE CHECKLIST PANELİ
        st.markdown("#### 📋 Core Verification")
        st.markdown(f"""
        <div class='panel-box' style='font-family:monospace; font-size:11px; line-height:1.7;'>
            Target Session: <span class='{"gate-passed" if node["kz"] else "gate-failed"}'>{"✅ "+node['session'] if node["kz"] else "❌ CLOSED"}</span><br>
            Macro News Filter: <span class='{"gate-passed" if not news_blocked else "gate-failed"}'>{"✅ CLEAR" if not news_blocked else "❌ "+news_reason}</span><br>
            Live Spread Protocol: <span class='{"gate-passed" if spread_pips <= 1.5 else "gate-failed"}'>{spread_pips:.1f} Pips</span><br>
            Correlation Cluster: <span class='{"gate-passed" if not correlation_lock else "gate-failed"}'>{"✅ STABLE" if not correlation_lock else "❌ LOCKED"}</span><br>
            Daily Drawdown Cap: <span class='{"gate-passed" if not daily_circuit_lock else "gate-failed"}'>${daily_pnl:.2f} / 3%</span><br>
            Maximum Drawdown Cap: <span class='{"gate-passed" if not total_circuit_lock else "gate-failed"}'>${total_pnl:.2f} / 5%</span>
        </div>
        """, unsafe_allow_html=True)
        
        # 14) DINAMIK POZISYON BOYUTLANDIRMA (Otomatik Lot Hesaplama)
        risk_pct = st.number_input("Risk Unit Factor (%)", value=1.0, step=0.1, key=f"rk_v54_{render_asset}")
        allowed_risk_usd = prop_capital * (risk_pct / 100.0)
        p_distance = abs(node["price"] - node["sl_p"]) * (10, 10000 if "USD" in render_asset and "XAU" not in render_asset else 10)[1]
        final_lot = allowed_risk_usd / (p_distance * 10 + 1e-9) if p_distance > 0 else 0.1
        final_lot = max(0.01, round(final_lot, 2))
        
        # 9) SETUP ARSİVLEME TETİGİ
        if node["bias"] != "WAIT" and not daily_circuit_lock and not total_circuit_lock:
            if st.button("MÜHÜRLE VE EMİR GÖNDER", key=f"btn_v54_{render_asset}"):
                cursor.execute(
                    "INSERT INTO v54_ledger (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, score, q_class, session, duration_min, close_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'OPEN', ?, ?, ?, 0, 'RUNNING')",
                    (datetime.now().strftime("%Y-%m-%d %H:%M"), render_asset, node["bias"], node["price"], node["sl_p"], node["tp1_p"], node["tp2_p"], final_lot, node["score"], node["q_class"], node["session"])
                )
                conn.commit()
                st.toast("Setup archived with class attributes.", icon="🏛️")
                
        # 13) GERÇEK FORWARD-TEST PERFORMANS PANELİ & 10) BACKTEST ENTEGRASYONU
        st.markdown("##### 📒 Performance Metrics Room")
        df_ledger = pd.read_sql_query("SELECT * FROM v54_ledger WHERE status != 'OPEN' AND status != 'EXPIRED_CANCEL'", conn)
        b_wr, b_pf, b_dd, b_exp = core.run_historical_backtest_matrix(df)
        
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
            
            # 10) RISK OF RUIN HESAPLAYICISI (Hesap Batma Olasılığı Formülü abi)
            # Matematiksel Basitleştirilmiş Formula: ((1 - (WR - 0.5)) / (1 + (WR - 0.5))) ^ (Capital / Risk)
            wr_f = wr / 100.0
            ror_factor = (((1 - wr_f) / (wr_f + 1e-9)) ** (1 / risk_pct)) * 100
            ror_factor = min(100.0, max(0.0, ror_factor))

            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[WALK-FORWARD REAL PERFORMANCE]</b><br>
                Win Rate: <span style='color:#00ebc7;'>%{wr:.1f}</span> | PF: {p_factor:.2f}<br>
                Max Drawdown: <span style='color:#ff5a5f;'>%{max_dd*100:.2f}</span><br>
                Risk of Ruin: <span style='color:#ff5a5f;'>%{ror_factor:.1f}</span><br>
                Sharpe: {sharpe:.2f} | Sortino: {sortino:.2f} | Calmar: {calmar:.2f}
            </div>
            """, unsafe_allow_html=True)
            
            # Equity Curve Grafiği
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(y=equity_curve, mode='lines+markers', line=dict(color='#00ebc7', width=1.5)))
            fig_eq.update_layout(template='plotly_dark', paper_bgcolor='#11131a', plot_bgcolor='#11131a', height=110, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[3-YEAR HISTORICAL BACKTEST ENGINE]</b><br>
                Est Winrate: <span style='color:#00ebc7;'>%{b_wr:.1f}</span><br>
                Profit Factor: {b_pf:.2f}<br>
                Expectancy: {b_exp:.2f} Pips<br>
                <span style='color:#848e9c; font-size:10px;'>Walk-forward forward verification engine active.</span>
            </div>
            """, unsafe_allow_html=True)

    conn.close()
        
