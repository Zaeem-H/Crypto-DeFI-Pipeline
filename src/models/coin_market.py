from pydantic import BaseModel, Field, field_validator
from typing import Optional

class CoinCapAsset(BaseModel):
    """Pydantic data contract for CoinCap API payloads.
    
    This model enforces schema validation, type casting, and standardisation 
    for raw market data extracted from the CoinCap API.
    """
    api_id: str = Field(alias='id')
    symbol: str
    name: str
    price_usd: Optional[float] = Field(alias='priceUsd', default=0.0)
    volume_24h_usd: Optional[float] = Field(alias='volumeUsd24Hr', default=0.0)
    market_cap_usd: Optional[float] = Field(alias='marketCapUsd', default=0.0)
    timestamp: float # Unix timestamp injected by the producer

    @field_validator('price_usd', 'volume_24h_usd', 'market_cap_usd', mode='before')
    @classmethod
    def parse_floats(cls, value):
        """Safely converts string numbers from the API into Python floats.

        Args:
            value (Any): The raw numerical value from the API payload.

        Returns:
            float: The parsed float value, or 0.0 if parsing fails.
        """
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
            
    @field_validator('symbol', mode='before')
    @classmethod
    def uppercase_symbol(cls, value):
        """Ensures symbols are always uppercase for clean relational joins later.

        Args:
            value (Any): The raw symbol string.

        Returns:
            str: The capitalised symbol, or "UNKNOWN" if missing.
        """
        return str(value).upper() if value else "UNKNOWN"