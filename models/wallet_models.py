from pydantic import BaseModel, Field
from typing import Optional

class UserWallet(BaseModel):
    wallet_name: str
    public_key: str
    encrypted_private_key: str
    salt: str
    iv: str
    tag: str

class WalletInfo(BaseModel):
    account_balance: float
    token_balances: dict[str, float]

class SolanaToken(BaseModel):
    """ A model representing a Solana token owned by the user."""
    # TODO: These optional fields should be made mandatory after testing
    token_address: str = Field(..., description="The token's mint address.")
    token_name: Optional[str] = Field(None, description="The token's name.")
    token_symbol: Optional[str] = Field(None, description="The token's symbol.")
    token_balance: float = Field(..., description="The token's balance.")
    token_decimals: int = Field(6, description="The token's decimals.")
    usd_value: Optional[float] = Field(None, description="The token's USD value.")