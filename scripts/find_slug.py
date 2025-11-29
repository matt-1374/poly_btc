import requests
import json
from datetime import datetime, timedelta
import pytz

def get_target_hourly_market_url():
    # 1. Get current time in ET
    et_tz = pytz.timezone('US/Eastern')
    now = datetime.now(et_tz)
    
    # 2. TARGET THE NEXT EXPIRATION
    # If it is 1:50 PM, we want the "2pm" market (which expires in 10 mins)
    # If you want the market that JUST started, change hours=1 to hours=0
    expiration_time = now + timedelta(hours=0)
    
    # 3. Format the slug parts
    month = expiration_time.strftime("%B").lower() # e.g. "november"
    day = expiration_time.day                      # e.g. "27"
    
    # Format Hour (e.g. "1pm", "2pm")
    hour_int = int(expiration_time.strftime("%I")) 
    am_pm = expiration_time.strftime("%p").lower()
    hour_str = f"{hour_int}{am_pm}"
    
    # 4. Construct the Slug
    slug = f"bitcoin-up-or-down-{month}-{day}-{hour_str}-et"
    
    print(f"Calculated Slug: {slug}")
    print("Fetching details from API...")
    
    # 5. Fetch from Gamma API to get the Market ID (tid)
    url = "https://gamma-api.polymarket.com/events"
    params = {"slug": slug}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data:
            event = data[0] if isinstance(data, list) else data
            
            # 6. Get the First Market ID (This is the 'tid')
            markets = event.get('markets', [])
            if markets:
                first_market = markets[0]
                market_id = first_market.get('id')
                
                # --- GENERATE THE CORRECT URL ---
                final_url = f"https://polymarket.com/event/{slug}?tid={market_id}"
                
                print("\n" + "="*60)
                print(f"✅ CORRECT URL: {final_url}")
                print("="*60 + "\n")
                
                # Print IDs for your bot
                print(f"Event ID: {event.get('id')}")
                if 'clobTokenIds' in first_market:
                    raw_ids = first_market['clobTokenIds']
                    t_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
                    print(f"Yes Token ID: {t_ids[0]}")
            else:
                print("Event found, but no markets inside it yet.")
                print(f"Base URL: https://polymarket.com/event/{slug}")
                
        else:
            print(f"Market '{slug}' not found yet. (It might be too early).")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_target_hourly_market_url()
