import time
from src.extract.coincap_client import fetch_market_data
from src.kafka.kafka_config import create_producer
from config.settings import KAFKA_TOPICS, POLL_INTERVAL_COINCAP

def run_producer():
    """Initialises the Kafka producer and continuously streams market data.

    This function polls the CoinCap API at configured intervals, extracts the 
    latest financial metrics, and publishes each asset as an individual message 
    to the designated Apache Kafka topic.

    Raises:
        Exception: If message transmission to the Kafka broker fails.
    """
    producer = create_producer()
    topic = KAFKA_TOPICS["market"]
    
    print(f"Starting CoinCap Producer on topic '{topic}'...")
    while True:
        data = fetch_market_data()
        if data:
            for item in data:
                try:
                    msg_key = str(item.get("id", "unknown"))
                    producer.send(topic, key=msg_key, value=item)
                except Exception as e:
                    print(f"[CoinCap] Kafka send failed: {e}")
            
            producer.flush()
            print(f"[CoinCap] Successfully streamed {len(data)} market events.")
            
        time.sleep(POLL_INTERVAL_COINCAP)

if __name__ == "__main__":
    run_producer()