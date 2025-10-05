from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from enum import Enum
from datetime import datetime

class PositionStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"

class Position(BaseModel):
    token_mint: str
    entry_price: Decimal
    entry_amount_sol: Decimal
    token_amount: Decimal
    target_roi: float = Field(..., description="Target ROI percentage for taking profit")
    stop_loss: float = Field(..., description="Stop loss percentage")
    ammKey: str = Field(..., description="This is the most active liquidity pool that will be used to monitor the pair")
    status: PositionStatus
    created_at: datetime
    entry_tx: Optional[str] = None
    exit_tx: Optional[str] = None
    exit_price: Optional[Decimal] = None
    exit_roi: Optional[float] = None
    trailing_stop_enabled: bool = False
    highest_price: Optional[Decimal] = None

class PriceUpdate(BaseModel):
    token_mint: str
    price_sol: Decimal
    price_usd: Optional[Decimal] = None
    timestamp: datetime
    source: str
    volume_24h: Optional[Decimal] = None
    liquidity_usd: Optional[Decimal] = None

