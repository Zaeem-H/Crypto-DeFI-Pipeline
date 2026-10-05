DeFi Market Intelligence Pipeline

Live Codespaces Environment: Access Repository Here

Project Overview

This repository contains an end-to-end Data Engineering ETL pipeline. It extracts live cryptocurrency market and protocol data via asynchronous Python producers, streams it through Apache Kafka (Bronze Layer), transforms it using Pandas and Pydantic (Silver Layer), and loads it into a PostgreSQL dimensional star schema (Gold Layer). The pipeline is fully orchestrated using Apache Airflow and visualised via an interactive Streamlit dashboard.

1. Environment Activation

If you are evaluating this project within the provided GitHub Codespace, the environment should be pre-configured (api keys are hard-coded into env and your own key needs adding). To manually activate or update the Conda environment, run the following commands in the terminal:

# Activate the environment
conda activate WM3B7

# (Optional) If dependencies are missing, update the environment:
conda env update -n WM3B7 --file WM3B7_env.yaml


2. Accessing the Live Services

The pipeline components run via Docker containers. Once the containers are spun up (using docker-compose up -d), you can access the live web interfaces through the "Ports" tab in GitHub Codespaces, or via the local links below:

Apache Airflow UI (Orchestration): http://localhost:8080

Username: admin

Password: admin

Usage: Navigate here to view the crypto_pipeline_dag, check the graph view, and monitor task execution logs.

docker-compose logs -f airflow-webserver

Live Streamlit Dashboard (Analytics): http://localhost:8502

Usage: Interactive front-end visualising the Gold layer PostgreSQL data. It queries the database in real-time.

3. Viewing the Automated Snapshot Report

In addition to the live dashboard, the final task in the Airflow DAG automatically generates a static HTML analytical report at the end of every pipeline run.

File Location: reports/latest_market_report.html

How to view: 1. Navigate to the reports folder in the Codespaces file explorer on the left.
2. Right-click latest_market_report.html and select Download.
3. Open the downloaded file in any standard web browser to view the interactive Plotly visualisation.

4. Running the Automated Test Suite

To ensure pipeline reliability and validate the dimensional modelling logic without risking corruption to the production database, a suite of automated unit tests has been engineered using pytest.

Ensure your environment is activated (conda activate WM3B7), then run:

# 1. Ensure pytest is installed
pip install pytest

# 2. Execute the test suite
pytest tests/


What this tests:

test_extract.py: Validates API extraction handling and graceful failure mocking.

test_transform.py: Validates Pydantic schema constraints and Pandas active filtering (Data Quality Gates).

test_load.py: Validates PostgreSQL engine connections and UPSERT statement logic.

5. Database Inspection (PostgreSQL)

If you would like to inspect the raw tables and execute SQL queries directly against the Gold layer, you can access the PostgreSQL interactive terminal (psql) running inside the Docker container.

Run the following command in your Codespaces terminal:

docker exec -it crypto_postgres psql -U airflow -d crypto_pipeline

Useful commands once connected:

\dt : List all tables in the database (e.g., dim_tokens, fact_token_market, protocol_token_map).

SELECT * FROM dim_tokens LIMIT 5; : View the first 5 descriptive dimension records.

SELECT count(*) FROM fact_token_market; : See how many streaming records have been ingested.

SELECT 
    p.name AS protocol_name, 
    p.category,
    t.symbol AS token_symbol,
    t.name AS token_name
FROM protocol_token_map bridge
JOIN dim_protocols p ON bridge.protocol_key = p.protocol_key
JOIN dim_tokens t ON bridge.token_key = t.token_key
ORDER BY p.name ASC
LIMIT 10;

SELECT 
    (SELECT COUNT(*) FROM fact_token_market WHERE price_usd IS NULL) as null_prices,
    (SELECT COUNT(*) FROM fact_protocol_tvl WHERE tvl_usd < 0) as negative_tvl,
    (SELECT COUNT(*) FROM fact_token_market WHERE price_usd <= 0) as zero_prices;

Audit command should return 0 

\q : Quit the database and return to your normal terminal.

Note: Ai was used to debug and refine code where necessary as well as to add documentation and comments to reduce development time. 