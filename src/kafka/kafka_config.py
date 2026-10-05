from kafka import KafkaProducer, KafkaConsumer
import json
from config.settings import KAFKA_BROKER

def create_producer() -> KafkaProducer:
    """Creates and returns a globally configured Apache Kafka Producer.

    Returns:
        KafkaProducer: An instantiated producer configured to serialise 
        messages into JSON bytes and keys into UTF-8 strings.
    """
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        # Serialises Python dictionaries into JSON byte arrays
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        # Serialises string keys into byte arrays (safely ignores if None)
        key_serializer=lambda k: k.encode("utf-8") if k else None
    )

def create_consumer(topic: str, group_id: str) -> KafkaConsumer:
    """Creates and returns a globally configured Apache Kafka Consumer.

    Args:
        topic (str): The name of the Kafka topic to subscribe to.
        group_id (str): The consumer group ID for offset management.

    Returns:
        KafkaConsumer: An instantiated consumer configured to deserialise 
        JSON payloads and automatically timeout after 10 seconds of inactivity.
    """
    return KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=group_id,
        # Deserialises JSON byte arrays back into Python dictionaries
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        # Deserialises byte array keys back into strings
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        # Terminates the polling loop after 10 seconds of silence, 
        # allowing the Airflow DAG to proceed to downstream tasks.
        consumer_timeout_ms=10000 
    )