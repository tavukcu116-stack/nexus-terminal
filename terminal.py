# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v54.6 - ENTERPRISE UI INTERFACE)
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import backend_core as core
from streamlit_autorefresh import st_autorefresh

# ⏳ GLOBAL FRONTEND AUTO-REFRESH (Twelve Data API rate-limit sınırlarına tam uyumlu 15s döngü)
st_autorefresh(interval=15000, key="nexus_v54_production_frontend_refresh")

# ==========================================
# 🎨 BRANDED TRADINGVIEW ULTRA-DARK COGNITIVE UI
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #0c0d12 !important; color: #b2b5be !important; }
    h1, h2, h3, h4, label { color: #ffffff !important; font-family: 'Inter', sans-serif !important; letter-spacing: -0.5px; font-weight: 600; }
    div[data-testid="stMetric"] { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important; padding: 10px !important; }
    .panel-box { background: #131722; border: 1px solid #2a2e39; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
    .gate-passed { color: #00ebc7; font-family: monospace; font-weight: bold; }
    .gate-failed { color: #ff5a5f; font-family: monospace; font-weight: bold; }
    .status-wait { color: #ffb74d; font-family: monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:0px; font-weight:700;'>🏛️ NEXUS QUANT v54.6 — SYSTEM RUNTIME</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #848e9c; font-size:12px; margin-top:2px; margin-bottom:15px;'>Enterprise Quantitative Core & Telegram Shield Active</p>", unsafe_allow_html=True)

# ==========================================
# 💱 CHOSEN ASSET CLASS RECONNAISSANCE SCREENER
# ==========================================
render_asset = st.sidebar.selectbox(
    "🏛️ PRODUCTION WATCHLIST SCREENER", 
    ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "NASDAQ", "US30", "BTC/USD", "ETH/USD"]
)

# Ticker dönüştürme matrisi
asset_map = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY", "XAU/USD": "XAU/USD",
    "NASDAQ": "IXIC", "US30": "DJI", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}

# Backend akıl küpünden analiz verilerini ve anlık Quote spread'ini çekelim abi
node = core.extract_quant_smc_matrix(asset_map[render_asset])
spread_pips, live_bid, live_ask = core.get_live_spread_data(asset_map[render_asset])

if node is None:
    st.error(f"Screener data ingestion pipeline buffer overflow for {render_asset}.")
else:
    df = node["df"]
    
    # ⚙️ Canlı açık işlemleri takip eden, kısmi kapanış ve iz süren koruma çarkını tetikle abi
    core.manage_v54_positions(render_asset, df)
    
    # Forex Factory RSS Canlı Haber Durumu
    news_blocked, news_reason = core.check_economic_news_timeline(asset_map[render_asset])
    
    # ==========================================
    # 🛡️ PROP REALTIME LOSS CIRCUIT BREAKER
    # ==========================================
    conn = sqlite3.connect("nexus_v54_vault.db")
    cursor = conn.cursor()
    
    # Günlük Kasa PnL Defteri Taraması
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger WHERE timestamp >= date('now')")
    daily_pnl_sum = cursor.fetchone()[0] or 0.0
    
    # Kümülatif Toplam PnL Defteri Taraması
    cursor.execute("SELECT SUM(pnl) FROM v54_ledger")
    total_pnl_sum = cursor.fetchone()[0] or 0.0
    
    # Prop Hesabı Bakiye Ayarı (Kural Kalkanı İçin Referans)
    prop_capital = st.number_input("Account Balance Capital Size ($)", value=10000.0, step=1000.0, key=f"capital_v54_{render_asset}")
    
    # %3 Günlük Zarar ve %5 Toplam Drawdown Kilit Kontrolü abi
    daily_circuit_lock = daily_pnl_sum < -(prop_capital * 0.03)
    total_circuit_lock = total_pnl_sum < -(prop_capital * 0.05)
    
    # ==========================================
    # 🔗 KORELASYON RISK MOTORU (CLUSTER LOCK)
    # ==========================================
    cursor.execute("SELECT asset, type FROM v54_ledger WHERE status = 'OPEN'")
    active_runs = cursor.fetchall()
    correlation_blocked = False
    if len(active_runs) > 0 and render_asset == "XAU/USD":
        for r in active_runs:
            if r[0] == "EUR/USD": correlation_blocked = True

    col_chart, col_desk = st.columns([3, 1])
    
    with col_chart:
        # ==========================================
        # 🏛️ NİHAİ COGNITIVE ANALİZ SONUCU PANELİ (MÜHÜRLÜ MATRIX)
        # ==========================================
        st.markdown(f"""
        <div class='panel-box'>
            <span style='font-size:11px; color:#848e9c; font-family:monospace;'>NEXUS HIGH-FREQUENCY AUTOMATED CORE MATRIX:</span><br>
            <span style='font-size:24px; font-weight:700; color:#ffffff;'>{render_asset}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
            Setup Grade: <span style='color:#00ebc7; font-weight:bold;'>{node['q_class']} ({node['score']}/100 pts)</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Bias Mode: <span style='color:#2962ff; font-weight:bold;'>{node['bias']}</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            Structure: <span style='color:#ffb74d; font-weight:bold;'>{node['structure']}</span><br>
            <span style='font-size:12px; font-family:monospace; color:#b2b5be;'>
                SMC Swing Zone: {node['zone']} | Live Bid/Ask Spread: {spread_pips:.1f} Pips | SL Target: {node['sl_p']:.5f} | TP1 (BE): {node['tp1_p']:.5f} | TP2 (Final): {node['tp2_p']:.5f} | Math RR: {node['rr']:.2f}
            </span><br>
            <div style='margin-top:8px; font-size:15px; font-family:monospace;' class='{"gate-passed" if node["bias"] != "WAIT" else "status-wait"}'>ACTION VECTOR PLAN: {node['action']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # ==========================================
        # 📈 HIGH-PERFORMANCE PLOTLY CANDLESTICK GRAPH
        # ==========================================
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350', name=render_asset
        ))
        fig.update_traces(whiskerwidth=0.3) # Fitil kalınlık optimizasyonu abi
        
        # Premium / Discount Akıllı Swing Alan Görsel Overlay Katmanları
        fig.add_hrect(y0=node['eq'], y1=node['pdh'], fillcolor="rgba(239, 83, 80, 0.015)", line_width=0, annotation_text="HTF PREMIUM AREA", annotation_position="top left")
        fig.add_hrect(y0=node['pdl'], y1=node['eq'], fillcolor="rgba(38, 166, 154, 0.015)", line_width=0, annotation_text="HTF DISCOUNT AREA", annotation_position="bottom left")
        
        # Tarihi Likidite Havuz Bantları (PDH & PDL)
        fig.add_hline(y=node['pdh'], line_color="rgba(255, 235, 59, 0.15)", line_width=1, annotation_text="PDH Pool")
        fig.add_hline(y=node['pdl'], line_color="rgba(255, 235, 59, 0.15)", line_width=1, annotation_text="PDL Pool")
        fig.add_hline(y=node['eq'], line_color="rgba(255, 255, 255, 0.1)", line_width=1, line_dash="dash", annotation_text="Equilibrium")
        
        # Canlı OB (Order Block) ve FVG Dinamik Kutu Çizimleri
        if node["ob"]:
            ob_color = "rgba(38, 166, 154, 0.05)" if "BULLISH" in node["ob"]["type"] else "rgba(239, 83, 80, 0.05)"
            fig.add_shape(type="rect", x0=node["ob"]["time"], x1=df['datetime'].iloc[-1], y0=node["ob"]["bottom"], y1=node["ob"]["top"], fillcolor=ob_color, line_width=0)
        if node["fvg"]:
            fvg_color = "rgba(41, 98, 255, 0.04)" if "BULLISH" in node["fvg"]["type"] else "rgba(255, 109, 0, 0.04)"
            fig.add_shape(type="rect", x0=node["fvg"]["time"], x1=df['datetime'].iloc[-1], y0=node["fvg"]["bottom"], y1=node["fvg"]["top"], fillcolor=fvg_color, line_width=0)

        # Eğer kurallar eşleştiyse hedefleri grafiğe mühürle abi
        if node["bias"] != "WAIT":
            fig.add_hline(y=node["sl_p"], line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text="SL LIMIT")
            fig.add_hline(y=node["tp2_p"], line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text="TP2 FINAL")

        fig.update_layout(template='plotly_dark', paper_bgcolor='#0c0d12', plot_bgcolor='#0c0d12', xaxis_rangeslider_visible=False, height=520, uirevision=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_desk:
        # ==========================================
        # 📋 VERIFICATION CORE CHECKLIST
        # ==========================================
        st.markdown("#### 📋 Matrix Verification")
        st.markdown(f"""
        <div class='panel-box' style='font-family:monospace; font-size:11px; line-height:1.7;'>
            Institutional Killzone: <span class='{"gate-passed" if node["kz"] else "gate-failed"}'>{"✅ OPEN ("+node['session']+")" if node["kz"] else "❌ CLOSED"}</span><br>
            Forex Factory Gate: <span class='{"gate-passed" if not news_blocked else "gate-failed"}'>{"✅ CLEAR" if not news_blocked else "❌ LOCK"}</span><br>
            Live Quote Spread: <span class='{"gate-passed" if spread_pips <= 1.5 else "gate-failed"}'>{spread_pips:.1f} Pips</span><br>
            Correlation Matrix: <span class='{"gate-passed" if not correlation_blocked else "gate-failed"}'>{"✅ STABLE" if not correlation_blocked else "❌ OVERLAP"}</span><br>
            Daily Loss Circuit: <span class='{"gate-passed" if not daily_circuit_lock else "gate-failed"}'>${daily_pnl_sum:.2f} / 3%</span><br>
            Maximum Drawdown Cap: <span class='{"gate-passed" if not total_circuit_lock else "gate-failed"}'>${total_pnl_sum:.2f} / 5%</span>
        </div>
        """, unsafe_allow_html=True)
        
        if news_blocked:
            st.error(f"⚠️ {news_reason}")

        # ==========================================
        # ⚙️ AUTOMATED POSITION RISKING VECTOR
        # ==========================================
        risk_pct = st.number_input("Exposure Unit Risk Vector (%)", value=1.0, step=0.1, key=f"risk_v54_{render_asset}")
        allowed_risk_usd = prop_capital * (risk_pct / 100.0)
        
        # Enstrümanın çarpan büyüklüğüne göre tam lot hesabı kalkanı
        mult_risk = 100 if "XAU" in render_asset or "BTC" in render_asset or "ETH" in render_asset else 10000
        p_distance = abs(node["price"] - node["sl_p"]) * mult_risk
        
        final_lot = allowed_risk_usd / (p_distance * 10 + 1e-9) if p_distance > 0 else 0.1
        final_lot = max(0.01, round(final_lot, 2))
        
        st.markdown(f"""
        <div class='panel-box' style='font-family: monospace; font-size:12px; text-align:center;'>
            Allocated Loss Budget: <span style='color:#ff5a5f;'>${allowed_risk_usd:.2f}</span><br>
            Calculated Core Size: <span style='color:#00ebc7; font-weight:bold;'>{final_lot} Lot</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Mükerrer emir kalkanı taraması abi
        cursor.execute("SELECT COUNT(*) FROM v54_ledger WHERE asset = ? AND status = 'OPEN'", (render_asset,))
        active_trade_count = cursor.fetchone()[0]
        
        # ==========================================
        # 🚀 EMİR MÜHÜRLERİ VE TELEGRAM ALERTER
        # ==========================================
        if node["bias"] != "WAIT" and active_trade_count == 0 and not daily_circuit_lock and not total_circuit_lock and not correlation_blocked and not news_blocked:
            if st.button("MÜHÜRLE VE EMİR GÖNDER", key=f"btn_v54_execute_{render_asset}"):
                # Analytics rasyolarının muhtaç olduğu ham dolar riski veritabanına mühürlenir abi!
                calculated_risk_usd = abs(node["price"] - node["sl_p"]) * final_lot * mult_risk
                
                cursor.execute(
                    "INSERT INTO v54_ledger (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, score, q_class, session, duration_min, close_time, initial_risk_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'OPEN', ?, ?, ?, 0, 'RUNNING', ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M"), render_asset, node["bias"], node["price"], node["sl_p"], node["tp1_p"], node["tp2_p"], final_lot, node["score"], node["q_class"], node["session"], calculated_risk_usd)
                )
                conn.commit()
                
                # Telegram Embedded Bildirim Taslağı
                tg_msg = (
                    f"🏛️ *NEXUS QUANT — SYSTEM EXECUTION DISPATCHED*\n\n"
                    f"🔹 *Asset:* {render_asset} ({node['session']} Session)\n"
                    f"🔹 *Action Vector:* `{node['bias']}` (Grade: {node['q_class']} - {node['score']}/100)\n"
                    f"🔹 *Position Size:* `{final_lot} Lot` (Risked: ${calculated_risk_usd:.2f})\n\n"
                    f"📍 *Entry Price:* {node['price']:.5f}\n"
                    f"🛑 *Stop Loss:* {node['sl_p']:.5f}\n"
                    f"🟢 *Partial TP1:* {node['tp1_p']:.5f}\n"
                    f"🎯 *Final Target TP2:* {node['tp2_p']:.5f}\n\n"
                    f"🔒 _Order registered securely into local SQLite vault._"
                )
                core.send_telegram_notification(tg_msg)
                st.toast("Setup dispatched and telegram alert deployed successfully.", icon="🏛️")
                
        # ==========================================
        # 📒 BACKTEST & VERİ HAVUZU GÖSTERGESİ
        # ==========================================
        st.markdown("##### 📒 Performance Overview")
        df_ledger = pd.read_sql_query("SELECT * FROM v54_ledger WHERE status != 'OPEN' AND status != 'EXPIRED_CANCEL'", conn)
        b_wr, b_pf, b_dd, b_exp = core.run_historical_backtest_matrix(df)
        
        if not df_ledger.empty:
            closed_pnl = df_ledger["pnl"].values
            wins = len(df_ledger[df_ledger["pnl"] > 0])
            wr = (wins / len(df_ledger)) * 100
            p_factor = closed_pnl[closed_pnl > 0].sum() / (abs(closed_pnl[closed_pnl < 0].sum()) + 1e-9)
            
            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[CANLI FORWARD TEST]</b><br>
                Win Rate: <span style='color:#00ebc7;'>%{wr:.1f}</span> | PF: {p_factor:.2f}<br>
                Kümülatif PnL: ${closed_pnl.sum():.2f}
            </div>
            """, unsafe_allow_html=True)
            
            # Canlı Bakiye Gelişim Eğrisi
            equity_curve = prop_capital + np.cumsum(closed_pnl)
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(y=equity_curve, mode='lines+markers', line=dict(color='#00ebc7', width=1.5)))
            fig_eq.update_layout(template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722', height=110, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.markdown(f"""
            <div class='panel-box' style='font-family: monospace; font-size:11px;'>
                <b>[3-YEAR BACKTEST ENGINE]</b><br>
                Est Winrate: <span style='color:#00ebc7;'>%{b_wr:.1f}</span><br>
                Profit Factor: {b_pf:.2f}<br>
                Expectancy: {b_exp:.2f} Pips
            </div>
            """, unsafe_allow_html=True)

    conn.close()
