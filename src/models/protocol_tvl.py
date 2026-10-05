from pydantic import BaseModel, Field, field_validator
from typing import Optional

class DefiLlamaProtocol(BaseModel):
    """Pydantic data contract for DefiLlama protocol payloads.
    
    This model enforces schema validation, type casting, and standardisation 
    for raw Total Value Locked (TVL) data extracted from the DefiLlama API.
    """
    defillama_id: str = Field(alias='slug')
    name: str
    symbol: Optional[str] = None # Many protocols do not have an associated governance token
    category: Optional[str] = "Unknown"
    tvl_usd: Optional[float] = Field(alias='tvl', default=0.0)
    timestamp: float # Unix timestamp injected by the producer

    @field_validator('symbol', mode='before')
    @classmethod
    def clean_symbol(cls, value):
        """Enforces uppercase symbols, allowing None if the protocol lacks a native token.

        Args:
            value (Any): The raw symbol string.

        Returns:
            Optional[str]: The capitalised symbol, or None if missing or invalid.
        """
        if not value or value == '-':
            return None
        return str(value).upper()
        
    @field_validator('tvl_usd', mode='before')
    @classmethod
    def parse_tvl(cls, value):
        """Safely converts string numbers from the API into Python floats.

        Args:
            value (Any): The raw numerical TVL value from the API payload.

        Returns:
            float: The parsed float value, or 0.0 if parsing fails.
        """
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0