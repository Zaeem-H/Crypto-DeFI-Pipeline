FROM apache/airflow:2.7.3-python3.8

USER root

# Install system dependencies required for psycopg2 integration
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install required Data Engineering Python packages directly to ensure a lightweight image
RUN pip install --no-cache-dir \
    pandas \
    sqlalchemy \
    psycopg2-binary \
    pydantic \
    kafka-python \
    requests \
    python-dotenv python-dotenv \
    plotly

# Temporarily elevate privileges to configure the entrypoint script execution permissions
USER root
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER airflow

ENTRYPOINT ["/entrypoint.sh"]