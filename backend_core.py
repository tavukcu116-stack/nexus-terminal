# ==========================================
# 📄 DOSYA: backend_core.py (NEXUS QUANT v56.4 - OPTIMIZED)
# ==========================================
import os
import sqlite3
import requests
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import streamlit as st
import logging
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_FILE = "nexus_v54_vault.db"
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "MOCK_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Binance sembol haritası: merkezi ve genişletilebilir ---
BINANCE_SYMBOL_MAP = {
    "IXIC": "BTCUSDT",   # NASDAQ doğrudan desteklenmiyor, en yakın proxy
    "DJI":  "BTCUSDT",   # DJI de aynı şekilde
}

# ─────────────────────────────────────────
# 1. VERİTABANI KATMANI
# ─────────────────────────────────────────

@contextmanager
def get_db():
    """
    Context manager ile bağlantı yönetimi.
    Her bloktan çıkışta bağlantı garantili kapatılır,
    hata durumunda rollback yapılır.
    """
    conn = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")   # eşzamanlı okuma/yazma için
    conn.execute("PRAGMA busy_timeout=5000")  # kilit beklemesi 5sn
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_v56_vault_and_migrations():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS v54_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, asset TEXT, type TEXT, entry REAL,
                sl REAL, tp1 REAL, tp2 REAL, lot REAL, pnl REAL,
                status TEXT, score INTEGER, q_class TEXT, session TEXT,
                duration_min INTEGER DEFAULT 0, direction TEXT, close_time TEXT,
                initial_risk_usd REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nexus_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, level TEXT, message TEXT
            )
        """)

        cursor.execute("PRAGMA table_info(v54_ledger)")
        existing = {col[1] for col in cursor.fetchall()}
        migrations = {
            "initial_risk_usd": "REAL DEFAULT 0.0",
            "close_time":       "TEXT",
            "direction":        "TEXT",
            "duration_min":     "INTEGER DEFAULT 0"
        }
        for col_name, col_type in migrations.items():
            if col_name not in existing:
                try:
                    cursor.execute(f"ALTER TABLE v54_ledger ADD COLUMN {col_name} {col_type}")
                    log_system_event("INFO", f"Migration: {col_name} eklendi.")
                except Exception as e:
                    log_system_event("ERROR", f"Migration hatası ({col_name}): {e}")


def log_system_event(level: str, message: str):
    """Konsol + DB log. DB hatası sessizce geçilir ama konsola yazılır."""
    logging.info(f"[{level}] {message}")
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO nexus_logs (timestamp, level, message) VALUES (?, ?, ?)",
                (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), level, message)
            )
    except Exception as e:
        logging.warning(f"Log DB yazım hatası: {e}")


init_v56_vault_and_migrations()


# ─────────────────────────────────────────
# 2. TELEGRAM
# ─────────────────────────────────────────

def send_telegram_notification(message: str) -> bool:
    if not TG_TOKEN or not TG_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload, timeout=5)
        return r.status_code == 200
    except Exception as e:
        log_system_event("ERROR", f"Telegram hatası: {e}")
        return False


# ─────────────────────────────────────────
# 3. VERİ ÇEKME
# ─────────────────────────────────────────

def _parse_twelve_data(r_json: dict) -> pd.DataFrame | None:
    if "values" not in r_json:
        return None
    df = pd.DataFrame(r_json["values"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.dropna().drop_duplicates(subset=["datetime"]).iloc[::-1].reset_index(drop=True)
    return df if not df.empty else None


def _parse_binance_data(res: list) -> pd.DataFrame | None:
    if not isinstance(res, list) or len(res) == 0:
        return None
    df = pd.DataFrame(res).iloc[:, :5]
    df.columns = ["datetime", "open", "high", "low", "close"]
    df["datetime"] = pd.to_datetime(df["datetime"], unit="ms")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna().reset_index(drop=True)


def _to_binance_symbol(symbol: str) -> str:
    """
    Twelve Data sembolünü Binance sembolüne çevirir.
    Önce sabit haritaya bakar, sonra sezgisel kurallar uygular.
    """
    clean = symbol.replace("/", "").upper()
    if clean in BINANCE_SYMBOL_MAP:
        return BINANCE_SYMBOL_MAP[clean]
    # Forex: USD → USDT (ör. EURUSD → EURUSDT)
    if clean.endswith("USD") and clean != "USDT":
        return clean + "T"
    return clean


INTERVAL_MAP = {"15min": "15m", "1h": "1h", "4h": "4h", "1day": "1d"}


def fetch_clean_candles(symbol: str, interval: str = "15min", outputsize: str = "100") -> pd.DataFrame | None:
    # — Twelve Data —
    try:
        url = (
            f"https://api.twelvedata.com/time_series"
            f"?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_KEY}"
        )
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        df = _parse_twelve_data(r.json())
        if df is not None:
            return df
    except Exception as e:
        log_system_event("ERROR", f"Twelve Data hatası ({symbol}): {e}")

    # — Binance fallback —
    try:
        b_sym = _to_binance_symbol(symbol)
        b_interval = INTERVAL_MAP.get(interval, "15m")
        url = f"https://api.binance.com/api/v3/klines?symbol={b_sym}&interval={b_interval}&limit={outputsize}"
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        df = _parse_binance_data(r.json())
        if df is not None:
            return df
    except Exception as e:
        log_system_event("CRITICAL", f"Binance fallback hatası ({symbol}): {e}")

    return None


def get_live_spread_data(symbol: str) -> tuple[float, float, float]:
    try:
        url = f"https://api.twelvedata.com/quotes?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        data = r.json()
        if "bid" in data and "ask" in data:
            bid, ask = float(data["bid"]), float(data["ask"])
            multiplier = 10 if any(x in symbol for x in ("XAU", "BTC", "ETH")) else 10000
            return round(abs(ask - bid) * multiplier, 2), bid, ask
    except Exception as e:
        log_system_event("ERROR", f"{symbol} spread alınamadı: {e}")
    return 1.2, 0.0, 0.0


# ─────────────────────────────────────────
# 4. POZİSYON BÜYÜKLÜĞÜ
# ─────────────────────────────────────────

def calculate_position_size(capital: float, risk_pct: float, price: float, sl_p: float, asset: str) -> float:
    if price == sl_p or sl_p == 0:
        return 0.01
    allowed_loss_usd = capital * (risk_pct / 100.0)
    multiplier = 10 if any(x in asset for x in ("XAU", "BTC", "ETH")) else 10000
    p_distance = abs(price - sl_p) * multiplier
    final_lot = allowed_loss_usd / (p_distance * 10 + 1e-9)
    return max(0.01, round(final_lot, 2))


# ─────────────────────────────────────────
# 5. HABER FİLTRESİ  (cache süresi 3 dk — haber zamanı kritik)
# ─────────────────────────────────────────

@st.cache_data(ttl=180)
def check_economic_news_timeline(symbol: str) -> tuple[bool, str]:
    currencies = ["USD", "EUR", "GBP", "AUD", "CAD", "CHF", "JPY"]
    active_currency = next((c for c in currencies if c in symbol), "USD")

    # — Forex Factory XML —
    try:
        url = "https://www.forexfactory.com/ffcal_xml_thisweek.xml"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            now_utc = datetime.now(timezone.utc)
            for event in root.findall("event"):
                currency_node = event.find("currency")
                impact_node   = event.find("impact")
                date_node     = event.find("date")
                time_node     = event.find("time")
                title_node    = event.find("title")

                if None in (currency_node, impact_node, date_node, time_node):
                    continue
                if currency_node.text != active_currency or impact_node.text != "High":
                    continue

                try:
                    event_time = datetime.strptime(
                        f"{date_node.text} {time_node.text}", "%m-%d-%Y %I:%M%p"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                window_start = event_time - timedelta(minutes=30)
                window_end   = event_time + timedelta(minutes=15)
                if window_start <= now_utc <= window_end:
                    title = title_node.text if title_node is not None else "Haber"
                    return True, f"LOCK: {title} HABER ENGELİ"

            return False, "GATES CLEAR"
    except Exception as e:
        log_system_event("ERROR", f"Haber filtre hatası: {e}")

    return False, "GATES CLEAR (FALLBACK)"


# ─────────────────────────────────────────
# 6. DEVRE KESİCİLER
# ─────────────────────────────────────────

CORRELATION_MATRIX: dict[str, list[str]] = {
    "EUR/USD":  ["GBP/USD", "XAU/USD"],
    "GBP/USD":  ["EUR/USD"],
    "NASDAQ":   ["US30"],
    "US30":     ["NASDAQ"],
}


def check_live_circuit_barriers(asset: str, capital: float) -> tuple[bool, str]:
    risk_unit_usd = capital * 0.01

    with get_db() as conn:
        cursor = conn.cursor()

        # Günlük -3R kilidi
        cursor.execute(
            "SELECT COALESCE(SUM(pnl), 0.0) FROM v54_ledger WHERE timestamp >= date('now', 'start of day')"
        )
        daily_pnl = cursor.fetchone()[0]
        if daily_pnl <= -(risk_unit_usd * 3):
            return True, "DAILY LOSS CIRCUIT TRIGGERED (-3R LOCKUP)"

        # Maksimum %5 drawdown kilidi
        cursor.execute("SELECT COALESCE(SUM(pnl), 0.0) FROM v54_ledger")
        total_pnl = cursor.fetchone()[0]
        if total_pnl <= -(capital * 0.05):
            return True, "MAX DRAWDOWN CAP REACHED (%5 HALT)"

        # Global açık pozisyon limiti
        cursor.execute("SELECT COUNT(*) FROM v54_ledger WHERE status = 'OPEN'")
        if cursor.fetchone()[0] >= 3:
            return True, "LIMIT LOCK: Global max 3 açık işlem sınırı"

        # Korelasyon çakışması
        if asset in CORRELATION_MATRIX:
            cursor.execute("SELECT asset FROM v54_ledger WHERE status = 'OPEN'")
            open_assets = {r[0] for r in cursor.fetchall()}
            for corr_asset in CORRELATION_MATRIX[asset]:
                if corr_asset in open_assets:
                    return True, f"CORRELATION LOCK: {corr_asset} ile risk çakışması"

    return False, "CLEAR"


# ─────────────────────────────────────────
# 7. PAZAR YAPISI ANALİZİ
# ─────────────────────────────────────────

def _find_swing_points(series: np.ndarray, window: int = 5) -> list[int]:
    """Verilen window içindeki lokal tepe/dip indekslerini döner."""
    return [
        i for i in range(window, len(series) - window)
        if series[i] == series[i - window: i + window + 1].max()
    ]


def analyze_advanced_market_structure(df_htf: pd.DataFrame | None) -> tuple[str, float, float, float]:
    if df_htf is None or len(df_htf) < 20:
        return "WAIT", 0.0, 0.0, 0.0

    highs  = df_htf["high"].values
    lows   = df_htf["low"].values
    closes = df_htf["close"].values

    sh_idx = _find_swing_points(highs)
    # Dip için düşük noktaları bul (negatif yaparız)
    sl_idx = [
        i for i in range(5, len(df_htf) - 5)
        if lows[i] == lows[i - 5: i + 6].min()
    ]

    last_sh = highs[sh_idx[-1]] if sh_idx else highs.max()
    last_sl = lows[sl_idx[-1]]  if sl_idx else lows.min()
    eq = (last_sh + last_sl) / 2

    if closes[-1] > last_sh:
        return "BULLISH", last_sh, last_sl, eq
    if closes[-1] < last_sl:
        return "BEARISH", last_sh, last_sl, eq
    return "WAIT", last_sh, last_sl, eq


# ─────────────────────────────────────────
# 8. SMC MATRİS TARAMASI
# ─────────────────────────────────────────

def _detect_ob_fvg(df_15m: pd.DataFrame, idx: int, atr: float) -> tuple[dict | None, dict | None, int, int]:
    """Order Block ve FVG tespiti — ayrı fonksiyon olarak izole edildi."""
    active_ob, active_fvg = None, None
    ob_points = fvg_points = 0

    for i in range(max(0, idx - 20), idx - 1):
        c0, o0 = df_15m["close"].iloc[i],   df_15m["open"].iloc[i]
        c1, o1 = df_15m["close"].iloc[i+1], df_15m["open"].iloc[i+1]
        h0, l0 = df_15m["high"].iloc[i],    df_15m["low"].iloc[i]

        # FVG tespiti
        gap_bull = df_15m["low"].iloc[i+2]  - h0
        gap_bear = l0 - df_15m["high"].iloc[i+2]

        if gap_bull > atr * 0.4:
            active_fvg = {
                "type": "BULLISH FVG",
                "top":    df_15m["low"].iloc[i+2],
                "bottom": h0,
                "time":   df_15m["datetime"].iloc[i+1]
            }
            fvg_points = 20

        elif gap_bear > atr * 0.4:
            active_fvg = {
                "type": "BEARISH FVG",
                "top":    l0,
                "bottom": df_15m["high"].iloc[i+2],
                "time":   df_15m["datetime"].iloc[i+1]
            }
            fvg_points = 20

        # OB tespiti
        if c0 < o0 and c1 > o1:   # Bearish mum → Bullish mum
            active_ob = {"type": "BULLISH OB", "top": h0, "bottom": l0, "time": df_15m["datetime"].iloc[i]}
            ob_points = 25
        elif c0 > o0 and c1 < o1: # Bullish mum → Bearish mum
            active_ob = {"type": "BEARISH OB", "top": h0, "bottom": l0, "time": df_15m["datetime"].iloc[i]}
            ob_points = 25

    return active_ob, active_fvg, ob_points, fvg_points


def _calculate_levels(bias: str, close_p: float, last_sh: float, last_sl: float, atr: float
                      ) -> tuple[float, float, float, float]:
    """SL, TP1, TP2 ve gerçek RR hesaplama."""
    if bias == "BUY":
        sl_p = last_sl - atr * 0.15 if last_sl < close_p else close_p - atr * 1.5
        risk = abs(close_p - sl_p)
        tp1_p = close_p + risk * 1.5
        tp2_p = close_p + risk * 3.0
        rr    = round(abs(tp2_p - close_p) / (risk + 1e-9), 1)
    elif bias == "SELL":
        sl_p = last_sh + atr * 0.15 if last_sh > close_p else close_p + atr * 1.5
        risk = abs(sl_p - close_p)
        tp1_p = close_p - risk * 1.5
        tp2_p = close_p - risk * 3.0
        rr    = round(abs(close_p - tp2_p) / (risk + 1e-9), 1)
    else:
        sl_p = tp1_p = tp2_p = rr = 0.0
    return sl_p, tp1_p, tp2_p, rr


def extract_quant_smc_matrix(symbol: str) -> dict | None:
    df_4h  = fetch_clean_candles(symbol, "4h",    "60")
    df_1h  = fetch_clean_candles(symbol, "1h",    "60")
    df_15m = fetch_clean_candles(symbol, "15min", "100")

    if df_4h is None or df_1h is None or df_15m is None or len(df_15m) < 40:
        return None

    idx = len(df_15m) - 1
    close_p = df_15m["close"].iloc[idx]
    high_p  = df_15m["high"].iloc[idx]
    low_p   = df_15m["low"].iloc[idx]

    atr = (df_15m["high"] - df_15m["low"]).rolling(14).mean().iloc[-1]
    hist_vol = (df_15m["high"] - df_15m["low"]).rolling(50).mean().iloc[-1]
    volatility_passed = atr >= hist_vol * 0.8

    # HTF trend
    htf_trend, pdh, pdl, eq_level = analyze_advanced_market_structure(df_4h)
    if htf_trend == "WAIT":
        htf_trend, pdh, pdl, eq_level = analyze_advanced_market_structure(df_1h)

    market_zone = "PREMIUM" if close_p > eq_level else "DISCOUNT"

    # 15M swing seviyeleri
    sh_15 = [df_15m["high"].iloc[i] for i in range(4, idx - 4) if df_15m["high"].iloc[i] == df_15m["high"].iloc[i-4:i+5].max()]
    sl_15 = [df_15m["low"].iloc[i]  for i in range(4, idx - 4) if df_15m["low"].iloc[i]  == df_15m["low"].iloc[i-4:i+5].min()]
    last_sh = sh_15[-1] if sh_15 else pdh
    last_sl = sl_15[-1] if sl_15 else pdl

    sweep_detected = (high_p > last_sh and close_p < last_sh) or (low_p < last_sl and close_p > last_sl)
    displacement   = abs(close_p - df_15m["open"].iloc[idx]) > atr * 0.9

    if   displacement and close_p > last_sh: structure_type = "BOS BULLISH"
    elif displacement and close_p < last_sl: structure_type = "BOS BEARISH"
    elif sweep_detected:                      structure_type = "CHOCH REVERSAL"
    else:                                     structure_type = "RANGE"

    active_ob, active_fvg, ob_points, fvg_points = _detect_ob_fvg(df_15m, idx, atr)

    # Skor
    score = 30 + ob_points + fvg_points
    if sweep_detected:            score += 20
    if structure_type != "RANGE": score += 15
    if volatility_passed:         score += 10

    q_class = "A+" if score >= 90 else "A" if score >= 75 else "B" if score >= 60 else "WAIT"

    # Bias
    bias = "WAIT"
    if htf_trend == "BULLISH" and market_zone == "DISCOUNT":
        bias = "BUY"
    elif htf_trend == "BEARISH" and market_zone == "PREMIUM":
        bias = "SELL"
    elif score >= 75:
        if market_zone == "DISCOUNT" and (structure_type == "BOS BULLISH" or sweep_detected):
            bias = "BUY"
        elif market_zone == "PREMIUM" and (structure_type == "BOS BEARISH" or sweep_detected):
            bias = "SELL"

    sl_p, tp1_p, tp2_p, rr = _calculate_levels(bias, close_p, last_sh, last_sl, atr)

    return {
        "df": df_15m, "price": close_p, "pdh": pdh, "pdl": pdl, "eq": eq_level,
        "zone": market_zone, "sh": last_sh, "sl": last_sl, "bias": bias,
        "structure": structure_type, "ob": active_ob, "fvg": active_fvg,
        "sl_p": sl_p, "tp1_p": tp1_p, "tp2_p": tp2_p, "rr": rr,
        "score": score, "q_class": q_class, "session": "LONDON", "kz": True,
        "action": "AUTONOMOUS MODE" if bias != "WAIT" else "STANDBY"
    }


# ─────────────────────────────────────────
# 9. OTONOM MOTOR
# ─────────────────────────────────────────

def manage_v55_autonomous_engine(
    asset: str, node: dict, final_lot: float,
    daily_lock: bool, total_lock: bool, corr_lock: bool, news_lock: bool,
    capital: float
) -> None:
    c_blocked, c_reason = check_live_circuit_barriers(asset, capital)
    if any([daily_lock, total_lock, corr_lock, news_lock, c_blocked]):
        log_system_event("INFO", f"Emir engellendi ({asset}): {c_reason}")
        return
    if node["bias"] == "WAIT" or node["score"] < 75:
        return

    mult = 10 if any(x in asset for x in ("XAU", "BTC", "ETH")) else 10000
    calculated_risk_usd = abs(node["price"] - node["sl_p"]) * final_lot * mult

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM v54_ledger WHERE asset = ? AND status = 'OPEN'", (asset,)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """INSERT INTO v54_ledger
                   (timestamp, asset, type, entry, sl, tp1, tp2, lot, pnl, status,
                    score, q_class, session, duration_min, direction, close_time, initial_risk_usd)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'OPEN', ?, ?, 'LONDON', 0, ?, 'RUNNING', ?)""",
                (
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    asset, node["bias"], node["price"], node["sl_p"],
                    node["tp1_p"], node["tp2_p"], final_lot,
                    node["score"], node["q_class"], node["bias"], calculated_risk_usd
                )
            )
            send_telegram_notification(
                f"🏛️ *NEXUS AUTONOMOUS EXECUTED:* {asset} {node['bias']} "
                f"{final_lot} Lot | Skor: {node['score']} | Risk: ${calculated_risk_usd:.2f}"
            )


# ─────────────────────────────────────────
# 10. POZİSYON YÖNETİMİ  (kısmi TP lot hatası düzeltildi)
# ─────────────────────────────────────────

def manage_v54_positions(asset: str, current_df: pd.DataFrame | None) -> None:
    if current_df is None or current_df.empty:
        return

    last_candle = current_df.iloc[-1]
    mult = 10 if any(x in asset for x in ("XAU", "BTC", "ETH")) else 10000

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, type, entry, sl, tp1, tp2, lot, timestamp FROM v54_ledger WHERE status = 'OPEN' AND asset = ?",
            (asset,)
        )
        trades = cursor.fetchall()

        for t_id, t_type, entry, sl, tp1, tp2, lot, ts in trades:
            closed = False
            pnl    = 0.0
            status = "OPEN"

            if t_type == "BUY":
                # Kısmi TP: sadece yarı lot ile hesapla, yeni lot yarıya güncelle
                if last_candle["high"] >= tp1 and sl < entry:
                    partial_lot = lot * 0.5
                    partial_pnl = (tp1 - entry) * partial_lot * mult
                    cursor.execute(
                        "UPDATE v54_ledger SET sl = ?, pnl = pnl + ?, lot = ?, initial_risk_usd = 0.0 WHERE id = ?",
                        (entry, partial_pnl, partial_lot, t_id)  # lot artık yarıya düştü
                    )
                    lot = partial_lot   # kalan lot güncellendi
                    sl  = entry
                    send_telegram_notification(
                        f"🎯 *PARTIAL TP1 (50%):* {asset} | +${partial_pnl:.2f} | BE'ye alındı"
                    )

                if last_candle["low"] <= sl:
                    closed = True
                    pnl    = (sl - entry) * lot * mult
                    status = "CLOSED_SL"
                elif last_candle["high"] >= tp2:
                    closed = True
                    pnl    = (tp2 - entry) * lot * mult
                    status = "CLOSED_TP"

            elif t_type == "SELL":
                if last_candle["low"] <= tp1 and sl > entry:
                    partial_lot = lot * 0.5
                    partial_pnl = (entry - tp1) * partial_lot * mult
                    cursor.execute(
                        "UPDATE v54_ledger SET sl = ?, pnl = pnl + ?, lot = ?, initial_risk_usd = 0.0 WHERE id = ?",
                        (entry, partial_pnl, partial_lot, t_id)
                    )
                    lot = partial_lot
                    sl  = entry
                    send_telegram_notification(
                        f"🎯 *PARTIAL TP1 (50%):* {asset} | +${partial_pnl:.2f} | BE'ye alındı"
                    )

                if last_candle["high"] >= sl:
                    closed = True
                    pnl    = (entry - sl) * lot * mult
                    status = "CLOSED_SL"
                elif last_candle["low"] <= tp2:
                    closed = True
                    pnl    = (entry - tp2) * lot * mult
                    status = "CLOSED_TP"

            if closed:
                cursor.execute(
                    "UPDATE v54_ledger SET pnl = pnl + ?, status = ?, close_time = ? WHERE id = ?",
                    (pnl, status, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), t_id)
                )
                send_telegram_notification(
                    f"🏛️ *POSITION CLOSED:* {asset} | {status} | Net PnL: ${pnl:.2f}"
                )


# ─────────────────────────────────────────
# 11. BACKTEST (SMC bazlı — daha temsili)
# ─────────────────────────────────────────

def run_historical_backtest_matrix(df: pd.DataFrame | None) -> tuple[float, float, float, float]:
    """
    Basit OB-tabanlı backtest.
    Bearish mum → Bullish mum geçişini OB olarak tanımlar,
    bir sonraki fiyatın SL veya TP'ye değip değmediğini kontrol eder.
    """
    if df is None or len(df) < 30:
        return 50.0, 1.0, 0.0, 0.0

    pnl_array: list[float] = []
    atr_series = (df["high"] - df["low"]).rolling(14).mean()

    for i in range(15, len(df) - 6):
        atr_local = atr_series.iloc[i]
        if pd.isna(atr_local) or atr_local == 0:
            continue

        c_prev, o_prev = df["close"].iloc[i-1], df["open"].iloc[i-1]
        c_curr, o_curr = df["close"].iloc[i],   df["open"].iloc[i]

        # Bullish OB: bearish → bullish dönüş
        if c_prev < o_prev and c_curr > o_curr:
            entry = c_curr
            sl    = df["low"].iloc[i-1] - atr_local * 0.15
            risk  = abs(entry - sl)
            if risk == 0:
                continue
            tp = entry + risk * 3.0

            for j in range(i + 1, min(i + 10, len(df))):
                fut = df.iloc[j]
                if fut["low"] <= sl:
                    pnl_array.append(-risk)
                    break
                if fut["high"] >= tp:
                    pnl_array.append(risk * 3.0)
                    break

    if not pnl_array:
        return 50.0, 1.0, 0.0, 0.0

    pnl_s  = pd.Series(pnl_array)
    wins   = pnl_s[pnl_s > 0]
    losses = pnl_s[pnl_s < 0]
    wr     = round(len(wins) / len(pnl_s) * 100, 1)
    pf     = round(wins.sum() / (abs(losses.sum()) + 1e-9), 2)
    return wr, max(0.1, pf), 0.01, round(pnl_s.mean(), 4)
