import os
import sys
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowSkipException

# Configure standard Airflow Python logging
log = logging.getLogger(__name__)

# Fallback path injection 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from config.settings import KAFKA_TOPICS
from src.kafka.consumers.bronze_consumer import consume_to_list
from src.load.bronze_loader import save_bronze_file
from src.transform.market_transformer import transform_market_data
from src.transform.trending_transformer import transform_trending_data
from src.transform.tvl_transformer import transform_tvl_data
from src.load.fact_loader import load_market_data, load_trending_data, load_tvl_data

# Import analytics and utility tasks
from src.analytics.data_quality import run_data_quality_checks
from src.utils.cleanup_old_files import cleanup_old_files
from src.analytics.report_generator import generate_html_report

# Wrapper functions for Airflow tasks
def extract_to_bronze(topic_key: str, **kwargs):
    """Extracts messages from the specified Kafka topic and saves them to the Bronze layer."""
    topic_name = KAFKA_TOPICS[topic_key]
    run_id = kwargs['dag_run'].run_id 
    
    log.info(f"Starting extraction for {topic_key} from {topic_name}")
    messages = consume_to_list(topic_name, group_id=f"airflow_group_{topic_key}")
    
    if not messages:
        log.warning(f"No messages found in {topic_name}.")
        raise AirflowSkipException(f"No messages in {topic_name}. Skipping downstream tasks.")
        
    bronze_filepath = save_bronze_file(topic_name, messages, run_id)
    log.info(f"Successfully saved Bronze file to {bronze_filepath}")
    return bronze_filepath

def transform_to_silver(task_id: str, transform_func, **kwargs):
    """Pulls the Bronze filepath from XCom, applies transformations, and saves to the Silver layer."""
    ti = kwargs['ti']
    bronze_filepath = ti.xcom_pull(task_ids=task_id, key="return_value") 
    
    if not bronze_filepath:
        raise AirflowSkipException("No Bronze file found in XCom.")
        
    log.info(f"Transforming file: {bronze_filepath}")
    silver_filepath = transform_func(bronze_filepath)
    
    if not silver_filepath:
        raise AirflowSkipException("Transformation failed or returned empty.")
        
    return silver_filepath

def load_to_gold(task_id: str, load_func, **kwargs):
    """Pulls the Silver filepath from XCom and loads the structured data into PostgreSQL."""
    ti = kwargs['ti']
    silver_filepath = ti.xcom_pull(task_ids=task_id, key="return_value")
    
    if not silver_filepath:
        raise AirflowSkipException("No Silver file found in XCom.")
        
    log.info(f"Loading file to Postgres: {silver_filepath}")
    load_func(silver_filepath)


# Define the DAG configuration
default_args = {
    'owner': '5590473',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,                           
    'retry_delay': timedelta(minutes=2),    
}

with DAG(
    'crypto_pipeline_dag',
    default_args=default_args,
    description='ETL pipeline for cryptocurrency market, trending, and TVL data',
    schedule_interval="*/15 * * * *",       
    start_date=datetime(2026, 3, 1),        
    catchup=False,
    max_active_runs=1,                      
    tags=['crypto', 'etl'],
) as dag:

    # Define the post-load processing tasks
    validate_task = PythonOperator(
        task_id='validate_data_quality', 
        python_callable=run_data_quality_checks
    )
    
    cleanup_task = PythonOperator(
        task_id='cleanup_old_data', 
        python_callable=cleanup_old_files
    )
    
    visualise_task = PythonOperator(
        task_id='generate_visualisation_report', 
        python_callable=generate_html_report
    )

    # Dynamic task generation loop
    pipelines = {
        "market": (transform_market_data, load_market_data),
        "trending": (transform_trending_data, load_trending_data),
        "tvl": (transform_tvl_data, load_tvl_data)
    }

    # Create an empty list to store the three load tasks.
    # This instructs the validator task to wait until all loads are finished.
    load_tasks = []

    for stream_name, (transform_func, load_func) in pipelines.items():
        
        extract_task_id = f'extract_{stream_name}_bronze'
        transform_task_id = f'transform_{stream_name}_silver'
        load_task_id = f'load_{stream_name}_gold'

        extract_task = PythonOperator(
            task_id=extract_task_id,
            python_callable=extract_to_bronze,
            op_kwargs={'topic_key': stream_name},
        )

        transform_task = PythonOperator(
            task_id=transform_task_id,
            python_callable=transform_to_silver,
            op_kwargs={'task_id': extract_task_id, 'transform_func': transform_func},
        )

        load_task = PythonOperator(
            task_id=load_task_id,
            python_callable=load_to_gold,
            op_kwargs={'task_id': transform_task_id, 'load_func': load_func},
        )

        # Define the dependency arrow for this specific data stream
        extract_task >> transform_task >> load_task
        
        # Add the load task to the tracking list
        load_tasks.append(load_task)

    # Master dependency flow
    # Wait for all loaders to finish, then validate the database, clean old files, and generate the visualisation.
    load_tasks >> validate_task >> cleanup_task >> visualise_task