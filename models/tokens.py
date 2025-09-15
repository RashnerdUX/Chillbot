from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TokenAlert(BaseModel):
    """
    TokenAlert model for representing a token alert pulled from a telegram channel.
    """
    contract_address: str = Field(..., pattern=r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
    token_name: Optional[str] = None
    token_symbol: Optional[str] = None
    source_chat: str
    message_text: str
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)

class TokenMetadata(BaseModel):
    """
    TokenMetadata model for representing metadata information of a token.

    Args:
        BaseModel (_type_): _description_
    """
    mint: str
    name: str
    symbol: str
    decimals: int
    supply: int
    freeze_authority: Optional[str] = None
    mint_authority: Optional[str] = None

class LiquidityInfo(BaseModel):
    """
    LiquidityInfo model for representing liquidity information of a token.

    Args:
        BaseModel (_type_): _description_
    """
    pool_address: str
    dex: str
    liquidity_usd: float
    volume_24h: float
    price_usd: float
    mcap: float