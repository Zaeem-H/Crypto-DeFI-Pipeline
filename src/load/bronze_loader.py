import json
import os
from config.settings import BRONZE_DIR, KAFKA_TOPICS

# Map topics to clean directory names
TOPIC_TO_FOLDER = {
    KAFKA_TOPICS["market"]: "coincap",
    KAFKA_TOPICS["trending"]: "coingecko",
    KAFKA_TOPICS["tvl"]: "defillama"
}

def save_bronze_file(topic_name: str, messages: list, run_id: str) -> str:
    """Saves a batch of JSON payloads to the local disk (Pure ETL Staging Layer).

    Utilises atomic writing to prevent file corruption during container crashes
    or abrupt pipeline terminations.

    Args:
        topic_name (str): The Kafka topic from which the messages were extracted.
        messages (list): A list of JSON payloads consumed from the topic.
        run_id (str): The unique Airflow DAG execution identifier.

    Returns:
        str: The absolute filepath to the safely written Bronze JSON file, 
        allowing Airflow to pass it to the transformer via XCom.
    """
    
    # Determine the correct subfolder based on the topic
    folder_name = TOPIC_TO_FOLDER.get(topic_name, "other")
    target_dir = os.path.join(BRONZE_DIR, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Clean the Airflow run_id to ensure a safe and compatible filename
    safe_run_id = str(run_id).replace(':', '').replace('-', '').replace('+', '').replace('T', '_')
    
    filename = f"batch_{folder_name}_{safe_run_id}.json"
    filepath = os.path.join(target_dir, filename)
    tmp_filepath = filepath + ".tmp"
    
    # Atomic Write: Dump to a temporary file first
    with open(tmp_filepath, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
        
    # Atomic Rename: Instantly convert to the final file, ensuring no partial writes occur
    os.rename(tmp_filepath, filepath)
        
    print(f"Staged {len(messages)} raw records safely to {filepath}")
    
    return filepath