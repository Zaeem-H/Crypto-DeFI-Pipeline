#!/bin/bash
set -e

# We only run the DB setup on the webserver container to prevent
# race conditions and database locks from the scheduler container
if [ "$1" = "webserver" ]; then
    echo "Initializing Airflow database..."
    airflow db migrate

    echo "Creating default admin user..."
    airflow users create \
      --username admin \
      --password admin \
      --firstname admin \
      --lastname user \
      --role Admin \
      --email admin@example.com || true
fi

echo "Starting Airflow service..."
exec airflow "$@"