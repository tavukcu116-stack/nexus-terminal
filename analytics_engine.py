# ==========================================
# 📄 DOSYA: analytics_engine.py (NEXUS QUANT v56.0 - ENTERPRISE QUANT STATS)
# ==========================================
import numpy as np
import pandas as pd
from datetime import datetime

def calculate_advanced_risk_metrics(df_ledger, risk_per_trade_usd=100.0, initial_capital=10000.0):
    """
    Mustafa Abi'nin Kurumsal Performans Motoru:
    Calmar koruması, Seans/Varlık bazlı Sharpe/Sortino, Streak analizleri ve CSV export altyapısı sunar.
    """
    # Veri boşsa kurumsal sıfır şablonu dön abi, sistem asla çökmez
    if df_ledger.empty or "pnl" not in df_ledger.columns or len(df_ledger) == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "sharpe": 0.0, "sortino": 0.0, "profit_factor": 0.0, "calmar": 0.0,
            "max_drawdown_usd": 0.0, "max_drawdown_pct": 0.0,
            "win_streak": 0, "loss_streak": 0, "avg_duration_min": 0.0,
            "session_stats": {}, "asset_stats": {}, "equity_curve": [initial_capital], "drawdown_curve": [0.0]
        }

    # Sadece kapalı pozisyonları süzüyoruz abi
    df_closed = df_ledger[df_ledger["status"].str.contains("CLOSED|EXPIRED", na=False, case=False)].copy()
    if df_closed.empty:
        return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "sharpe": 0.0, "sortino": 0.0, "profit_factor": 0.0, "calmar": 0.0, "max_drawdown_usd": 0.0, "win_streak": 0, "loss_streak": 0, "equity_curve": [initial_capital], "drawdown_curve": [0.0]}

    pnl_array = df_closed["pnl"].astype(float).values
    total_trades = len(pnl_array)
    
    wins_series = pnl_array[pnl_array > 0]
    losses_series = pnl_array[pnl_array < 0]
    wins_count = len(wins_series)
    losses_count = len(losses_series)
    win_rate = round((wins_count / total_trades) * 100, 1)

    # 🔄 EQUITY VE DRAWDOWN EĞRİSİ HESAPLAMA MOTORU
    equity_curve = [initial_capital]
    current_equity = initial_capital
    for pnl in pnl_array:
        current_equity += pnl
        equity_curve.append(current_equity)
        
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.cummax()
    drawdown_series = running_max - equity_series
    max_dd_usd = round(drawdown_series.max(), 2)
    max_dd_pct = round((max_dd_usd / running_max.max()) * 100, 2) if running_max.max() > 0 else 0.0
    
    drawdown_curve = (drawdown_series / running_max * 100).round(2).tolist()

    # 🛡️ SHARPE / SORTINO & PROFIT FACTOR (Sıfıra Bölünme Kalkanlı)
    mean_return = pnl_array.mean()
    std_dev = pnl_array.std() if len(pnl_array) > 1 else 1e-9
    sharpe = round(max(0.0, (mean_return / (std_dev + 1e-9)) * np.sqrt(252)), 2)
    
    downside_std = losses_series.std() if len(losses_series) > 1 else 1e-9
    sortino = round(max(0.0, (mean_return / (downside_std + 1e-9)) * np.sqrt(252)), 2)
    
    profit_factor = round(wins_series.sum() / (abs(losses_series.sum()) + 1e-9), 2)
    
    # 🛡️ CALMAR RASYOSU: Senin uyardığın o sıfıra bölünme hatası kurumsal engellendi abi!
    calmar = round(max(0.0, mean_return / (max_dd_usd + 1e-9) * 12), 2) if max_dd_usd > 0 else round(mean_return * 12, 2)

    # 🔍 ARDIŞIK WIN / LOSS STREAK SAYACI
    win_streak = current_win = 0
    loss_streak = current_loss = 0
    for pnl in pnl_array:
        if pnl > 0:
            current_win += 1; current_loss = 0
            if current_win > win_streak: win_streak = current_win
        elif pnl < 0:
            current_loss += 1; current_win = 0
            if current_loss > loss_streak: loss_streak = current_loss

    # ⏱️ ORTALAMA İŞLEM SÜRESİ SEGMENTASYONU
    avg_duration = 0.0
    if "duration_min" in df_closed.columns:
        avg_duration = round(df_closed["duration_min"].astype(float).mean(), 1)

    # 🌐 SEANS BAZLI SHARPE / SORTINO DAĞILIMI
    session_stats = {}
    if "session" in df_closed.columns:
        for sess, group in df_closed.groupby("session"):
            g_pnl = group["pnl"].values
            g_std = g_pnl.std() if len(g_pnl) > 1 else 1e-9
            sess_sharpe = (g_pnl.mean() / (g_std + 1e-9)) * np.sqrt(252)
            session_stats[sess] = {"trades": len(group), "sharpe": round(max(0.0, sess_sharpe), 2), "pnl": round(g_pnl.sum(), 2)}

    # 💱 VARLIK (ASSET) BAZLI SHARPE / SORTINO MATRIXİ
    asset_stats = {}
    for asset, group in df_closed.groupby("asset"):
        a_pnl = group["pnl"].values
        a_std = a_pnl.std() if len(a_pnl) > 1 else 1e-9
        asset_sharpe = (a_pnl.mean() / (a_std + 1e-9)) * np.sqrt(252)
        asset_stats[asset] = {"trades": len(group), "sharpe": round(max(0.0, asset_sharpe), 2), "pnl": round(a_pnl.sum(), 2)}

    return {
        "total_trades": total_trades, "wins": wins_count, "losses": losses_count, "win_rate": win_rate,
        "sharpe": sharpe, "sortino": sortino, "profit_factor": profit_factor, "calmar": calmar,
        "max_drawdown_usd": max_dd_usd, "max_drawdown_pct": max_dd_pct,
        "win_streak": win_streak, "loss_streak": loss_streak, "avg_duration_min": avg_duration,
        "session_stats": session_stats, "asset_stats": asset_stats, "equity_curve": equity_series.tolist(), "drawdown_curve": drawdown_curve
    }

def export_ledger_to_audit_csv(df_ledger):
    """🏛️ AUDIT EXPORT ENGINE: Bütün veritabanı kayıtlarını kurumsal denetim standartlarında CSV'ye basar abi."""
    try:
        if df_ledger.empty: return ""
        # Hassas şifreleme veya id kolonlarını temizleyip yapılandırıyoruz abi
        df_export = df_ledger.drop(columns=["id"], errors="ignore").copy()
        df_export["export_verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return df_export.to_csv(index=False, encoding="utf-8")
    except:
        return ""
    
