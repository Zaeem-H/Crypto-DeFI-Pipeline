from airflow.exceptions import AirflowSkipException
from src.kafka.kafka_config import create_consumer

def consume_to_list(topic_name: str, group_id: str = 'airflow_etl_group') -> list:
    """Consumes all available messages from an Apache Kafka topic into a Python list.

    Args:
        topic_name (str): The name of the Kafka topic to consume messages from.
        group_id (str, optional): The Kafka consumer group ID. Defaults to 'airflow_etl_group'.

    Returns:
        list: A list containing all the message payloads consumed from the specified topic.

    Raises:
        Exception: If a connection or processing error occurs while consuming from Kafka.
        AirflowSkipException: If no messages are retrieved, safely skipping subsequent Airflow tasks.
    """
    print(f"Connecting to Kafka topic: {topic_name}...")
    
    # Instantiate the consumer using the unified configuration
    consumer = create_consumer(topic_name, group_id)
    messages = []
    
    try:
        # The consumer will automatically break this loop after 10 seconds of inactivity
        # (configured via consumer_timeout_ms=10000 in kafka_config.py)
        for msg in consumer:
            messages.append(msg.value)
    except Exception as e:
        print(f"Error consuming from {topic_name}: {e}")
        raise e
    finally:
        # Always close the connection to prevent memory leaks and release resources
        consumer.close()

    # If the producers have not transmitted any data, safely skip the subsequent Airflow tasks
    if not messages:
        print(f"No new data found in {topic_name}.")
        raise AirflowSkipException(f"Stream {topic_name} is empty. Skipping downstream tasks.")

    print(f"Successfully consumed {len(messages)} messages from {topic_name}.")
    return messages