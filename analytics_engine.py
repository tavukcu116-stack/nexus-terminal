# ==========================================
# 📄 DOSYA: analytics_engine.py (NEXUS QUANT v54.2 - PERFORMANCE ANALYTICS ENGINE)
# ==========================================
import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

DB_FILE = "nexus_v54_vault.db"

def load_closed_trades():
    """Veritabanından sadece kapanmış gerçek işlemleri okur."""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT * FROM v54_ledger WHERE status IN ('CLOSED_SL', 'CLOSED_TP', 'EXPIRED_CANCEL') ORDER BY id ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Matematiksel hesaplamalar için veri tiplerini sabitleyelim
        if not df.empty:
            df['pnl'] = df['pnl'].astype(float)
            df['entry'] = df['entry'].astype(float)
            df['sl'] = df['sl'].astype(float)
            df['tp2'] = df['tp2'].astype(float)
            df['score'] = df['score'].astype(int)
            # Gerçekleşen RR hesabı
            df['realized_rr'] = abs(df['tp2'] - df['entry']) / (abs(df['entry'] - df['sl']) + 1e-9)
        return df
    except Exception as e:
        st.error(f"Veritabanı Okuma Hatası: {e}")
        return pd.DataFrame()

def load_open_trades():
    """Açık pozisyonları izole etmek için veritabanını tarar."""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT timestamp, asset, type, entry, sl, tp2, lot, score, q_class, session FROM v54_ledger WHERE status = 'OPEN' ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

# 📊 1. GENEL METRİKLER MOTORU
def calculate_advanced_metrics(df):
    if df.empty:
        return None
        
    pnl_series = df['pnl'].values
    total_trades = len(df)
    
    winning_trades = df[df['pnl'] > 0]
    losing_trades = df[df['pnl'] <= 0]
    
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    
    win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0.0
    
    gross_profit = winning_trades['pnl'].sum()
    gross_loss = abs(losing_trades['pnl'].sum())
    profit_factor = gross_profit / (gross_loss + 1e-9) if gross_loss > 0 else gross_profit
    
    avg_win = winning_trades['pnl'].mean() if num_wins > 0 else 0.0
    avg_loss = losing_trades['pnl'].mean() if num_losses > 0 else 0.0
    
    net_profit = df['pnl'].sum()
    avg_rr = df['realized_rr'].mean()
    
    # Expectancy Formula: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
    loss_rate = 1 - (win_rate / 100)
    expectancy = ((win_rate / 100) * avg_win) - (loss_rate * abs(avg_loss))
    
    # Ardışık Galibiyet / Mağlubiyet Serisi Taraması (Streak Engine)
    consecutive_wins = max_streak = 0
    consecutive_losses = min_streak = 0
    for pnl in pnl_series:
        if pnl > 0:
            consecutive_wins += 1
            max_streak = max(max_streak, consecutive_wins)
            consecutive_losses = 0
        else:
            consecutive_losses += 1
            min_streak = max(min_streak, consecutive_losses)
            consecutive_wins = 0

    # Gelişmiş Risk/Getiri Rasyoları (Sharpe, Sortino, Calmar)
    # Günlük risksiz getiri oranı kurumsal standartta 0 kabul edilir.
    returns = df['pnl'].values
    avg_return = np.mean(returns)
    std_dev = np.std(returns) + 1e-9
    sharpe = (avg_return / std_dev) * np.sqrt(252) if len(returns) > 1 else 0.0
    
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns) + 1e-9
    sortino = (avg_return / downside_std) * np.sqrt(252) if len(downside_returns) > 1 else 0.0
    
    # Kümülatif Bakiye ve Drawdown Matrisi
    initial_balance = 10000.0 # Prop Firm standardı referans bakiye
    equity_curve = initial_balance + np.cumsum(returns)
    
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (running_max - equity_curve) / running_max * 100
    max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
    current_dd = drawdowns[-1] if len(drawdowns) > 0 else 0.0
    
    calmar = (net_profit / (max_dd / 100 + 1e-9)) if max_dd > 0 else net_profit
    
    return {
        "total_trades": total_trades, "num_wins": num_wins, "num_losses": num_losses,
        "win_rate": round(win_rate, 2), "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
        "net_profit": round(net_profit, 2), "avg_rr": round(avg_rr, 2),
        "expectancy": round(expectancy, 2), "streak_win": max_streak, "streak_loss": min_streak,
        "sharpe": round(sharpe, 2), "sortino": round(sortino, 2), "calmar": round(calmar, 2),
        "max_dd": round(max_dd, 2), "current_dd": round(current_dd, 2), "equity_curve": equity_curve
    }

# 🧠 2. RISK OF RUIN ENGINE
def run_risk_of_ruin(win_rate, avg_rr, risk_pct=1.0):
    wr = win_rate / 100.0
    if wr >= 1.0 or wr <= 0.0:
        return 0.0
    
    # Standart RoR Formülü: ((1 - Edge) / (1 + Edge))^Units
    # Edge basitleştirilmiş haliyle WR ve RR oranından çıkarılır.
    loss_ratio = 1.0 - wr
    try:
        # Kurumsal formülasyon: Batma olasılığı tespiti
        ruin_prob = ((loss_ratio) / (wr * avg_rr + 1e-9)) ** (100.0 / risk_pct)
        return round(min(100.0, max(0.0, ruin_prob * 100)), 2)
    except:
        return 0.0

# 🎲 3. MONTE CARLO SIMULATION ENGINE
def run_monte_carlo_matrix(df, simulations=500, horizon=30):
    if len(df) < 10:
        return None # Güvenilir sonuç için alt sınır barajı abi
        
    pnl_pool = df['pnl'].values
    initial_balance = 10000.0
    all_trajectories = []
    ending_balances = []
    max_dd_list = []
    
    for _ in range(simulations):
        # Gerçek işlemlerden rastgele örnekleme yapılıyor (Resampling with replacement)
        sampled_returns = np.random.choice(pnl_pool, size=horizon, replace=True)
        trajectory = initial_balance + np.cumsum(sampled_returns)
        all_trajectories.append(trajectory)
        ending_balances.append(trajectory[-1])
        
        # Simülasyon içi drawdown hesabı
        run_max = np.maximum.accumulate(trajectory)
        dds = (run_max - trajectory) / run_max * 100
        max_dd_list.append(np.max(dds))
        
    return {
        "trajectories": all_trajectories,
        "worst_dd": round(np.max(max_dd_list), 2),
        "median_outcome": round(np.median(ending_balances) - initial_balance, 2)
    }

# 🛡️ 4. STRATEGIC EDGE DETECTOR
def run_edge_detector_guard(df, metrics):
    if len(df) < 10:
        return "🟢 EDGE HEALTHY (CALIBRATING)"
        
    # Son 30 veya mevcut maksimum veriyi süzüyoruz
    recent_df = df.tail(30)
    recent_pnl = recent_df['pnl'].values
    recent_wins = len(recent_df[recent_df['pnl'] > 0])
    recent_wr = (recent_wins / len(recent_df)) * 100
    
    rec_gross_prof = recent_df[recent_df['pnl'] > 0]['pnl'].sum()
    rec_gross_loss = abs(recent_df[recent_df['pnl'] <= 0]['pnl'].sum())
    recent_pf = rec_gross_prof / (rec_gross_loss + 1e-9)
    
    # Alarm Matrix tetikleyicileri
    alarm_score = 0
    if recent_wr < 45.0: alarm_score += 1
    if recent_pf < 1.0: alarm_score += 1
    if metrics['current_dd'] > 4.0: alarm_score += 1
    if metrics['expectancy'] < 0: alarm_score += 2
    
    if alarm_score >= 3:
        return "🔴 EDGE DEGRADING (RISK REDUCTION REQUIRED)"
    elif alarm_score >= 1:
        return "🟡 EDGE WEAKENING (MONITOR SESSIONS)"
    else:
        return "🟢 EDGE HEALTHY"

# 🎛️ 5. STREAMLIT UI RENDER PLATFORMU
def render_performance_dashboard():
    st.set_page_config(page_title="NEXUS QUANT v54.2 - ANALYTICS", layout="wide", initial_sidebar_state="collapsed")
    
    # Koyu Kurumsal Tema Enjeksiyonu
    st.markdown("""
        <style>
            .stApp { background-color: #0B0E11; color: #EAECEF; }
            h1, h2, h3 { color: #F0B90B; font-family: 'Courier New', monospace; }
            .metric-box { background-color: #181A20; padding: 15px; border-radius: 6px; border: 1px solid #2B2F36; }
        </style>
    """, unsafe_style_html=True)
    
    st.title("🏛️ NEXUS QUANT v54.2 — PERFORMANCE ANALYTICS DASHBOARD")
    st.write(f"Sistem Raporlama Saati (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    
    df_closed = load_closed_trades()
    df_open = load_open_trades()
    
    # 🚨 CANLI AÇIK POZİSYON PANELİ
    st.subheader("📡 Active Unhedged Orders (Açık Pozisyonlar)")
    if not df_open.empty:
        st.dataframe(df_open, use_container_width=True)
    else:
        st.info("Piyasada aktif açık emir bulunmuyor. Kalkanlar devrede.")
        
    if df_closed.empty:
        st.warning("Veritabanında analiz edilecek kapanmış işlem geçmişi bulunamadı abi. Pozisyonların kapanması bekleniyor.")
        return
        
    metrics = calculate_advanced_metrics(df_closed)
    
    # 📊 EXECUTIVE SUMMARY & EDGE HEALTH STATUS
    edge_status = run_edge_detector_guard(df_closed, metrics)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🛡️ Strategic Edge Health Monitor")
        if "🔴" in edge_status: st.error(edge_status)
        elif "🟡" in edge_status: st.warning(edge_status)
        else: st.success(edge_status)
        
    with col2:
        st.subheader("🎲 Risk of Ruin Panel")
        risk_input = st.number_input("İşlem Başı Risk (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        ror_value = run_risk_of_ruin(metrics['win_rate'], metrics['avg_rr'], risk_input)
        if ror_value > 20.0: st.error(f"RoR: %{ror_value} (YÜKSEK İFLAS RİSKİ)")
        else: st.metric(label="Risk of Ruin (%)", value=f"%{ror_value}")

    # METRİK KARTLARI PANELİ
    st.subheader("📊 Executive Performance Analytics")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Total / Wins / Losses", f"{metrics['total_trades']} | {metrics['num_wins']} | {metrics['num_losses']}")
        st.metric("Win Rate (%)", f"%{metrics['win_rate']}")
        st.metric("Profit Factor", f"{metrics['profit_factor']}")
    with m_col2:
        st.metric("Net Profit (Points/$)", f"{metrics['net_profit']}")
        st.metric("Expectancy (Beklenti)", f"{metrics['expectancy']}")
        st.metric("Average RR", f"{metrics['avg_rr']} RR")
    with m_col3:
        st.metric("Average Win / Loss", f"{metrics['avg_win']} / {metrics['avg_loss']}")
        st.metric("Streak (Win/Loss)", f"{metrics['streak_win']} / {metrics['streak_loss']}")
        st.metric("Max / Current Drawdown", f"%{metrics['max_dd']} / %{metrics['current_dd']}")
    with m_col4:
        st.metric("Sharpe Ratio", f"{metrics['sharpe']}")
        st.metric("Sortino Ratio", f"{metrics['sortino']}")
        st.metric("Calmar Ratio", f"{metrics['calmar']}")

    # 📈 BAKIYE VE EQUITY BÜYÜME GRAFİĞİ
    st.subheader("📈 Institutional Equity Curve ($10,000 Starting Capital)")
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(y=metrics['equity_curve'], mode='lines+markers', name='Equity Curve', line=dict(color='#F0B90B', width=2)))
    fig_eq.update_layout(template='plotly_dark', paper_bgcolor='#111518', plot_bgcolor='#111518', margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_eq, use_container_width=True)

    # 🔬 MATRİS VE SEGMENT ANALİZLERİ (TABLOLAR)
    st.subheader("🔬 Advanced Segment Matrices")
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Setup Quality", "⏳ Session Node", "💱 Asset Analytics", "🛠️ Strategy Components"])
    
    # Helper lambda function for tables
    def build_matrix_row(sub_df, name):
        if sub_df.empty: return [name, 0, "%0.0", 0.0, 0.0, 0.0]
        t_tot = len(sub_df)
        t_win = len(sub_df[sub_df['pnl'] > 0])
        t_wr = (t_win / t_tot) * 100
        t_pf = sub_df[sub_df['pnl'] > 0]['pnl'].sum() / (abs(sub_df[sub_df['pnl'] <= 0]['pnl'].sum()) + 1e-9)
        t_rr = abs(sub_df['tp2'] - sub_df['entry']) / (abs(sub_df['entry'] - sub_df['sl']) + 1e-9)
        return [name, t_tot, f"%{round(t_wr,1)}", round(t_pf,2), round(t_rr.mean(),2), round(sub_df['pnl'].sum(),2)]

    with tab1:
        # 3. Setup Quality Table
        g_ap = df_closed[df_closed['score'] >= 90]
        g_a = df_closed[(df_closed['score'] >= 80) & (df_closed['score'] < 90)]
        g_b = df_closed[(df_closed['score'] >= 70) & (df_closed['score'] < 70)]
        
        setup_data = [build_matrix_row(g_ap, "A+ (90-100)"), build_matrix_row(g_a, "A (80-89)"), build_matrix_row(g_b, "B (70-79)")]
        st.table(pd.DataFrame(setup_data, columns=["Setup Grade", "Trades", "Win Rate", "Profit Factor", "Avg RR", "Net Profit"]))

    with tab2:
        # 4. Session Table
        s_asia = df_closed[df_closed['session'] == 'ASIA']
        s_lon = df_closed[df_closed['session'] == 'LONDON']
        s_ny = df_closed[df_closed['session'] == 'NEW YORK']
        
        session_data = [build_matrix_row(s_asia, "Asia"), build_matrix_row(s_lon, "London"), build_matrix_row(s_ny, "New York")]
        st.table(pd.DataFrame(session_data, columns=["Session", "Trades", "WR", "PF", "Avg RR", "Net PnL"]))

    with tab3:
        # 5. Asset Table
        assets = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD", "ETHUSD", "NASDAQ", "US30"]
        asset_data = []
        for pair in assets:
            clean_sym = pair.replace("USD", "").replace("/", "")
            sub_asset = df_closed[df_closed['asset'].str.contains(clean_sym, case=False, na=False)]
            asset_data.append(build_matrix_row(sub_asset, pair))
        st.table(pd.DataFrame(asset_data, columns=["Asset", "Trades", "WR", "PF", "Avg RR", "Net PnL"]))

    with tab4:
        # 6. Strategy Components Table
        components = ["Fresh OB", "Mitigated OB", "FVG", "Sweep", "BOS", "CHOCH"]
        comp_data = []
        for comp in components:
            # Not: ledger içindeki 'direction' veya 'status' sütunlarından değil, 'q_class' veya log metinlerinden ayrıştırma yapılır.
            # v54 core yapısında 'direction' veya 'type' verisine göre akış filtrelenir.
            sub_comp = df_closed[df_closed['direction'].str.contains(comp, case=False, na=False)] if 'direction' in df_closed.columns else pd.DataFrame()
            if sub_comp.empty and comp == "FVG":
                sub_comp = df_closed[df_closed['q_class'] != 'WAIT'] # Fallback node
            c_row = build_matrix_row(sub_comp, comp)
            comp_data.append(c_row[:5]) # İstenen sütun sayısı 5
        st.table(pd.DataFrame(comp_data, columns=["Component", "Trades", "WR", "PF", "Avg RR"]))

    # 🎲 6. MONTE CARLO PANELİ
    st.subheader("🎲 Monte Carlo Simulator (500 Run Simulation Matrix)")
    mc_results = run_monte_carlo_matrix(df_closed, simulations=500, horizon=30)
    if mc_results:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Worst Case Drawdown Prediction", f"%{mc_results['worst_dd']}")
        with col_m2:
            st.metric("Median Projected Return Outcome", f"{mc_results['median_outcome']} Points/$")
            
        fig_mc = go.Figure()
        for traj in mc_results['trajectories'][:60]: # Görsel hafiflik için 60 çizgiyi çiziyoruz
            fig_mc.add_trace(go.Scatter(y=traj, mode='lines', line=dict(width=1), opacity=0.25, showlegend=False))
        fig_mc.update_layout(template='plotly_dark', paper_bgcolor='#111518', plot_bgcolor='#111518', title="Equity Curves Horizon Projections")
        st.plotly_chart(fig_mc, use_container_width=True)
    else:
        st.info("Monte Carlo simülasyonunun ve risk dağılımının çalışabilmesi için kurumsal sınır olan minimum 10 adet kapanmış işlem verisi birikmelidir abi.")

if __name__ == "__main__":
    render_performance_dashboard()
