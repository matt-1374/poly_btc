import requests
import json
import time

def get_midpoint_price(token_id):
    """
    Fetches the midpoint price using the CLOB endpoint.
    """
    url = "https://clob.polymarket.com/midpoint"
    params = {"token_id": token_id}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # The API returns {"mid": "0.55"}
        return float(data.get('mid', 0))
    except Exception:
        return None

def scan_event_midpoints(event_id):
    # 1. Fetch Event Details
    gamma_url = "https://gamma-api.polymarket.com/events"
    try:
        response = requests.get(gamma_url, params={"id": event_id})
        data = response.json()
        
        if not data:
            print("Event not found.")
            return

        event = data[0] if isinstance(data, list) else data
        print(f"--- EVENT: {event['title']} ---")
        print(f"Event ID: {event['id']}")
        print("Fetching prices via /midpoint endpoint...\n")
        
        markets = event.get('markets', [])
        
        # 2. Loop through ALL markets to find the active one
        for i, market in enumerate(markets):
            question = market.get('question')
            
            # Parse Token IDs
            raw_ids = market.get('clobTokenIds')
            token_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
            yes_token_id = token_ids[0]
            
            # 3. USE THE NEW MIDPOINT ENDPOINT
            mid_price = get_midpoint_price(yes_token_id)
            
            if mid_price is not None:
                prob = mid_price * 100
                
                # Logic to determine status
                status = "✅ ACTIVE"
                if mid_price > 0.97: status = "🔒 WON (Deep ITM)"
                if mid_price < 0.03: status = "❌ LOST (Deep OTM)"
                
                print(f"Option {i+1}: {question}")
                print(f"   > Midpoint: {mid_price} ({prob:.1f}%)")
                print(f"   > Status:   {status}")
                print(f"   > Token ID: {yes_token_id}") # Copy this one!
                print("-" * 50)
            else:
                print(f"Option {i+1}: {question} (No liquidity/price)")
            
            # Tiny sleep to be polite to the API
            time.sleep(0.1)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    TARGET_EVENT_ID = 90320
    
    scan_event_midpoints(TARGET_EVENT_ID)
