import time
import requests
from config.settings import API_ENDPOINTS, COINGECKO_API_KEY

def fetch_trending_data():
    """
    Fetches currently trending coins based on global search volume 
    using the CoinGecko API.
    """
    url = API_ENDPOINTS["trending"]
    
    # Add the User-Agent and CoinGecko's specific API key header
    headers = {
        'User-Agent': 'crypto-pipeline/1.0',
        'x-cg-demo-api-key': COINGECKO_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        payload = response.json()
        payload['timestamp'] = time.time()
        
        return payload
    except Exception as e:
        print(f"[CoinGecko Client] Error fetching data: {e}")
        # Return a consistent dictionary structure on failure to prevent downstream pipeline crashes
        return {"coins": [], "timestamp": time.time()}