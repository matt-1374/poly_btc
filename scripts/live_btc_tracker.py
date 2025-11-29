import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
# PASTE THE ACTIVE TOKEN ID YOU FOUND HERE
# Example: "2173812938120938102938120938"
TARGET_TOKEN_ID = "97363386097795743259869678564252955512233011824024063453883355723713172563997" 

def track_live_price(token_id):
    url = "https://clob.polymarket.com/midpoint"
    params = {"token_id": token_id}
    
    print(f"--- 🔴 STARTED LIVE TRACKING (Token: {token_id[:10]}...) ---")
    print(f"{'TIMESTAMP':<10} | {'PRICE':<10} | {'PROBABILITY':<10}")
    print("-" * 40)

    while True:
        try:
            # 1. Fetch Data
            response = requests.get(url, params=params, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                mid_str = data.get('mid')
                
                if mid_str:
                    # 2. Parse Data
                    price = float(mid_str)
                    prob = price * 100
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # 3. Output to Terminal
                    # We use \r and end='' to overwrite the line if you prefer a static dashboard
                    # But for a log (requested), we usually print new lines.
                    print(f"{timestamp:<10} | ${price:<9.3f} | {prob:<9.1f}%")
                else:
                    print("No midpoint data available (Illiquid).")
            
            elif response.status_code == 429:
                print("Rate limited! Slowing down...")
                time.sleep(2)
            else:
                print(f"API Error: {response.status_code}")

            # 4. Wait 1 Second (Polymarket rate limits are generous, but 1s is safe)
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Tracking stopped by user.")
            break
        except Exception as e:
            print(f"Connection Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    if TARGET_TOKEN_ID == "YOUR_TOKEN_ID_HERE":
        print("⚠️  PLEASE EDIT THE SCRIPT AND PASTE YOUR TOKEN ID FIRST!")
    else:
        track_live_price(TARGET_TOKEN_ID)
