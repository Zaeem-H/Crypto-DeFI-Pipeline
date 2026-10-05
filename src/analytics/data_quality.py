import pandas as pd
from sqlalchemy import text
from src.utils.db_connection import get_engine

def run_data_quality_checks():
    """
    Executes SQL audit queries to ensure data integrity within the Data Warehouse.
    If anomalous data (e.g., null prices, negative TVL) is detected, this function 
    acts as an active quality gate, executing DELETE statements to sanitise the 
    Gold layer and preserve analytical accuracy.
    """
    print("Running Data Quality Checks and Active Cleanup...")
    engine = get_engine()
    
    # Define audit rules and their corresponding remediation queries
    quality_gates = {
        "Null Prices in Market Fact": {
            "audit": "SELECT COUNT(*) FROM fact_token_market WHERE price_usd IS NULL",
            "clean": "DELETE FROM fact_token_market WHERE price_usd IS NULL"
        },
        "Negative TVL in Protocols": {
            "audit": "SELECT COUNT(*) FROM fact_protocol_tvl WHERE tvl_usd < 0",
            "clean": "DELETE FROM fact_protocol_tvl WHERE tvl_usd < 0"
        },
        "Orphaned Bridge Records": {
            "audit": "SELECT COUNT(*) FROM protocol_token_map WHERE token_key IS NULL OR protocol_key IS NULL",
            "clean": "DELETE FROM protocol_token_map WHERE token_key IS NULL OR protocol_key IS NULL"
        },
        "Null Timestamps": {
            "audit": "SELECT COUNT(*) FROM fact_token_market WHERE timestamp IS NULL",
            "clean": "DELETE FROM fact_token_market WHERE timestamp IS NULL"
        },
        "Negative or Zero Prices": {
            "audit": "SELECT COUNT(*) FROM fact_token_market WHERE price_usd <= 0",
            "clean": "DELETE FROM fact_token_market WHERE price_usd <= 0"
        }
    }
    
    # Use engine.begin() to automatically commit the DELETE transactions
    with engine.begin() as conn:
        for rule_name, queries in quality_gates.items():
            # Execute the audit query
            invalid_row_count = pd.read_sql(queries["audit"], conn).iloc[0, 0]
            
            if invalid_row_count > 0:
                print(f"DATA QUALITY ALERT: '{rule_name}' found {invalid_row_count} invalid rows.")
                print(f"Executing remediation cleanup for '{rule_name}'...")
                
                # Execute the cleanup query to sanitise the database
                conn.execute(text(queries["clean"]))
                print(f"Cleanup successful. Removed {invalid_row_count} malformed records.")
            else:
                print(f"Check Passed: '{rule_name}'. No invalid rows found.")
                
    print("All Data Quality validations complete. The Gold layer is pristine.")