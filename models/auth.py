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

class AuthToken(BaseModel):
    """
    AuthToken model for representing an authentication token.

    Args:
        BaseModel (pydantic.BaseModel): Base model class from Pydantic.
    """
    token: str = Field(..., min_length=20)
    user_id: int
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

class RefreshToken(BaseModel):
    """
    RefreshToken model for representing a refresh token.

    Args:
        BaseModel (pydantic.BaseModel): Base model class from Pydantic.
    """
    token: str = Field(..., min_length=20)
    user_id: int
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

class Settings(BaseModel):
    """
    Settings model for representing user-specific trading settings.

    Args:
        BaseModel (pydantic.BaseModel): Base model class from Pydantic.
    """
    user_id: int  # This is the foreign key
    risk_amount: float
    target_roi: float
    stop_loss: float

class TelegramChatID(BaseModel):
    """
    TelegramChatID model for representing a Telegram chat ID associated with a user.

    Args:
        BaseModel (pydantic.BaseModel): Base model class from Pydantic.
    """
    user_id: int  # This is the foreign key
    chat_name: str  # Name of the Telegram chat
    chat_id: int  # Telegram chat ID

