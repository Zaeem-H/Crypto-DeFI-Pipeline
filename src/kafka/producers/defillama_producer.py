import time
from src.extract.defillama_client import fetch_tvl_data
from src.kafka.kafka_config import create_producer
from config.settings import KAFKA_TOPICS, POLL_INTERVAL_DEFILLAMA

def run_producer():
    """Initialises the Kafka producer and continuously streams Total Value Locked (TVL) data.

    This function polls the DefiLlama API at configured intervals, extracts the 
    latest TVL metrics for decentralised finance (DeFi) protocols, and publishes 
    each protocol as an individual message to the designated Apache Kafka topic.

    Raises:
        Exception: If message transmission to the Kafka broker fails.
    """
    producer = create_producer()
    topic = KAFKA_TOPICS["tvl"]
    
    print(f"Starting DefiLlama Producer on topic '{topic}'...")
    while True:
        data = fetch_tvl_data()
        if data:
            for item in data:
                try:
                    # Utilise the protocol slug as the Kafka key for partition ordering
                    msg_key = str(item.get("slug", "unknown"))
                    producer.send(topic, key=msg_key, value=item)
                except Exception as e:
                    print(f"[DefiLlama] Kafka send failed: {e}")
                
            producer.flush()
            print(f"[DefiLlama] Successfully streamed {len(data)} protocol events.")
            
        time.sleep(POLL_INTERVAL_DEFILLAMA)

if __name__ == "__main__":
    run_producer()