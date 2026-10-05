import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.load.fact_loader import load_market_data

@patch('src.load.fact_loader.get_engine')
def test_load_market_data(mock_get_engine, tmp_path):
    """Tests the load script to ensure it interacts with the database engine correctly.

    This test utilises a temporary directory to host a simulated Silver layer 
    CSV file and mocks the SQLAlchemy engine and connection to verify that 
    the loading logic executes the expected number of database operations 
    without requiring a live PostgreSQL instance.

    Args:
        mock_get_engine (MagicMock): Mocked version of the get_engine utility.
        tmp_path (pathlib.Path): Pytest fixture providing a temporary directory.
    """
    # Create a simulated Silver CSV file for the test case
    silver_file = tmp_path / "clean_market_test.csv"
    
    mock_df = pd.DataFrame({
        "api_id": ["bitcoin"],
        "symbol": ["BTC"],
        "name": ["Bitcoin"],
        "price_usd": [50000.0],
        "volume_24h_usd": [1000000.0],
        "market_cap_usd": [1000000000.0],
        "timestamp": ["2026-03-15 12:00:00"]
    })
    mock_df.to_csv(silver_file, index=False)

    # Configure the mocked database engine and transaction connection
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    
    # Mock the read_sql function used by the loader to retrieve dimension keys
    with patch('src.load.fact_loader.pd.read_sql') as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame({
            "token_key": [1], 
            "api_id": ["bitcoin"]
        })
        
        # Execute the loading function
        load_market_data(str(silver_file))
        
        # Verify that the database connection was utilised for both Dimensions and Facts
        assert mock_conn.execute.call_count >= 2, "Database execute was not called the expected number of times."