import time
from src.extract.coingecko_client import fetch_trending_data
from src.kafka.kafka_config import create_producer
from config.settings import KAFKA_TOPICS, POLL_INTERVAL_COINGECKO

def run_producer():
    """Initialises the Kafka producer and continuously streams trending token data.

    This function polls the CoinGecko API at configured intervals, extracts the 
    latest global trending cryptocurrency snapshot, and publishes the entire 
    payload as a single message to the designated Apache Kafka topic.

    Raises:
        Exception: If message transmission to the Kafka broker fails.
    """
    producer = create_producer()
    topic = KAFKA_TOPICS["trending"]
    
    print(f"Starting CoinGecko Producer on topic '{topic}'...")
    while True:
        payload = fetch_trending_data()
        
        # Ensure the payload is valid and contains active trending tokens
        if payload and payload.get("coins"):
            try:
                # Utilise a static routing key as this represents a global market snapshot
                msg_key = "global_trending_snapshot"
                producer.send(topic, key=msg_key, value=payload)
                producer.flush()
                
                # Log the successful transmission alongside the token count
                num_coins = len(payload.get("coins", []))
                print(f"[CoinGecko] Successfully streamed trending snapshot ({num_coins} coins).")
            except Exception as e:
                print(f"[CoinGecko] Kafka send failed: {e}")
            
        time.sleep(POLL_INTERVAL_COINGECKO)

if __name__ == "__main__":
    run_producer()