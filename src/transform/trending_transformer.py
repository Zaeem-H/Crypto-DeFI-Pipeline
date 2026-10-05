import json
import os
import pandas as pd
from src.models.trending_coin import CoinGeckoTrending
from config.settings import SILVER_DIR

def transform_trending_data(bronze_filepath: str) -> str:
    """Reads nested Bronze JSON payloads, un-nests them, validates via Pydantic, and saves the output as a Silver CSV.

    Args:
        bronze_filepath (str): The absolute file path to the raw JSON batch file in the Bronze layer.

    Returns:
        str: The absolute file path to the cleaned and validated CSV file in the Silver layer.
    """
    print(f"Transforming Trending Data from: {bronze_filepath}")
    
    with open(bronze_filepath, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    records = []

    for payload in raw_data:
        try:
            validated_payload = CoinGeckoTrending(**payload)
            timestamp = validated_payload.timestamp
            
            # Un-nest the coins from this specific market snapshot
            for coin in validated_payload.coins:
                record = coin.item.model_dump(by_alias=False)
                record['timestamp'] = timestamp
                records.append(record)
        except Exception as e:
            print(f"Invalid CoinGecko payload skipped: {e}")

    df = pd.DataFrame(records)
    
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')

    target_dir = os.path.join(SILVER_DIR, 'trending')
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.basename(bronze_filepath).replace('batch_', 'clean_').replace('.json', '.csv')
    silver_filepath = os.path.join(target_dir, filename)
    
    df.to_csv(silver_filepath, index=False)
    print(f"Saved {len(df)} cleaned trending records to {silver_filepath}")
    
    return silver_filepath