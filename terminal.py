import openai
import json
import os

class AITradeTerminal:
    def _init_(self, api_key=None):
        """
        AI Karar Terminali.
        API anahtarini ortam degiskenlerinden veya doğrudan parametre olarak alir.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key

    def _generate_system_prompt(self):
        """
        Yapaya zekaya katı kurumsal kurallari dikte eden profesyonel sistem promptu.
        Goz boyamaya veya esneklige kesinlikle izin verilmez.
        """
        return """Sen, Ekin Yüzbaşıoğlu tarzında mekanik Smart Money Concepts (SMC) ve Price Action kurallarıyla çalışan profesyonel bir Forex Analiz Motorusun. 
Duygusallığa, esnekliğe ve yüzeysel yorumlara yer yok. Sana sağlanan teknik ve temel analiz verilerini strictly (katı bir şekilde) süzgeçten geçireceksin.

İŞLEM KONTROL PROTOKOLÜ (Mekanik Kurallar):
1. HABER DURUMU: Eğer 'news_lockdown' değeri True ise, piyasa manipülatif dalgalanmalara açık demektir. Grafik ne kadar kusursuz olursa olsun anında 'WAIT' kararı vereceksin.
2. LİKİDİTE (SWEEP): Ekin'in stratejisinin kalbi likiditedir. 'liquidity_sweep_status' değeri 'NONE' ise, piyasada henüz yakıt toplanmamıştır. Kurumsal hamle başlamaz. Kesinlikle 'WAIT' diyeceksin.
3. TREND & YAPI UYUMU: 'market_bias' ile LTF dönüş yapısı uyumlu olmalıdır. Bias BEARISH ise sadece Short (SELL), BULLISH ise sadece Long (BUY) yönlü onay arayabilirsin.
4. MİKRO STOP & RR MATEMATİĞİ: 
   - Giriş seviyesini (ENTRY_LEVEL) anlık fiyata veya FVG bölgesinin testine kuracaksın.
   - Stop seviyesini (STOP_LOSS), likiditeyi alan iğnenin tam ucuna (Safe Exit) milimetrik olarak koyacaksın (Dar stop).
   - Hedef seviyesini (TAKE_PROFIT), grafik verilerindeki zıt yönlü likidite havuzuna kuracaksın.
   - Hesapladığın Risk/Ödül Oranı (Estimated RR) KESİNLİKLE minimum 1:4.0 olmak zorundadır. Altındaysa işlemi reddet!

ÇIKTI FORMATI:
Yalnızca ve yalnızca aşağıdaki JSON formatında yanıt vereceksin. Markdown etiketleri (json ... ), açıklama satırları veya ekstra metinler KESİNLİKLE eklenmeyecektir:
{
  "DECISION": "BUY" | "SELL" | "WAIT",
  "PANEL_STATUS": "İşlem aktifse 'ORDER_READY', WAIT ise tam sebebi (Örn: HIGH IMPACT NEWS LOCKDOWN, HTF TREND MISALIGNMENT, NO LIQUIDITY SWEEP, RR TOO LOW, AWAITING OB RETEST)",
  "ENTRY_LEVEL": 0.0,
  "STOP_LOSS": 0.0,
  "TAKE_PROFIT": 0.0,
  "ESTIMATED_RR": "0.0 (Örn: 4.5)"
}"""

    def analyze_and_decide(self, news_status, market_analysis):
        """
        Haber ve SMC verilerini birlestirerek yapay zekadan nihai kurumsal karari ister.
        """
        if not self.api_key and not openai.api_key:
            return {
                "DECISION": "WAIT",
                "PANEL_STATUS": "SYSTEM_ERROR: MISSING_API_KEY",
                "ENTRY_LEVEL": 0.0, "STOP_LOSS": 0.0, "TAKE_PROFIT": 0.0, "ESTIMATED_RR": "0.0"
            }

        # Yapay zekaya beslenecek veri paketini hazirliyoruz
        payload = {
            "news_lockdown": news_status.get("lockdown", False),
            "news_reason": news_status.get("reason", ""),
            "market_bias": market_analysis.get("market_bias", "NONE"),
            "liquidity_sweep_status": market_analysis.get("liquidity_sweep_status", "NONE"),
            "swept_liquidity_level": market_analysis.get("swept_liquidity_level", None),
            "fvg_detected": market_analysis.get("fvg_detected", False),
            "fvg_type": market_analysis.get("fvg_type", "NONE"),
            "fvg_zone": market_analysis.get("fvg_zone", {}),
            "current_close": market_analysis.get("current_close", 0.0),
            "highest_price_20d": market_analysis.get("highest_price_20d", 0.0),
            "lowest_price_20d": market_analysis.get("lowest_price_20d", 0.0)
        }

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o", # Değişiklikleri ve katı mantığı en iyi simüle eden reasoning modeli
                messages=[
                    {"role": "system", "content": self._generate_system_prompt()},
                    {"role": "user", "content": f"Mevcut Piyasa Durumu Verileri:\n{json.dumps(payload, indent=2)}"}
                ],
                temperature=0.0 # Sapmalari engellemek ve her zaman tutarli/katı kararlar almak icin 0 yapiyoruz
            )
            
            # Gelen yanıtı temizleyip JSON objesine donusturuyoruz
            raw_content = response.choices[0].message.content.strip()
            
            # Olası markdown etiketlerini temizleme temizliği
            if raw_content.startswith("```"):
                raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
                if raw_content.startswith("json"):
                    raw_content = raw_content[4:].strip()

            return json.loads(raw_content)

        except Exception as e:
            return {
                "DECISION": "WAIT",
                "PANEL_STATUS": f"SYSTEM_ERROR: AI_ENGINE_EXCEPTION ({str(e)})",
                "ENTRY_LEVEL": 0.0, "STOP_LOSS": 0.0, "TAKE_PROFIT": 0.0, "ESTIMATED_RR": "0.0"
            }
