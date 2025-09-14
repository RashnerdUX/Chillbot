from pydantic import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    """
    User model for representing a user in the system.

    Args:
        BaseModel (pydantic.BaseModel): Base model class from Pydantic.
    """
    id: int
    username: str
    email: str
    is_active: bool = True
    is_admin: bool = False
    created_at: str
    updated_at: str

class TokenAlert(BaseModel):
    """
    TokenAlert model for representing a token alert pulled from a telegram channel.

    Args:
        BaseModel (pydantic.BaseModel): Base model class from Pydantic.
    """
    contract_address: str = Field(..., pattern=r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
    token_name: str | None = None
    token_symbol: str | None = None
    source_chat: str
    message_text: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime

