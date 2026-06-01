# ==========================================
# 📄 DOSYA: terminal.py (NEXUS QUANT v56.0 - ENTERPRISE DASHBOARD)
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime
from backend_core import (
    extract_quant_smc_matrix, get_db_connection, get_live_spread_data,
    check_economic_news_timeline, check_live_circuit_barriers,
    manage_v55_autonomous_engine, calculate_position_size, manage_v54_positions
)
from analytics_engine import calculate_advanced_risk_metrics, export_ledger_to_audit_csv

# 1. 🏛️ STREAMLIT PAGE CONFIG & THEME LOCKUP
st.set_page_config(page_title="NEXUS QUANT v56.0", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .reportview-container { background: #0A0E17; color: #E2E8F0; }
    .stMetric { background: #151D2A; padding: 15px; border-radius: 8px; border: 1px solid #233145; }
    .status-online { color: #10B981; font-weight: bold; }
    .status-offline { color: #EF4444; font-weight: bold; }
    </style>
""", unsafe_allowed_index=True)

# 2. ⚡ CACHE TEMİZLEME MOTORU (Senin Uyardığın Nokta Abi)
if st.sidebar.button("♻️ FORCE FLUSH (CACHE TEMİZLE)"):
    st.cache_data.clear()
    st.sidebar.success("Ön bellek tamamen havaya uçuruldu abi!")
    st.rerun()

st.title("🏛️ NEXUS QUANT v56.0 — INDUSTRIAL ALGO TERMINAL")

# 3. 🌐 SYSTEM HEALTH & API STATUS SIGNALS
st.sidebar.header("🌐 Core System Status")
twelve_key = os.getenv("TWELVE_DATA_API_KEY")
tg_token = os.getenv("TELEGRAM_BOT_TOKEN")

tdata_status = "<span class='status-online'>ONLINE</span>" if twelve_key and twelve_key != "MOCK_KEY" else "<span class='status-offline'>OFFLINE</span>"
tg_status = "<span class='status-online'>ONLINE</span>" if tg_token else "<span class='status-offline'>OFFLINE</span>"

st.sidebar.markdown(f"Twelve Data: {tdata_status}", unsafe_allowed_index=True)
st.sidebar.markdown(f"Telegram Bot: {tg_status}", unsafe_allowed_index=True)

# Global Ayarlar
capital = st.sidebar.number_input("Kasa Sermayesi ($)", min_value=100.0, value=10000.0, step=500.0)
risk_pct = st.sidebar.slider("İşlem Başı Risk (%R)", 0.25, 5.0, 1.0, 0.25)
selected_asset = st.sidebar.selectbox("Varlık (Asset)", ["EUR/USD", "GBP/USD", "XAU/USD", "NASDAQ"])

# 4. 📈 VERİ AKIŞI VE SÜZGEÇ TETİKLERİ
node = extract_quant_smc_matrix(selected_asset)

if node is None:
    st.error("⚠️ Sunucudan canlı mum verisi akmıyor abi! Bağlantıları veya parite kodunu kontrol et.")
else:
    # Arka planda pozisyon takip çarklarını çalıştır abi
    manage_v54_positions(selected_asset, node["df"])
    
    spread, bid, ask = get_live_spread_data(selected_asset)
    news_blocked, news_reason = check_economic_news_timeline(selected_asset)
    circuit_blocked, circuit_reason = check_live_circuit_barriers(selected_asset, capital)
    
    # Hesaplanan dinamik löt miktarı
    final_lot = calculate_position_size(capital, risk_pct, node["price"], node["sl_p"], selected_asset)
    
    # 🌟 OTONOM MOTOR TETİĞİ
    manage_v55_autonomous_engine(selected_asset, node, final_lot, circuit_blocked, False, False, news_blocked, capital)

    # 5. 🚨 CANLI AÇIK POZİSYON PANELİ (Eksik Kapatıldı Abi)
    st.subheader("🚨 Active Open Positions (Canlı Takip)")
    conn = get_db_connection()
    df_live = pd.read_sql_query("SELECT * FROM v54_ledger WHERE status = 'OPEN'", conn)
    conn.close()
    
    if df_live.empty:
        st.info("Şu anda otonom motor tarafından açılmış aktif bir canlı pozisyon yok abi. Pusuda bekleniyor.")
    else:
        st.dataframe(df_live, use_container_width=True)

    # 6. 📊 ÜST METRİK MATRİXİ
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("Live Price", f"{node['price']:.5f}", f"Spread: {spread} Pips")
    with col2: st.metric("SMC Score", f"{node['score']}/100", f"Grade: {node['q_class']}")
    with col3: st.metric("Autonomous Bias", node["bias"], f"Action: {node['action']}")
    with col4: st.metric("Calculated Lot", f"{final_lot:.2f} Lots", f"Risk: %{risk_pct}")
    with col5: st.metric("Dinamik Math RR", f"{node['rr']:.1f} R", "Real Risk Metric")

    # 7. 🎛️ EMNİYET VE DEVRE KESİCİ DURUMLARI
    st.subheader("🛡️ Algorithmic Circuit Breakers")
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        if news_blocked: st.error(f"🛑 NEWS BARRIER: {news_reason}")
        else: st.success("🟢 NEWS GATE: CLEAR (Haber kilidi temiz)")
    with c_col2:
        if circuit_blocked: st.error(f"🛑 ACCOUNT SAFETY LOCK: {circuit_reason}")
        else: st.success("🟢 ACCOUNT GATE: CLEAR (Hesap limiti ve korumalar güvenli)")

    # 8. 📊 ADVANCED TRADINGVIEW PLOTLY GRAPHIC ENGINE (Kutular ve Kırılımlar Buraya Çiziliyor Abi!)
    st.subheader(f"📈 {selected_asset} Interactive SMC Structure Chart")
    df = node["df"]
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="Price Action"
    )])

    # 🟢 FVG Kutusu Çizimi (Eksik Kapatıldı)
    if node["fvg"]:
        f_color = "rgba(16, 185, 129, 0.15)" if "BULLISH" in node["fvg"]["type"] else "rgba(239, 68, 68, 0.15)"
        fig.add_shape(type="rect",
            x0=df['datetime'].iloc[-20], y0=node["fvg"]["bottom"],
            x1=df['datetime'].iloc[-1], y1=node["fvg"]["top"],
            line=dict(width=0), fillcolor=f_color, name=node["fvg"]["type"]
        )

    # 🔵 OB Kutusu Çizimi (Eksik Kapatıldı)
    if node["ob"]:
        ob_color = "rgba(59, 130, 246, 0.2)" if "BULLISH" in node["ob"]["type"] else "rgba(245, 158, 11, 0.2)"
        fig.add_shape(type="rect",
            x0=node["ob"]["time"], y0=node["ob"]["bottom"],
            x1=df['datetime'].iloc[-1], y1=node["ob"]["top"],
            line=dict(dash="dot", width=1, color="blue"), fillcolor=ob_color, name=node["ob"]["type"]
        )

    # 🟡 PDH/PDL & Equilibrium Çizgileri
    fig.add_hline(y=node["pdh"], line_color="purple", line_dash="dash", annotation_text="PDH Seviyesi")
    fig.add_hline(y=node["pdl"], line_color="purple", line_dash="dash", annotation_text="PDL Seviyesi")
    fig.add_hline(y=node["eq"], line_color="cyan", line_dash="dot", annotation_text="Equilibrium (Denge)")

    # 🔴 BOS / CHOCH Kırılım Çizgileri ve Entry/SL/TP Seviyeleri
    if node["bias"] != "WAIT":
        fig.add_hline(y=node["sl_p"], line_color="red", line_width=2, annotation_text="STRUCTURAL SL")
        fig.add_hline(y=node["tp1_p"], line_color="green", line_dash="dash", annotation_text="TARGET TP1")
        fig.add_hline(y=node["tp2_p"], line_color="darkgreen", line_width=2, annotation_text="TARGET TP2 (MAIN)")

    fig.update_layout(theme="slate", height=600, xcalendar="gregorian", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# 9. 📊 ADVANCED PERFORMANCE & METRIC SHARDS (İstatistik Paneli)
st.header("📊 Enterprise Quantitative Analytics")
conn = get_db_connection()
df_ledger = pd.read_sql_query("SELECT * FROM v54_ledger", conn)
conn.close()

metrics = calculate_advanced_risk_metrics(df_ledger, initial_capital=capital)

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric("Total Trades Closed", metrics["total_trades"])
    st.metric("Win Rate (Başarı Oranı)", f"%{metrics['win_rate']}")
with m_col2:
    st.metric("Sharpe Ratio (Yıllık)", metrics["sharpe"])
    st.metric("Sortino Ratio", metrics["sortino"])
with m_col3:
    st.metric("Profit Factor (Karlılık)", metrics["profit_factor"])
    st.metric("Calmar Ratio (Safety)", metrics["calmar"])
with m_col4:
    st.metric("Max Drawdown ($)", f"${metrics['max_drawdown_usd']}")
    st.metric("Win/Loss Streak (Seri)", f"+{metrics['win_streak']} / -{metrics['loss_streak']}")

# 📂 AUDIT CSV EXPORT CORNER
st.subheader("📂 Institutional Audit Export")
csv_data = export_ledger_to_audit_csv(df_ledger)
if csv_data:
    st.download_button(label="📥 DOWNLOAD VERIFIED AUDIT CSV (Denetim Raporu)", data=csv_data, file_name="nexus_verified_ledger.csv", mime="text/csv")

# 🛠️ MANUEL TRADE GİRİŞ PANELİ (Eksik Kapatıldı)
st.sidebar.markdown("---")
st.sidebar.header("➕ Manual Trade Injection")
with st.sidebar.form("manual_trade_form"):
    m_asset = st.selectbox("Asset", ["EUR/USD", "GBP/USD", "XAU/USD", "NASDAQ"])
    m_type = st.selectbox("Direction", ["BUY", "SELL"])
    m_entry = st.number_input("Entry Price", value=1.0000)
    m_pnl = st.number_input("Net PnL ($)", value=0.0)
    if st.form_submit_button("Deftere Elle İşle"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO v54_ledger (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status, score, q_class, session) VALUES (?, ?, ?, ?, 0, 0, 0, 0.1, ?, 'CLOSED_MANUAL', 100, 'A+', 'LONDON')",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), m_asset, m_type, m_entry, m_pnl)
        )
        conn.commit()
        conn.close()
        st.success("İşlem ledger'a elle enjekte edildi abi!")
        st.rerun()

# 📑 TÜM VAULT DEFTERİ GÖRÜNTÜLEYİCİ
st.subheader("📑 Internal Ledger Vault Data Log")
st.dataframe(df_ledger.iloc[::-1], use_container_width=True)

