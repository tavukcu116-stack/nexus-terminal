import requests
from datetime import datetime, timedelta, timezone

def check_news_lockdown(trading_currency="USD", buffer_minutes=15):
    """
    Forex Factory veya benzeri takvim sağlayıcılarından günün ekonomik haberlerini çeker.
    Yüksek etkili (High Impact) haberlerin etrafında 'buffer_minutes' kadar bir kısıtlama penceresi oluşturur.
    """
    # Günlük ekonomik takvimi güncel formatta çeken güvenilir ve ücretsiz bir API ucu
    url = "https://io.alkermansour.com/forex/calendar/today"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            # API'ye ulaşılamazsa güvenlik amacıyla (false-negative olmaması için) kısıtlama vermiyoruz
            # Ancak backend'e durumu raporluyoruz.
            return {"lockdown": False, "reason": "Haber API baglantisi kurulamadi, teknik kontrol gerekli."}
            
        events = response.json()
        # Şu anki zamanı UTC (Evrensel Saat) olarak alıyoruz çünkü finansal takvimler UTC çalışır
        current_time = datetime.now(timezone.utc)
        
        for event in events:
            # Sadece Kırmızı Klasör (High) ve işlem yaptığımız para birimini (Örn: USD, EUR) etkileyen haberler
            if event.get('impact') == 'High' and event.get('currency') == trading_currency:
                
                # API'den gelen tarih formatını datetime nesnesine çeviriyoruz
                # Örnek format: 2026-06-10T15:30:00Z
                try:
                    event_time = datetime.strptime(event['date'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue # Format uyuşmazlığı varsa sıradakine geç
                
                # Haber öncesi ve sonrası yasaklı bölge sınırları
                lockdown_start = event_time - timedelta(minutes=buffer_minutes)
                lockdown_end = event_time + timedelta(minutes=buffer_minutes)
                
                # Eğer şu anki saat bu yasaklı aralığın içindeyse sistemi kilitle!
                if lockdown_start <= current_time <= lockdown_end:
                    return {
                        "lockdown": True,
                        "event_name": event.get('name'),
                        "currency": event.get('currency'),
                        "reason": f"KRITIK HABER ENGELI: {event.get('name')} ({event.get('currency')})"
                    }
                    
    except Exception as e:
        return {"lockdown": False, "reason": f"Haber kontrolu sirasinda hata olustu: {str(e)}"}
        
    # Eğer riskli bir haber penceresinde değilsek sistem temizdir
    return {"lockdown": False, "reason": "Yakin zamanda kritik bir haber verisi bulunmuyor. Sistem aktif."}

# Kodun tek başına doğru çalışıp çalışmadığını test etmek için test bloğu
if _name_ == "_main_":
    print("Haber kontrol mekanizmasi test ediliyor...")
    # Varsayılan olarak USD pariteleri (Altın, EURUSD, NASDAQ vb.) için kontrol yapıyoruz
    result = check_news_lockdown(trading_currency="USD")
    print(f"Kilit Durumu: {result['lockdown']}")
    print(f"Gerekçe: {result['reason']}")
