import pytest
from unittest.mock import patch, MagicMock
from src.extract.coincap_client import fetch_market_data
from src.extract.defillama_client import fetch_tvl_data

# 1. Test CoinCap Extractor

@patch('src.extract.coincap_client.requests.get')
def test_fetch_market_data_success(mock_get):
    """Tests that the CoinCap client successfully extracts and timestamps data.
    
    This test mocks a successful 200 OK response from the CoinCap API and 
    verifies that the client correctly parses the JSON payload and injects 
    the mandatory ingestion timestamp.
    """
    # Create a simulated successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': [{'id': 'bitcoin', 'symbol': 'BTC', 'priceUsd': '50000.00'}]
    }
    mock_get.return_value = mock_response

    # Execute the extraction function
    result = fetch_market_data()

    # Assertions to verify expected behaviour
    assert len(result) == 1
    assert result[0]['id'] == 'bitcoin'
    assert 'timestamp' in result[0], "Extractor failed to inject the ingestion timestamp"

@patch('src.extract.coincap_client.requests.get')
def test_fetch_market_data_failure(mock_get):
    """Tests that API failures are handled gracefully without terminating the process.
    
    This test simulates a network-level exception (e.g., a connection timeout) 
    to ensure the client returns an empty list rather than allowing the 
    exception to propagate and crash the pipeline.
    """
    # Simulate a network-level exception
    mock_get.side_effect = Exception("Connection Timeout")
    
    result = fetch_market_data()
    
    assert isinstance(result, list)
    assert len(result) == 0, "Failed extraction should return an empty list to maintain stability"

# 2. Test DefiLlama Extractor

@patch('src.extract.defillama_client.requests.get')
def test_fetch_tvl_data_success(mock_get):
    """Tests that the DefiLlama client correctly formats protocol data.
    
    This test verifies that the client can handle the specific list-based 
    JSON structure returned by the DefiLlama API and successfully 
    appends the required metadata.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    # DefiLlama returns a direct list of protocols rather than a nested dictionary
    mock_response.json.return_value = [{'slug': 'aave', 'name': 'Aave', 'tvl': 5000000}]
    mock_get.return_value = mock_response

    result = fetch_tvl_data()

    assert len(result) == 1
    assert result[0]['slug'] == 'aave'
    assert 'timestamp' in result[0], "Timestamp injection missing for DefiLlama records"