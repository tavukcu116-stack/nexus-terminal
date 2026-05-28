# backend_core.py
import asyncio
import logging
import json
import redis.asyncio as aioredis
from datetime import datetime, time
import numpy as np
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] -> %(message)s")
logger = logging.getLogger("NexusForexBackend")

class EnterpriseForexCore:
    def _init_(self):
        self.redis_url = "redis://localhost:6379"
        
        # FOREX YAPILANDIRMASI
        self.symbol = "XAU/USD"  # İşlem yaptığın parite (Altın / Dolar)
        # Twelve Data WebSocket Adresi (requirements.txt içindeki paketlerle uyumlu)
        self.api_key = "YOUR_TWELVE_DATA_API_KEY" # Buraya Twelve Data API anahtarını koyacaksın
        self.forex_wss = f"wss://ws.twelvedata.com/v1/quotes?apikey={self.api_key}"
        
        # CPU ve RAM dostu sabit dairesel buffer (Numpy dizisi)
        self.max_window = 5000
        self.prices = np.zeros(self.max_window)
        self.pointer = 0
        self.is_full = False

        # ICT / SMC Killzone Zaman Aralıkları (EST / New York Saati)
        self.sessions = {
            "NY_AM": {"start": time(8, 0), "end": time(12, 0)},
            "NY_LUNCH": {"start": time(12, 0), "end": time(13, 30)},
            "NY_PM": {"start": time(13, 30), "end": time(17, 0)}
        }

    async def init_redis(self):
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def stream_data_pipeline(self):
        """Forex Canlı Veri Hattı (Twelve Data WS İstemcisi)"""
        async with websockets.connect(self.forex_wss) as ws:
            # Twelve Data'ya hangi pariteyi izlemek istediğimizi bildiriyoruz (Subscribe)
            subscribe_msg = {
                "action": "subscribe",
                "params": {
                    "symbols": self.symbol
                }
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"🏛️ Forex Core connected to Twelve Data WS for {self.symbol}")
            
            while True:
                raw_msg = await ws.recv()
                msg = json.loads(raw_msg)
                
                # Twelve Data'dan gelen fiyat verisini yakala (Price tick)
                if msg.get("event") == "price":
                    idx = self.pointer
                    self.prices[idx] = float(msg["price"])
                    
                    self.pointer = (self.pointer + 1) % self.max_window
                    if self.pointer == 0: 
                        self.is_full = True
                    
                    await self.reconcile_and_evaluate()

    async def reconcile_and_evaluate(self):
        """Forex SMC / ICT Market Yapısı Analiz Odası"""
        valid_len = self.max_window if self.is_full else self.pointer
        if valid_len < 100: 
            return
        
        current_price = self.prices[valid_len - 1]
        current_time = datetime.now()
        current_tick_time = current_time.time()
        
        # Aktif ICT Killzone Seansını Belirle
        active_session = "OUT_OF_SESSION"
        for name, config in self.sessions.items():
            if config["start"] <= current_tick_time <= config["end"]:
                active_session = name
                break
        
        # Son 100 tikteki lokal zirveleri bul (Forex MSS Analizi)
        local_high = np.max(self.prices[max(0, valid_len-100):valid_len])
        mss_bullish = current_price > local_high
        
        # Durum verilerini tamamen paketle ve Redis'e fırlat
        payload = {
            "price": current_price,
            "active_session": active_session,
            "mss_bullish": int(mss_bullish),
            "timestamp": str(current_time),
            "status": "OPERATIONAL"
        }
        await self.redis.set("nexus_live_state", json.dumps(payload))

    async def start_server(self):
        await self.init_redis()
        await self.stream_data_pipeline()

if _name_ == "_main_":
    core = EnterpriseForexCore()
    asyncio.run(core.start_server())
