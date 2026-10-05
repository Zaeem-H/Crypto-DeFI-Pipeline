import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from src.utils.db_connection import get_engine

def generate_html_report():
    """
    Extracts the latest harmonised data from the PostgreSQL Gold layer and 
    generates an interactive HTML scatter plot visualisation.
    
    The visualisation compares protocol utility (Total Value Locked) against 
    speculative market valuation (Market Capitalisation), highlighting global 
    trending status.
    
    Raises:
        RuntimeError: If report generation fails due to database or file system errors.
    """
    print("Generating Automated Visualisation Report...")
    engine = get_engine()
    
    # The query isolates the most recent snapshot for each token and protocol using DISTINCT ON,
    # then joins them through the bridging schema to calculate core valuation metrics.
    query = """
    WITH LatestMarket AS (
        SELECT DISTINCT ON (token_key) token_key, price_usd, market_cap_usd, is_trending
        FROM fact_token_market
        ORDER BY token_key, timestamp DESC
    ),
    LatestTVL AS (
        SELECT DISTINCT ON (protocol_key) protocol_key, tvl_usd
        FROM fact_protocol_tvl
        ORDER BY protocol_key, timestamp DESC
    )
    SELECT 
        p.name AS protocol,
        t.symbol,
        m.price_usd AS price,
        m.market_cap_usd / 1000000000 AS mcap_billions,
        tvl.tvl_usd / 1000000000 AS tvl_billions,
        m.is_trending
    FROM dim_tokens t
    JOIN protocol_token_map bridge ON t.token_key = bridge.token_key
    JOIN dim_protocols p ON bridge.protocol_key = p.protocol_key
    JOIN LatestMarket m ON t.token_key = m.token_key
    JOIN LatestTVL tvl ON p.protocol_key = tvl.protocol_key
    WHERE m.price_usd > 0 AND m.market_cap_usd > 0
    ORDER BY tvl.tvl_usd DESC
    LIMIT 500
    """
    
    try:
        # Establish connection and load query results into a Pandas DataFrame
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            
        if df.empty:
            print("No data found to visualise yet. Skipping report generation.")
            return

        # Construct the scatter plot using Plotly Express with logarithmic scaling
        # to handle the extreme variance in cryptocurrency market capitalisations.
        # Note: 'color' is used as a keyword argument here as it is required by the Plotly API.
        fig = px.scatter(
            df, 
            x="tvl_billions", 
            y="mcap_billions", 
            hover_name="protocol",
            hover_data=["symbol", "price"],
            color="is_trending",
            color_discrete_map={True: 'red', False: '#1f77b4'},
            log_x=True, 
            log_y=True,
            title=f"DeFi Protocol Valuation (Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')})",
            labels={"tvl_billions": "Total Value Locked (Billions)", "mcap_billions": "Market Cap (Billions)"}
        )
        
        # Robust path resolution with Docker permission fallback
        base_dir = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
        reports_dir = os.path.join(base_dir, 'reports')
        filepath = os.path.join(reports_dir, 'latest_market_report.html')
        
        try:
            # Attempt to create the directory in the standard Airflow home path
            os.makedirs(reports_dir, exist_ok=True)
            # Test write access before allowing Plotly to attempt the save operation
            with open(filepath, 'w') as f:
                pass
        except (OSError, PermissionError):
            # Fallback to the universally writable /tmp/ directory if Docker volume permissions fail
            print(f"Permission denied for {reports_dir}. Falling back to /tmp/reports/")
            reports_dir = '/tmp/reports'
            os.makedirs(reports_dir, exist_ok=True)
            filepath = os.path.join(reports_dir, 'latest_market_report.html')

        # Write the final interactive HTML file to the filesystem
        fig.write_html(filepath)
        print(f"Successfully generated report at: {filepath}")
        
    except Exception as e:
        # Raise an explicit error so the Airflow orchestrator marks the task as FAILED
        raise RuntimeError(f"Report generation failed: {e}")