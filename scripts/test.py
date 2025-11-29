import requests

def get_series_names():
    url = "https://gamma-api.polymarket.com/series"
    try:
        response = requests.get(url)
        response.raise_for_status()
        series_list = response.json()
        
        # Loop through the list and print only the 'title'
        for series in series_list:
            print(series.get('title'))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_series_names()
