# ==========================================
# 📄 DOSYA: analytics_engine.py (NEXUS QUANT v55.1 - FIXED METRICS)
# ==========================================
import numpy as np
import pandas as pd

def calculate_advanced_risk_metrics(pnl_array, risk_per_trade_usd=100.0):
    """
    Mustafa Abi'nin Kurumsal Risk Denetim Motoru:
    Sharpe, Sortino, Realized RR ve Blok Bootstrap Monte Carlo Simülasyonu çalıştırır.
    """
    if len(pnl_array) == 0:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "realized_rr": 0.0,
            "monte_carlo_fail_prob": 0.0
        }
        
    pnl_series = pd.Series(pnl_array)
    
    # 🌟 KRİTİK ENJEKSİYON: Senin yakaladığın wins ve losses listeleri tam burada hesaplanıyor abi!
    wins_list = pnl_series[pnl_series > 0]
    losses_list = pnl_series[pnl_series < 0]
    
    total_trades = len(pnl_series)
    wins_count = len(wins_list)
    losses_count = len(losses_list)
    win_rate = (wins_count / total_trades) * 100 if total_trades > 0 else 0.0
    
    # Ortalama ve Standart Sapma Hesaplamaları
    mean_return = pnl_series.mean()
    std_dev = pnl_series.std() if len(pnl_series) > 1 else 1e-9
    
    # Sharpe Rasyosu (Risk Free Rate = 0 baz alınmıştır)
    sharpe_ratio = (mean_return / (std_dev + 1e-9)) * np.sqrt(252)
    
    # Sortino Rasyosu (Sadece negatif getirilerin standart sapması)
    downside_std = losses_list.std() if len(losses_list) > 1 else 1e-9
    sortino_ratio = (mean_return / (downside_std + 1e-9)) * np.sqrt(252)
    
    # Realized RR (Gerçekleşen Risk/Ödül Oranı)
    realized_rr = mean_return / (risk_per_trade_usd + 1e-9)
    
    # Monte Carlo Simulation (Blok Bootstrap - 1000 Döngü)
    fail_count = 0
    sim_runs = 1000
    sequence_length = 30
    
    for _ in range(sim_runs):
        simulated_sequence = np.random.choice(pnl_array, size=sequence_length, replace=True)
        cumulative_pnl = np.cumsum(simulated_sequence)
        
        if np.any(cumulative_pnl < -(risk_per_trade_usd * 5)):
            fail_count += 1
            
    monte_carlo_fail_prob = (fail_count / sim_runs) * 100
    
    # 🌟 MÜHÜRLÜ SÖZLÜK YAPISI: Artık ön yüzdeki o satır asla KeyError vermez abi!
    return {
        "total_trades": total_trades,
        "wins": wins_count,
        "losses": losses_count,
        "win_rate": round(win_rate, 1),
        "sharpe": round(max(0.0, sharpe_ratio), 2),
        "sortino": round(max(0.0, sortino_ratio), 2),
        "realized_rr": round(realized_rr, 2),
        "monte_carlo_fail_prob": round(monte_carlo_fail_prob, 2)
    }
