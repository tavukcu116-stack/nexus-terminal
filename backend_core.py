# backend_core.py
import asyncio
import logging
import json
import redis.asyncio as aioredis
from datetime import datetime, time
import numpy as np
import websockets

# Sistem loglarını temiz ve takip edilebilir kılmak için
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] -> %(message)s")
logger = logging.getLogger("NexusBackend")

class EnterpriseQuantCore:
    def _init_(self):
        self.redis_url = "redis://localhost:6379"
        # Analiz etmek istediğin parite (Görseldeki mantığa uygun olarak Binance Futures BTCUSDT)
        self.symbol = "BTCUSDT"
        self.binance_wss = f"wss://fstream.binance.com/ws/{self.symbol.lower()}@aggTrade"
        
        # CPU/RAM dostu sabit dairesel buffer (Numpy dizisi)
        self.max_window = 5000
        self.prices = np.zeros(self.max_window)
        self.pointer = 0
        self.is_full = False

        # Görseldeki ICT/SMC Killzone Zaman Aralıkları (Saat Kontrolleri)
        self.sessions = {
            "NY_AM": {"start": time(8, 0), "end": time(12, 0)},
            "NY_LUNCH": {"start": time(12, 0), "end": time(13, 30)},
            "NY_PM": {"start": time(13, 30), "end": time(17, 0)}
        }

    async def init_redis(self):
        """Asenkron Redis Cache katmanı bağlantısı."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def stream_data_pipeline(self):
        """Gecikmesiz ve kesintisiz ham veri akış hattı."""
        async with websockets.connect(self.binance_wss) as ws:
            logger.info(f"⚡ Backend Core connected to Binance Futures WS for {self.symbol}")
            while True:
                raw_msg = await ws.recv()
                msg = json.loads(raw_msg)
                
                idx = self.pointer
                self.prices[idx] = float(msg["p"])
                
                self.pointer = (self.pointer + 1) % self.max_window
                if self.pointer == 0: 
                    self.is_full = True
                
                # Her veride tüm scripti baştan çalıştırmak yerine sadece matematiksel hesaplamayı tetikle
                await self.reconcile_and_evaluate()

    async def reconcile_and_evaluate(self):
        """Gelişmiş Seans ve Market Yapısı Analiz Odası"""
        valid_len = self.max_window if self.is_full else self.pointer
        if valid_len < 100: 
            return
        
        current_price = self.prices[valid_len - 1]
        current_time = datetime.now()
        current_tick_time = current_time.time()
        
        # Aktif Seansı Belirle
        active_session = "OUT_OF_SESSION"
        for name, config in self.sessions.items():
            if config["start"] <= current_tick_time <= config["end"]:
                active_session = name
                break
        
        # Son 100 işlemdeki lokal zirveleri Numpy ile hızlıca bul (SMC Yapısal Analizi)
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
    core = EnterpriseQuantCore()
    asyncio.run(core.start_server())
