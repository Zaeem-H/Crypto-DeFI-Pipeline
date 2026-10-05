import time
import requests
from config.settings import API_ENDPOINTS

def fetch_tvl_data():
    """
    Fetches Total Value Locked (TVL) metrics for decentralised finance (DeFi) 
    protocols using the DefiLlama API.
    """
    url = API_ENDPOINTS["tvl"]
    headers = {"User-Agent": "crypto-pipeline/1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        current_time = time.time()
        valid_data = []
        
        # Defensive check to ensure only valid dictionaries are processed, safeguarding downstream tasks
        for item in data:
            if isinstance(item, dict):
                item['timestamp'] = current_time
                valid_data.append(item)
                
        return valid_data
    except Exception as e:
        print(f"[DefiLlama Client] Error fetching data: {e}")
        # Return a consistent empty list on failure to prevent pipeline crashes
        return []