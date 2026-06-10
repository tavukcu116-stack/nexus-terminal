import pandas as pd
import numpy as np

class SMCEngine:
    def _init_(self, swing_window=20):
        """
        SMC Analiz Motoru.
        swing_window: Likidite havuzlarini belirlemek icin geriye donuk bakilacak minimum mum sayisi.
        """
        self.swing_window = swing_window

    def find_swing_points(self, df):
        """
        Piyasadaki gercek kurumsal Tepe (Swing High) ve Dip (Swing Low) noktalarini bulur.
        Siradan yuksek/dusuk seviyeleri degil, piyasanin donus yaptigi ana likidite havuzlarini secer.
        """
        df['Swing_High'] = df['high'].rolling(window=self.swing_window, center=True).max()
        df['Swing_Low'] = df['low'].rolling(window=self.swing_window, center=True).min()
        return df

    def detect_true_liquidity_sweep(self, df):
        """
        EKIN YÜZBAŞIOĞLU STRATEJISI - KRITIK FILTRE:
        Fiyat eski bir tepenin uzerine ciktiginda bu bir yukselis sinyali mi yoksa stop patlatma mi?
        Gercek bir Likidite Avini (True Sweep) dogrulamak icin:
        1. Anlik mumun en yuksek degeri (High), gecmis Swing High'i asmali.
        2. Mum kapanisi (Close), kesinlikle o Swing High seviyesinin ALTINDA olmali (Igne birakmali).
        """
        last_row = df.iloc[-1]
        prev_rows = df.iloc[:-1]
        
        # Son 50 mumun en yuksek ve en dusuk likidite seviyelerini koridor olarak aliyoruz
        recent_highest_liquidity = prev_rows['high'].max()
        recent_lowest_liquidity = prev_rows['low'].min()
        
        current_high = last_row['high']
        current_low = last_row['low']
        current_close = last_row['close']
        
        sweep_status = "NONE"
        captured_level = None
        
        # Buy-Side Liquidity Sweep (Ayilar icin tuzak - Satis Firsati)
        if current_high > recent_highest_liquidity and current_close < recent_highest_liquidity:
            # Mumun biraktigi igne oranini kontrol et (Igne boyu, mumun toplam boyunun en az %30'u olmali)
            candle_range = current_high - current_low
            wick_size = current_high - max(last_row['open'], current_close)
            if candle_range > 0 and (wick_size / candle_range) >= 0.30:
                sweep_status = "BUY_SIDE_LIQUIDITY_SWEPT"
                captured_level = recent_highest_liquidity
                
        # Sell-Side Liquidity Sweep (Bogalar icin tuzak - Alis Firsati)
        elif current_low < recent_lowest_liquidity and current_close > recent_lowest_liquidity:
            candle_range = current_high - current_low
            wick_size = min(last_row['open'], current_close) - current_low
            if candle_range > 0 and (wick_size / candle_range) >= 0.30:
                sweep_status = "SELL_SIDE_LIQUIDITY_SWEPT"
                captured_level = recent_lowest_liquidity
                
        return sweep_status, captured_level

    def detect_displaced_fvg(self, df):
        """
        INSTITUTIONAL GRADE FILTRE - FAIR VALUE GAP (FVG):
        Piyasada kurumsal emirlerin gercekten girildigini gosteren hacimli bosluklari bulur.
        3 mumluk bir yapida; 1. mumun iğnesi ile 3. mumun iğnesi arasindaki boslugu hesaplar.
        """
        if len(df) < 3:
            return {"fvg_present": False, "type": "NONE", "level": None}
            
        # Son 3 mumu inceliyoruz (0: iki önceki, 1: bir önceki, 2: mevcut mum)
        m0 = df.iloc[-3]
        m1 = df.iloc[-2]
        m2 = df.iloc[-1]
        
        # Bullish FVG (Alis yonlu bosluk - Fiyat burayi doldurmak isteyecektir)
        if m2['low'] > m0['high']:
            # Boslugun kurumsal momentumla (Displacement) olustugunu dogrulamak icin hacim kontrolu
            if m1['volume'] > df['volume'].tail(10).mean(): 
                return {
                    "fvg_present": True,
                    "type": "BULLISH",
                    "fvg_top": m2['low'],
                    "fvg_bottom": m0['high']
                }
                
        # Bearish FVG (Satis yonlu bosluk)
        elif m2['high'] < m0['low']:
            if m1['volume'] > df['volume'].tail(10).mean():
                return {
                    "fvg_present": True,
                    "type": "BEARISH",
                    "fvg_top": m0['low'],
                    "fvg_bottom": m2['high']
                }
                
        return {"fvg_present": False, "type": "NONE", "fvg_top": None, "fvg_bottom": None}

    def run_full_analysis(self, raw_data_df):
        """
        Tum profesyonel filtreleri sirasiyla calistirir ve yapay zekaya gonderilecek
        kusursuz matematiksel raporu hazırlar.
        """
        df = raw_data_df.copy()
        df = self.find_swing_points(df)
        
        sweep_status, sweep_level = self.detect_true_liquidity_sweep(df)
        fvg_metrics = self.detect_displaced_fvg(df)
        
        # Basit trend degil, Son 50 mumun agirlikli kurumsal yonu (Market Bias)
        htf_bias = "BULLISH" if df['close'].iloc[-1] > df['close'].tail(50).mean() else "BEARISH"
        
        analysis_report = {
            "market_bias": htf_bias,
            "liquidity_sweep_status": sweep_status,
            "swept_liquidity_level": sweep_level,
            "fvg_detected": fvg_metrics["fvg_present"],
            "fvg_type": fvg_metrics["type"],
            "fvg_zone": {"top": fvg_metrics["fvg_top"], "bottom": fvg_metrics["fvg_bottom"]},
            "current_close": df['close'].iloc[-1],
            "highest_price_20d": df['high'].tail(20).max(),
            "lowest_price_20d": df['low'].tail(20).min()
        }
        
        return analysis_report
