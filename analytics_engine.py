# ==========================================
# 📄 DOSYA: analytics_engine.py (NEXUS QUANT v56.4 - OPTIMIZED)
# ==========================================
import numpy as np
import pandas as pd
from datetime import datetime

# Forex/Kripto için günlük işlem sayısı tahmini (yıllıklaştırma çarpanı)
# Hisse senedi için 252 kullanılır; Forex 24/5 → ~260, Kripto 365
TRADING_DAYS_PER_YEAR = 252


def _empty_metrics(initial_capital: float) -> dict:
    return {
        "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
        "sharpe": 0.0, "sortino": 0.0, "profit_factor": 0.0, "calmar": 0.0,
        "max_drawdown_usd": 0.0, "max_drawdown_pct": 0.0,
        "win_streak": 0, "loss_streak": 0, "avg_duration_min": 0.0,
        "session_stats": {}, "asset_stats": {},
        "equity_curve": [initial_capital], "drawdown_curve": [0.0]
    }


def calculate_advanced_risk_metrics(
    df_ledger: pd.DataFrame,
    risk_per_trade_usd: float = 100.0,
    initial_capital: float = 10_000.0
) -> dict:

    if df_ledger.empty or "pnl" not in df_ledger.columns:
        return _empty_metrics(initial_capital)

    df_closed = df_ledger[
        df_ledger["status"].str.contains("CLOSED|EXPIRED", na=False, case=False)
    ].copy()

    if df_closed.empty:
        return _empty_metrics(initial_capital)

    pnl_array    = df_closed["pnl"].astype(float).values
    total_trades = len(pnl_array)

    wins_series   = pnl_array[pnl_array > 0]
    losses_series = pnl_array[pnl_array < 0]
    wins_count    = len(wins_series)
    losses_count  = len(losses_series)
    win_rate      = round(wins_count / total_trades * 100, 1)

    # ── Equity & Drawdown ──────────────────────────────────────────────────
    equity_curve   = [initial_capital + pnl_array[:i+1].sum() for i in range(total_trades)]
    equity_curve   = [initial_capital] + equity_curve
    equity_s       = pd.Series(equity_curve, dtype=float)
    running_max    = equity_s.cummax()
    drawdown_abs   = running_max - equity_s               # USD drawdown
    max_dd_usd     = round(float(drawdown_abs.max()), 2)

    # Drawdown yüzdesi: başlangıç sermayesine göre (running_max.max() yerine)
    # bu değer prop firm kurallarıyla tutarlıdır
    max_dd_pct = round(max_dd_usd / initial_capital * 100, 2) if initial_capital > 0 else 0.0

    # Drawdown eğrisi (yüzde)
    drawdown_curve = (drawdown_abs / initial_capital * 100).round(2).tolist()

    # ── Sharpe & Sortino ──────────────────────────────────────────────────
    # Yıllıklaştırma: trade başına ortalama getiri * sqrt(yıllık işlem sayısı)
    mean_ret  = float(pnl_array.mean())
    std_dev   = float(pnl_array.std(ddof=1)) if total_trades > 1 else 1e-9

    annualize = np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe    = round(max(0.0, (mean_ret / (std_dev + 1e-9)) * annualize), 2)

    # Sortino: downside std — sadece negatif getirilerden
    if len(losses_series) > 1:
        downside_std = float(losses_series.std(ddof=1))
    else:
        downside_std = 1e-9
    sortino = round(max(0.0, (mean_ret / (downside_std + 1e-9)) * annualize), 2)

    # ── Profit Factor & Calmar ────────────────────────────────────────────
    gross_profit = float(wins_series.sum())   if len(wins_series)   > 0 else 0.0
    gross_loss   = float(abs(losses_series.sum())) if len(losses_series) > 0 else 1e-9
    profit_factor = round(gross_profit / gross_loss, 2)

    # Calmar: ortalama aylık getiri / max drawdown
    # (mean_ret zaten trade başına; *12 ile aylığa değil yıllığa taşımak daha doğru)
    calmar = round(
        max(0.0, (mean_ret * TRADING_DAYS_PER_YEAR) / (max_dd_usd + 1e-9)), 2
    ) if max_dd_usd > 0 else round(mean_ret * TRADING_DAYS_PER_YEAR, 2)

    # ── Streak Sayacı ────────────────────────────────────────────────────
    win_streak = current_win = 0
    loss_streak = current_loss = 0
    for pnl in pnl_array:
        if pnl > 0:
            current_win   += 1; current_loss = 0
            win_streak     = max(win_streak, current_win)
        elif pnl < 0:
            current_loss  += 1; current_win  = 0
            loss_streak    = max(loss_streak, current_loss)

    # ── Ortalama Süre ────────────────────────────────────────────────────
    avg_duration = 0.0
    if "duration_min" in df_closed.columns:
        avg_duration = round(
            pd.to_numeric(df_closed["duration_min"], errors="coerce").mean(), 1
        )

    # ── Seans Bazlı İstatistik ───────────────────────────────────────────
    session_stats: dict = {}
    if "session" in df_closed.columns:
        for sess, group in df_closed.groupby("session"):
            g_pnl = group["pnl"].astype(float).values
            g_mean = g_pnl.mean()
            g_std  = g_pnl.std(ddof=1) if len(g_pnl) > 1 else 1e-9
            g_neg  = g_pnl[g_pnl < 0]
            g_down = g_neg.std(ddof=1) if len(g_neg) > 1 else 1e-9

            session_stats[sess] = {
                "trades":  len(group),
                "sharpe":  round(max(0.0, g_mean / (g_std + 1e-9) * annualize), 2),
                "sortino": round(max(0.0, g_mean / (g_down + 1e-9) * annualize), 2),
                "pnl":     round(float(g_pnl.sum()), 2),
            }

    # ── Varlık Bazlı İstatistik ──────────────────────────────────────────
    asset_stats: dict = {}
    if "asset" in df_closed.columns:
        for asset, group in df_closed.groupby("asset"):
            a_pnl  = group["pnl"].astype(float).values
            a_mean = a_pnl.mean()
            a_std  = a_pnl.std(ddof=1) if len(a_pnl) > 1 else 1e-9
            asset_stats[asset] = {
                "trades": len(group),
                "sharpe": round(max(0.0, a_mean / (a_std + 1e-9) * annualize), 2),
                "pnl":    round(float(a_pnl.sum()), 2),
            }

    return {
        "total_trades":     total_trades,
        "wins":             wins_count,
        "losses":           losses_count,
        "win_rate":         win_rate,
        "sharpe":           sharpe,
        "sortino":          sortino,
        "profit_factor":    profit_factor,
        "calmar":           calmar,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
        "win_streak":       win_streak,
        "loss_streak":      loss_streak,
        "avg_duration_min": avg_duration,
        "session_stats":    session_stats,
        "asset_stats":      asset_stats,
        "equity_curve":     equity_s.tolist(),
        "drawdown_curve":   drawdown_curve,
    }


def export_ledger_to_audit_csv(df_ledger: pd.DataFrame) -> str:
    """
    Tüm ledger'ı denetim için CSV'ye aktarır.
    Hata durumunda boş string yerine hata mesajı döner (sessiz yutma yok).
    """
    if df_ledger.empty:
        return ""
    try:
        df_export = df_ledger.drop(columns=["id"], errors="ignore").copy()
        df_export["export_verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return df_export.to_csv(index=False, encoding="utf-8")
    except Exception as e:
        # Sessiz yutma yerine: üst katmana bilgi ver
        return f"EXPORT_ERROR: {e}"
