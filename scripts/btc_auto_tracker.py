import requests
import time
import json
import pytz
from datetime import datetime, timedelta

# --- CONFIGURATION ---
REFRESH_RATE = 1.0  # Seconds between price updates
TZ_ET = pytz.timezone('US/Eastern') # Polymarket uses ET for URLs

class PolyAutoBot:
    def __init__(self):
        self.current_token_id = None
        self.current_market_question = None
        self.current_slug = None
        self.target_expiration_hour = -1

    def get_midpoint(self, token_id):
        """
        Fetches the single midpoint price from the CLOB.
        """
        url = "https://clob.polymarket.com/midpoint"
        try:
            resp = requests.get(url, params={"token_id": token_id}, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                mid_str = data.get('mid')
                if mid_str:
                    return float(mid_str)
        except Exception:
            return None
        return None

    def get_target_slug(self):
        """
        YOUR LOGIC: Calculates the slug for the upcoming hourly expiration.
        """
        now = datetime.now(TZ_ET)
        
        # TARGET THE NEXT EXPIRATION (Standard Logic)
        # If it is 1:50 PM, we want the "2pm" market.
        expiration_time = now + timedelta(hours=0)

        month = expiration_time.strftime("%B").lower()
        day = expiration_time.day
        
        # Format Hour (e.g. 1pm, 2pm, 12pm)
        hour_int = int(expiration_time.strftime("%I")) 
        am_pm = expiration_time.strftime("%p").lower()
        hour_str = f"{hour_int}{am_pm}"

        slug = f"bitcoin-up-or-down-{month}-{day}-{hour_str}-et"
        return slug, int(hour_int)

    def find_market_by_slug(self):
        """
        Fetches the Event by slug and strictly takes the FIRST market.
        """
        slug, target_hour = self.get_target_slug()
        
        # Avoid re-fetching if we are already on the correct slug
        if slug == self.current_slug and self.current_token_id:
            return True

        print(f"\n\n🔍 SWITCHING TO NEW MARKET: {slug}")
        
        # 1. Get Event Details
        gamma_url = "https://gamma-api.polymarket.com/events"
        try:
            resp = requests.get(gamma_url, params={"slug": slug}, timeout=5)
            data = resp.json()
            
            if not data:
                print("   ⚠️  Event not found yet via API. Waiting...")
                return False

            event = data[0] if isinstance(data, list) else data
            markets = event.get('markets', [])
            
            if not markets:
                print("   ⚠️  Event found, but no markets inside yet.")
                return False

            # --- STRICT SELECTION LOGIC ---
            # We strictly take the FIRST market, as per your requirement.
            target_market = markets[0]
            
            # Parse Token IDs
            raw_ids = target_market.get('clobTokenIds')
            if isinstance(raw_ids, str):
                token_ids = json.loads(raw_ids)
            else:
                token_ids = raw_ids
            
            # The YES token is Index 0
            yes_token_id = token_ids[0]
            question = target_market.get('question')

            # Update State
            self.current_token_id = yes_token_id
            self.current_market_question = question
            self.current_slug = slug
            self.target_expiration_hour = target_hour
            
            print(f"   ✅ LOCKED MARKET: {question}")
            print(f"   🆔 Token ID: {yes_token_id}")
            print("="*80 + "\n")
            return True

        except Exception as e:
            print(f"   ❌ Lookup Error: {e}")
            return False

    def run(self):
        print("🤖 POLYMARKET BTC LIVE TRACKER")
        print("   (Using strict slug/first-market logic)")

        while True:
            try:
                # 1. Sync Market
                # This checks every loop if the calculated slug has changed (e.g. new hour)
                # or if we don't have a token yet.
                slug_check, _ = self.get_target_slug()
                
                if self.current_token_id is None or slug_check != self.current_slug:
                    found = self.find_market_by_slug()
                    if not found:
                        time.sleep(5)
                        continue

                # 2. Get Live Price
                mid_price = self.get_midpoint(self.current_token_id)
                
                if mid_price is not None:
                    prob = mid_price * 100
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Formatting
                    color = "🟢" if mid_price >= 0.50 else "🔴"
                    
                    # Dashboard Output (Rewrites the same line)
                    output = (
                        f"{color} {timestamp} | "
                        f"PROB: {prob:5.1f}% | "
                        f"PRICE: ${mid_price:.4f} | "
                        f"MKT: {self.current_market_question}"
                    )
                    
                    # Pad output to ensure it clears previous text
                    print(f"\r{output:<110}", end="", flush=True)
                
                else:
                    # Illiquid handling
                    print(f"\r⚠️  {datetime.now().strftime('%H:%M:%S')} | No Midpoint Data (Illiquid)...", end="", flush=True)

                time.sleep(REFRESH_RATE)

            except KeyboardInterrupt:
                print("\n\n🛑 Bot Stopped.")
                break
            except Exception as e:
                print(f"\n⚠️  Loop Error: {e}")
                time.sleep(2)

if __name__ == "__main__":
    bot = PolyAutoBot()
    bot.run()
