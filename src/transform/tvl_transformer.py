import json
import os
import pandas as pd
from src.models.protocol_tvl import DefiLlamaProtocol
from config.settings import SILVER_DIR

def transform_tvl_data(bronze_filepath: str) -> str:
    """Reads raw Bronze JSON payloads, validates them via Pydantic, filters anomalous data, and saves the output as a Silver CSV.

    Args:
        bronze_filepath (str): The absolute file path to the raw JSON batch file in the Bronze layer.

    Returns:
        str: The absolute file path to the cleaned and validated CSV file in the Silver layer.
    """
    print(f"Transforming TVL Data from: {bronze_filepath}")
    
    with open(bronze_filepath, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    valid_records = []
    dropped = 0
    
    for item in raw_data:
        try:
            validated = DefiLlamaProtocol(**item)
            valid_records.append(validated.model_dump(by_alias=False))
        except Exception:
            dropped += 1

    if dropped > 0:
        print(f"Dropped {dropped} invalid TVL records (usually missing tokens).")

    df = pd.DataFrame(valid_records)
    
    # Data Quality Filter: Exclude records with negative Total Value Locked metrics
    if not df.empty:
        df = df[df['tvl_usd'] >= 0]
    
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')

    # Create the target subdirectory if it does not already exist
    target_dir = os.path.join(SILVER_DIR, 'tvl')
    os.makedirs(target_dir, exist_ok=True)

    # Retain exact batch traceability within the filename
    filename = os.path.basename(bronze_filepath).replace('batch_', 'clean_').replace('.json', '.csv')
    silver_filepath = os.path.join(target_dir, filename)
    
    df.to_csv(silver_filepath, index=False)
    print(f"Saved {len(df)} cleaned TVL records to {silver_filepath}")
    
    return silver_filepath