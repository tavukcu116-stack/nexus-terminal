import time
import pandas as pd
from datetime import datetime, timezone

# Kendi yazdigimiz diger modulleri projeye dahil ediyoruz
from news_manager import check_news_lockdown
from analytics_engine import SMCEngine
from terminal import AITradeTerminal

class NexusQuantCore:
    def _init_(self, target_currency="USD"):
        self.target_currency = target_currency
        self.smc_engine = SMCEngine(swing_window=20)
        # API anahtarini ortam degiskeninden aliyoruz (Guvvenlik icin)
        self.ai_terminal = AITradeTerminal() 

    def _get_live_market_data(self):
        """
        Canli grafik verilerini ceken fonksiyon taslagi.
        Sistemi hemen test edebilmen icin buraya gercekci bir SMC yapisi simule ediyoruz.
        (Normal sartlarda burasi MetaTrader 5'e veya bir borsanin API'sine baglanir).
        """
        print("[DATA] Grafik verileri saglayicidan cekiliyor...")
        
        # Yapay zekanin gercek seviyede karar kalitesini test etmek icin:
        # Bir 'Sell-Side Liquidity Sweep' (Ayilar icin tuzak, Bogalar icin alim) senaryosu simule edelim.
        base_price = 1.08500
        data = {
            "open":   [base_price + i*0.0001 for i in range(51)],
            "high":   [base_price + i*0.0001 + 0.0005 for i in range(51)],
            "low":    [base_price + i*0.0001 - 0.0002 for i in range(51)],
            "close":  [base_price + i*0.0001 + 0.0002 for i in range(51)],
            "volume": [1500 + (i * 50) for i in range(51)]
        }
        
        # Son mumu (Mevcut anlik mumu) bilerek guclu bir Likidite Avina sokuyoruz:
        # Fiyat onceki diplerin altina sarkiyor (low dusuyor) ama iceride kapatiyor (close yuksek).
        data["high"][-1] = 1.08900
        data["low"][-1]  = 1.08100  # Son 50 mumun en dip seviyesini deldi (Sweep)
        data["open"][-1] = 1.08600
        data["close"][-1]= 1.08750  # Eski dibin uzerinde kapatti ve altinda devasa bir igne birakti.
        data["volume"][-1]= 5000     # Kurumsal hacim girisi (Displacement)
        
        return pd.DataFrame(data)

    def run_execution_cycle(self):
        """
        Sistemin tek bir analiz dongusunu calistirir.
        """
        print(f"\n=================== NEXUS QUANT CORE DÖNGÜSÜ ({datetime.now().strftime('%H:%M:%S')}) ===================")
        
        # 1. ADIM: HABER KALKANI KONTROLÜ
        print("[KONTROL 1] Forex Factory ekonomik takvimi denetleniyor...")
        news_status = check_news_lockdown(trading_currency=self.target_currency)
        
        if news_status["lockdown"]:
            print(f"[UYARI] {news_status['reason']} - Sistem Guvenlik Modunda!")
            # Haber varsa grafige ve yapay zekaya hic gitmeden donguyu WAIT ile bitiriyoruz
            return {
                "DECISION": "WAIT",
                "PANEL_STATUS": "HIGH_IMPACT_NEWS_LOCKDOWN",
                "REASON": news_status["reason"]
            }
            
        print("[ONAY] Haber kısıtlaması bulunmuyor. Teknik analize geciliyor.")
        
        # 2. ADIM: GRAFİK VERİLERİNİN ÇEKİLMESİ VE MATEMATİKSEL SMC ANALİZİ
        raw_df = self._get_live_market_data()
        print("[KONTROL 2] Matematiksel SMC ve Likidite filtreleri calistiriliyor...")
        market_analysis = self.smc_engine.run_full_analysis(raw_df)
        
        # 3. ADIM: YAPAY ZEKA KARAR MOTORU
        print("[KONTROL 3] Analiz raporu Yapay Zeka Terminaline gonderiliyor...")
        ai_decision = self.ai_terminal.analyze_and_decide(news_status, market_analysis)
        
        # 4. ADIM: PANEL ÇIKTISINI YAZDIRMA
        print("\n------------------- ANALIZ SONUÇ PANELİ -------------------")
        print(f"KARAR         : {ai_decision.get('DECISION')}")
        print(f"PANEL DURUMU  : {ai_decision.get('PANEL_STATUS')}")
        if ai_decision.get('DECISION') in ['BUY', 'SELL']:
            print(f"GİRİŞ SEVİYESİ: {ai_decision.get('ENTRY_LEVEL')}")
            print(f"STOP LOSS     : {ai_decision.get('STOP_LOSS')} (Mikro Stop)")
            print(f"TAKE PROFIT   : {ai_decision.get('TAKE_PROFIT')}")
            print(f"HESAPLANAN RR : {ai_decision.get('ESTIMATED_RR')}")
        print("-----------------------------------------------------------")
        
        return ai_decision

if _name_ == "_main_":
    # Sistemi USD pariteleri icin baslatiyoruz
    core_system = NexusQuantCore(target_currency="USD")
    
    # Gercek sistemde bu bir 'while True' dongusu icinde mum kapanislarina gore tetiklenir.
    # Simdilik tek bir dongu calistirip test ediyoruz:
    try:
        core_system.run_execution_cycle()
    except KeyboardInterrupt:
        print("\nSistem kullanıcı tarafından durduruldu.")
