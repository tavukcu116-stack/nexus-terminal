# ==========================================
# 📄 DOSYA: core/indicators.py (Gerçek Matematik Motoru)
# ==========================================
import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    if len(series) < period + 1:
        return 50.0
    delta = pd.Series(series).diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2)

def calculate_emas(series):
    if len(series) < 50:
        return series[-1], series[-1]
    s = pd.Series(series)
    ema20 = s.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = s.ewm(span=50, adjust=False).mean().iloc[-1]
    return round(ema20, 5), round(ema50, 5)

def calculate_atr(df, period=14):
    if len(df) < period + 1:
        return 0.001
    high_low = df['high'] - df['low']
    high_cp = abs(df['high'] - df['close'].shift(1))
    low_cp = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return round(tr.rolling(period).mean().iloc[-1], 5)
