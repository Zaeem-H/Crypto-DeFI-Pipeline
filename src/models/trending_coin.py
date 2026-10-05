from pydantic import BaseModel, Field, field_validator
from typing import List

class TrendingItem(BaseModel):
    """Pydantic data contract for the deeply nested item inside the CoinGecko payload.
    
    This model represents the core attributes of a globally trending cryptocurrency,
    enforcing schema validation and type casting for subsequent data warehouse ingestion.
    """
    api_id: str = Field(alias='id') # Often matches the primary identifier used by CoinCap
    symbol: str
    name: str
    score: int # The rank on the trending list (0 represents the highest rank)

    @field_validator('symbol', mode='before')
    @classmethod
    def uppercase_symbol(cls, value):
        """Enforces uppercase symbols to ensure successful relational joins in the Fact table.

        Args:
            value (Any): The raw symbol string extracted from the API.

        Returns:
            str: The capitalised symbol, or "UNKNOWN" if missing or invalid.
        """
        return str(value).upper() if value else "UNKNOWN"

class TrendingCoin(BaseModel):
    """Wrapper dictionary mapping for the trending item to match the API hierarchy."""
    item: TrendingItem

class CoinGeckoTrending(BaseModel):
    """Top-level Pydantic data contract for the CoinGecko Trending API response.
    
    This model validates the entire JSON payload, ensuring the list of trending 
    coins and the injected timestamp adhere to the expected schema.
    """
    coins: List[TrendingCoin]
    timestamp: float # Unix timestamp injected by the data producer