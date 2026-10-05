import time
import requests
from config.settings import API_ENDPOINTS, COINCAP_API_KEY

def fetch_market_data():
    """
    Fetches real-time cryptocurrency financial metrics using the CoinCap V3 API.
    """
    url = API_ENDPOINTS["market"]
    
    # Add the User-Agent and Bearer token for V3 authentication
    headers = {
        "User-Agent": "crypto-pipeline/1.0",
        "Authorization": f"Bearer {COINCAP_API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json().get('data', [])
        current_time = time.time()
        
        for item in data:
            item['timestamp'] = current_time
    
        return data
    except Exception as e:
        print(f"[CoinCap Client] Error fetching data: {e}")
        # Return a consistent empty list instead of None to ensure pipeline stability
        return []