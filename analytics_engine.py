# ==========================================
# 📄 DOSYA: analytics_engine.py (NEXUS QUANT v64.0 - LITE STATS)
# ==========================================
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_pure_metrics(signals_list):
    """
    Mustafa Abi'nin Safkan Analitik Motoru:
    Sadece Win Rate, Ortalama RR, Son 30 Sinyal Takibi ve Aylık Performansı hesaplar.
    """
    if not signals_list or len(signals_list) == 0:
        return {
            "win_rate": 0.0,
            "avg_rr": 0.0,
            "last_30_signals": [],
            "monthly_performance": {}
        }
    
    # Listeyi DataFrame'e çevirip hızlıca süzüyoruz abi
    df = pd.DataFrame(signals_list)
    total_signals = len(df)
    
    # 1. Win Rate Hesaplama (Puanı 75 ve üzeri olan başarılı kurulumların oranı)
    passed_setups = df[df["score"] >= 75]
    win_rate = round((len(passed_setups) / total_signals) * 100, 1) if total_signals > 0 else 0.0
    
    # 2. Ortalama RR Hesaplama
    avg_rr = round(df["rr"].mean(), 1) if "rr" in df.columns else 0.0
    
    # 3. Son 30 Sinyal İzolatörü
    last_30 = signals_list[-30:] if len(signals_list) > 30 else signals_list
    # Ters çeviriyoruz ki en yeni sinyal en üstte görünsün abi
    last_30_reversed = list(reversed(last_30))
    
    # 4. Aylık Performans Dağılımı (Aylara göre toplam sinyal ve kaliteleri)
    monthly_perf = {}
    if "timestamp" in df.columns:
        df["month"] = df["timestamp"].apply(lambda x: x.strftime("%Y-%m") if isinstance(x, datetime) else str(x)[:7])
        for month, group in df.groupby("month"):
            monthly_perf[month] = {
                "total_signals": len(group),
                "premium_count": len(group[group["score"] >= 85]),
                "normal_count": len(group[(group["score"] >= 75) & (group["score"] < 85)])
            }
            
    return {
        "win_rate": win_rate,
        "avg_rr": avg_rr,
        "last_30_signals": last_30_reversed,
        "monthly_performance": monthly_perf
    }
