from pydantic import BaseModel, Field
from typing import List, Optional
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

class RouteInfo(BaseModel):
    amm: str
    pool_address: str
    in_amount: float
    out_amount: float
    fee_amount: float
    fee_mint: str


class LiquidityInfo(BaseModel):
    """
    Liquidity information for a token trade, derived from Jupiter quote API.
    """
    tradable: bool                  # Whether the token passes liquidity checks
    price_impact_pct: float         # Price impact % of the test swap
    expected_out: float             # Expected token output from simulated trade
    min_out: float                  # Minimum tokens expected after slippage tolerance
    usd_value_in: float             # Approximate USD value of simulated input swap
    input_amount_sol: float         # SOL used for simulation
    dex_routes: List[RouteInfo]     # Route details (AMM, pool, fees, etc.)
    reason: Optional[str] = None    # If not tradable, explain why