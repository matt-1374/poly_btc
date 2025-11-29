import os
import time
import json
import csv
import requests
import logging
import pytz
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
DATA_ROOT = Path("./data_collection")
BINANCE_API_TICKER = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
BINANCE_API_KLINE = "https://api.binance.com/api/v3/klines"
POLY_GAMMA_API = "https://gamma-api.polymarket.com/events"
POLY_CLOB_MID_API = "https://clob.polymarket.com/midpoint"
POLL_INTERVAL = 1.0
TZ_ET = pytz.timezone('US/Eastern')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("PolyCollector")

class PolySimpleCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; PolySimpleCollector/1.0)"
        })

    def get_binance_price(self):
        """Fetch live BTC price."""
        try:
            resp = self.session.get(BINANCE_API_TICKER, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                return float(data['price'])
        except Exception:
            pass
        return None

    def get_binance_hour_open(self, target_dt):
        """
        Fetches the Open Price of the 1H candle starting at target_dt.
        target_dt must be the exact top of the hour (e.g. 14:00:00).
        """
        try:
            # Ensure we are requesting the exact top of the hour
            clean_dt = target_dt.replace(minute=0, second=0, microsecond=0)
            
            # Convert to Unix Milliseconds
            ts_ms = int(clean_dt.timestamp() * 1000)
            
            params = {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "startTime": ts_ms,
                "limit": 1
            }
            
            resp = self.session.get(BINANCE_API_KLINE, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # If we get data, data[0][1] is the Open Price
                if data:
                    return float(data[0][1])
        except Exception as e:
            logger.error(f"Binance History Error: {e}")
        return None

    def get_midpoint_price(self, token_id):
        try:
            resp = self.session.get(POLY_CLOB_MID_API, params={"token_id": token_id}, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get('mid', 0))
        except Exception:
            pass
        return None

    def generate_slug(self, target_time):
        month = target_time.strftime("%B").lower()
        day = target_time.day
        hour_int = int(target_time.strftime("%I"))
        am_pm = target_time.strftime("%p").lower()
        hour_str = f"{hour_int}{am_pm}"
        return f"bitcoin-up-or-down-{month}-{day}-{hour_str}-et"

    def find_active_market(self):
        now_et = datetime.now(TZ_ET)
        
        # Check Current Hour and Next Hour
        for i in range(2):
            target_time = now_et + timedelta(hours=i)
            slug = self.generate_slug(target_time)
            
            logger.info(f"Scanning slug: {slug}")
            
            try:
                resp = self.session.get(POLY_GAMMA_API, params={"slug": slug}, timeout=5)
                if resp.status_code != 200: continue
                    
                data = resp.json()
                if not data: continue

                event = data[0] if isinstance(data, list) else data
                markets = event.get('markets', [])

                for market in markets:
                    if market.get('closed'): continue

                    raw_ids = market.get('clobTokenIds')
                    token_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
                    yes_token_id = token_ids[0]

                    # Check validity via midpoint
                    mid_price = self.get_midpoint_price(yes_token_id)
                    
                    if mid_price is not None:
                        # 1. Get Expiration Time
                        end_date_str = event.get('endDate').replace("Z", "+00:00")
                        try:
                            end_date_dt = datetime.fromisoformat(end_date_str)
                        except:
                            end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)

                        # 2. DETERMINISTIC START TIME (Top of the Previous Hour)
                        # If expires at 5:00:00, Start is 4:00:00
                        strike_time_dt = end_date_dt - timedelta(hours=1)
                        # Sanitize: Enforce :00:00 just to be safe
                        strike_time_dt = strike_time_dt.replace(minute=0, second=0, microsecond=0)

                        # 3. RETRY LOOP FOR STRIKE PRICE
                        strike = None
                        
                        while strike is None:
                            # Abort if market expires
                            if datetime.now(timezone.utc) > end_date_dt:
                                logger.warning("Market expired before Strike found.")
                                return None

                            # Query Binance for that specific hour candle
                            strike = self.get_binance_hour_open(strike_time_dt)
                            
                            if strike is None:
                                logger.warning(f"Waiting for Binance 1H Candle Open at {strike_time_dt.strftime('%H:%M')}... Retrying in 30s")
                                time.sleep(30)
                            else:
                                logger.info(f"Strike Price Found: ${strike} (Candle: {strike_time_dt.strftime('%H:%M')})")

                        return {
                            "slug": slug,
                            "question": market.get('question'),
                            "strike": strike,
                            "end_date_dt": end_date_dt,
                            "yes_token_id": yes_token_id
                        }
            except Exception as e:
                logger.error(f"Discovery Error: {e}")
                time.sleep(5)
        return None

    def setup_directories(self, market_data):
        now = datetime.now()
        date_folder = now.strftime("%Y-%m-%d")
        
        end_time = market_data['end_date_dt'].astimezone(TZ_ET)
        hour_prefix = end_time.strftime("%H%M")
        
        event_folder_name = f"{hour_prefix}_{market_data['slug']}"
        full_path = DATA_ROOT / date_folder / event_folder_name
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def run(self):
        while True:
            # 1. DISCOVERY
            market = self.find_active_market()
            if not market:
                logger.warning("No active market found. Retrying in 10s...")
                time.sleep(10)
                continue
            
            logger.info(f"✅ TRACKING: {market['question']} (Strike: ${market['strike']:.2f})")
            
            # 2. FILE SETUP
            save_dir = self.setup_directories(market)
            csv_path = save_dir / "market_data.csv"
            write_header = not csv_path.exists()
            
            # 3. COLLECTION LOOP
            with open(csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                
                if write_header:
                    writer.writerow(["timestamp", "time_readable", "btc_price", "strike_price", "poly_yes_price"])
                
                logger.info("Starting Collection... (Ctrl+C to stop)")
                
                while True:
                    loop_start = time.time()
                    now_utc = datetime.now(timezone.utc)
                    
                    if now_utc > market['end_date_dt']:
                        logger.info("⌛ Market Expired. Rolling over...")
                        break 
                    
                    try:
                        ts = time.time()
                        btc = self.get_binance_price()
                        yes_price = self.get_midpoint_price(market['yes_token_id'])
                        
                        if btc is not None and yes_price is not None:
                            time_readable = datetime.now().strftime("%H:%M:%S")
                            writer.writerow([ts, time_readable, btc, market['strike'], yes_price])
                            f.flush()
                            
                            # Terminal Output
                            time_left = market['end_date_dt'] - now_utc
                            mins, secs = divmod(time_left.seconds, 60)
                            print(f"\rBTC: ${btc:.2f} | Strike: ${market['strike']:.2f} | Yes: {yes_price:.2f} ({yes_price*100:.0f}%) | Time: {mins}m {secs}s  ", end="")
                        
                    except Exception as e:
                        logger.error(f"Loop Error: {e}")
                        
                    elapsed = time.time() - loop_start
                    time.sleep(max(0, POLL_INTERVAL - elapsed))

if __name__ == "__main__":
    try:
        PolySimpleCollector().run()
    except KeyboardInterrupt:
        print("\nBot Stopped.")
