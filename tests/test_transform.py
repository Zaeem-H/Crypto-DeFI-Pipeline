import pytest
import json
import os
import pandas as pd
from src.models.coin_market import CoinCapAsset
from src.models.protocol_tvl import DefiLlamaProtocol
from src.transform.market_transformer import transform_market_data

def test_coincap_model_validation():
    """Tests that the Pydantic model correctly casts data types and standardises symbols.

    This test verifies that the CoinCapAsset model performs mandatory type 
    conversion (e.g., string to float) and executes capitalisation validation 
    on asset symbols to ensure relational consistency.
    """
    raw_data = {
        "id": "bitcoin",
        "symbol": "btc", # Input in lowercase to verify the uppercase validator
        "name": "Bitcoin",
        "priceUsd": "50000.50", # Input as string to verify the float parser
        "timestamp": 1700000000.0
    }
    
    asset = CoinCapAsset(**raw_data)
    
    # Assertions to verify correct data standardisation
    assert asset.symbol == "BTC", "Asset symbol was not capitalised as expected."
    assert isinstance(asset.price_usd, float), "Numerical string was not successfully cast to a float."
    assert asset.price_usd == 50000.50

def test_defillama_model_handles_nulls():
    """Tests that missing numerical values within the payload default to 0.0 safely.

    This test simulates a scenario where the DefiLlama API returns null values 
    for financial metrics, verifying that the model prevents runtime errors 
    by defaulting to a neutral numerical value.
    """
    raw_data = {
        "slug": "uniswap",
        "name": "Uniswap",
        "tvl": None, # Simulating a common API data integrity issue
        "timestamp": 1700000000.0
    }
    
    protocol = DefiLlamaProtocol(**raw_data)
    assert protocol.tvl_usd == 0.0, "Null TVL value did not default to 0.0 correctly."

def test_transform_market_data_drops_invalid_rows(tmp_path, monkeypatch):
    """Tests the transformation pipeline to ensure it functions as a robust quality gate.

    This test utilises a temporary directory to host a simulated Bronze layer 
    JSON file and verifies that the Pandas transformation logic correctly 
    identifies and excludes records containing null or non-positive prices.

    Args:
        tmp_path (pathlib.Path): Pytest fixture providing a temporary directory.
        monkeypatch (pytest.MonkeyPatch): Pytest fixture used to mock environment variables.
    """
    # Create a temporary JSON file to simulate the raw output from the Bronze layer
    bronze_file = tmp_path / "batch_coincap_test.json"
    
    mock_payload = [
        {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "priceUsd": "50000", "timestamp": 1700000},
        {"id": "badcoin", "symbol": "BAD", "name": "Bad", "priceUsd": None, "timestamp": 1700000}, # Should be filtered out
        {"id": "zerocoin", "symbol": "ZERO", "name": "Zero", "priceUsd": "-100", "timestamp": 1700000} # Should be filtered out
    ]
    
    bronze_file.write_text(json.dumps(mock_payload))
    
    # Mock the Silver directory to ensure the output is saved within the temporary test path
    monkeypatch.setattr('src.transform.market_transformer.SILVER_DIR', str(tmp_path))
    
    # Execute the transformation logic
    silver_filepath = transform_market_data(str(bronze_file))
    
    # Extract the resulting CSV to verify the data cleansing operations
    df = pd.read_csv(silver_filepath)
    
    # Assertions to confirm that only high-quality data persists
    assert len(df) == 1, "The transformation pipeline failed to exclude invalid records."
    assert df.iloc[0]['symbol'] == 'BTC', "The incorrect record was preserved during transformation."
    assert 'timestamp' in df.columns, "The mandatory timestamp column is missing from the Silver layer."