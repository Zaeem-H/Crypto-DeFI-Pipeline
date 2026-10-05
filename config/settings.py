import os
from dotenv import load_dotenv

# Load environment variables (crucial for local testing outside Docker)
load_dotenv()

# System Paths
# If running inside Docker, AIRFLOW_HOME is /opt/airflow. Otherwise, local repository root.
ROOT_DIR = os.getenv('AIRFLOW_HOME', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DATA_DIR = os.path.join(ROOT_DIR, 'data')
BRONZE_DIR = os.path.join(DATA_DIR, 'bronze')
SILVER_DIR = os.path.join(DATA_DIR, 'silver')
GOLD_DIR = os.path.join(DATA_DIR, 'gold')

SQL_DIR = os.path.join(ROOT_DIR, 'src', 'sql')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')

# Ensure local directories exist
for path in [DATA_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR, SQL_DIR, REPORTS_DIR]:
    os.makedirs(path, exist_ok=True)

# PostgreSQL Configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"), # Localhost fallback for external scripts
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "crypto_pipeline"),
    "user": os.getenv("POSTGRES_USER", "airflow"),
    "password": os.getenv("POSTGRES_PASSWORD", "airflow"),
}

# Master SQLAlchemy string for our Python scripts
DB_CONN = f"postgresql+psycopg2://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"

# Kafka Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

KAFKA_TOPICS = {
    "market": os.getenv("KAFKA_TOPIC_MARKET", "crypto.market.coincap"),
    "trending": os.getenv("KAFKA_TOPIC_TRENDING", "crypto.market.trending"),
    "tvl": os.getenv("KAFKA_TOPIC_TVL", "crypto.defi.tvl"),
}

# API Endpoints & Keys
COINCAP_API_KEY = os.getenv("COINCAP_API_KEY", "")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

API_ENDPOINTS = {
    "market": "https://rest.coincap.io/v3/assets",
    "trending": "https://api.coingecko.com/api/v3/search/trending",
    "tvl": "https://api.llama.fi/protocols"
}

# Polling Intervals (Seconds)
POLL_INTERVAL_COINCAP = 30
POLL_INTERVAL_COINGECKO = 60
POLL_INTERVAL_DEFILLAMA = 120