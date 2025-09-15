# token_validator.py
import json
import os
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from anchorpy import Provider, Program, Idl
from typing import Optional, Dict
import base58
import struct
from models.tokens import TokenMetadata, LiquidityInfo
from pathlib import Path
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logging = logging.getLogger(__name__)
# Get this from user's preference or config
RISK_THRESHOLD = 0.7  # Example threshold for risk score

class TokenValidator:
    def __init__(self, rpc_url: str):
        self.client = Client(rpc_url)
        self.jupiter_api = "https://price.jup.ag/v4"
        """self.metaplex_program_id = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
        # TODO: Provider is currently in read-only mode; for transactions, a wallet is needed.
        self.provider = Provider.readonly(self.client)
        # Load the IDL
        json_path = Path(__file__).parent / "metaplex_token_metadata.json"
        with open(json_path) as f:
            raw_idl = json.load(f)
            print(f"Raw IDL: {raw_idl}")

        idl = Idl.from_json(raw_idl)
        # For debugging
        print(f"Loaded IDL: {idl}")
        if 'instructions' in idl:
            print(f"Loaded IDL Instructions: {idl.get('instructions', 'Unknown')}")
        self.program = Program(idl=idl, program_id=self.metaplex_program_id, provider=self.provider)"""

    async def validate_token(self, contract_address: str) -> Dict:
        """Complete validation pipeline for a token"""
        results = {
            "is_valid": False,
            "metadata": None,
            "liquidity": None,
            "risk_score": 0,
            "warnings": [],
            "checks": {}
        }
        
        try:
            # 1. Verify it's a valid SPL token
            token_info = await self.get_token_info(contract_address)
            if not token_info:
                results["warnings"].append("Not a valid SPL token")
                return results
            
            results["metadata"] = token_info
            results["checks"]["is_spl_token"] = True
            
            # 2. Check for mint/freeze authorities
            if token_info.mint_authority:
                results["warnings"].append("Mint authority not renounced")
                results["checks"]["mint_renounced"] = False
            else:
                results["checks"]["mint_renounced"] = True
                
            if token_info.freeze_authority:
                results["warnings"].append("Freeze authority active")
                results["checks"]["freeze_renounced"] = False
            else:
                results["checks"]["freeze_renounced"] = True
            
            # 3. Check liquidity pools
            liquidity = await self.check_liquidity(contract_address)
            if liquidity:
                results["liquidity"] = liquidity
                results["checks"]["has_liquidity"] = True
                
                # Check minimum liquidity
                if liquidity.liquidity_usd < 10000:
                    results["warnings"].append(f"Low liquidity: ${liquidity.liquidity_usd:.2f}")
            else:
                results["warnings"].append("No liquidity found")
                results["checks"]["has_liquidity"] = False
            
            # 4. Check for honeypot characteristics
            honeypot_check = await self.check_honeypot(contract_address)
            results["checks"]["honeypot"] = honeypot_check
            if honeypot_check["is_honeypot"]:
                results["warnings"].append(f"Honeypot detected: {honeypot_check['reason']}")
            
            # 5. Calculate risk score
            results["risk_score"] = self.calculate_risk_score(results)
            
            # Determine if valid for trading
            results["is_valid"] = (
                results["checks"].get("is_spl_token", False) and
                results["checks"].get("has_liquidity", False) and
                not results["checks"].get("honeypot", {}).get("is_honeypot", True) and
                results["risk_score"] < 0.7
            )
            
        except Exception as e:
            results["warnings"].append(f"Validation error: {str(e)}")
            
        return results
    
    async def get_token_info(self, mint_address: str) -> Optional[TokenMetadata]:
        """Get SPL token metadata"""
        try:
            mint_pubkey = Pubkey.from_string(mint_address)
            account_info = self.client.get_account_info(mint_pubkey)
            
            if not account_info.value:
                return None
            
            # Parse mint data
            data = account_info.value.data
            
            # SPL Token mint structure
            mint_authority_option = struct.unpack('<I', data[0:4])[0]
            mint_authority = None if mint_authority_option == 0 else base58.b58encode(data[4:36]).decode()
            
            supply = struct.unpack('<Q', data[36:44])[0]
            decimals = data[44]
            
            is_initialized = data[45]
            if not is_initialized:
                return None
            
            freeze_authority_option = struct.unpack('<I', data[46:50])[0]
            freeze_authority = None if freeze_authority_option == 0 else base58.b58encode(data[50:82]).decode()

            # Get metadata from Moralis
            metadata = self.get_metadata(mint_address)
            
            return TokenMetadata(
                mint=mint_address,
                name=metadata.get('name', 'Unknown'),
                symbol=metadata.get('symbol', 'Unknown'),
                decimals=decimals,
                supply=supply,
                freeze_authority=freeze_authority,
                mint_authority=mint_authority
            )
            
        except Exception as e:
            logging.error(f"Error getting token info: {e}")
            return None
    
    async def check_liquidity(self, mint_address: str) -> Optional[LiquidityInfo]:
        """Check liquidity across DEXs"""
        try:
            # Check Jupiter for price and liquidity
            response = await self.fetch_jupiter_price(mint_address)
            
            if response:
                return LiquidityInfo(
                    pool_address=response.get('pool_address', ''),
                    dex=response.get('dex', 'Unknown'),
                    liquidity_usd=response.get('liquidity_usd', 0),
                    volume_24h=response.get('volume_24h', 0),
                    price_usd=response.get('price', 0),
                    mcap=response.get('market_cap', 0)
                )
            
            # Fallback to Raydium check
            # TODO: Implement Raydium liquidity check if Jupiter fails
            # return await self.check_raydium_pools(mint_address)
            
        except Exception as e:
            logging.error(f"Error checking liquidity: {e}")
            return None
        
    async def fetch_jupiter_price(self, mint_address: str) -> Optional[Dict]:
        """Fetch price and liquidity info from Jupiter API"""
        try:
            url = f"{self.jupiter_api}/tokens/{mint_address}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and len(data['data']) > 0:
                    token_data = data['data'][0]
                    return {
                        "pool_address": token_data.get("poolAddress", ""),
                        "dex": "Jupiter",
                        "liquidity_usd": token_data.get("liquidityUSD", 0),
                        "volume_24h": token_data.get("volume24hUSD", 0),
                        "price": token_data.get("priceUSD", 0),
                        "market_cap": token_data.get("marketCapUSD", 0)
                    }
            return None
        except Exception as e:
            logging.error(f"Jupiter API error: {e}")
            return None
    
    async def check_honeypot(self, mint_address: str) -> Dict:
        """Check for honeypot characteristics"""
        result = {
            "is_honeypot": False,
            "reason": None,
            "checks": {}
        }
        
        try:
            # 1. Check if trading is actually possible
            simulation = await self.simulate_swap(mint_address, 0.1)
            result["checks"]["can_buy"] = simulation.get("buy_success", False)
            result["checks"]["can_sell"] = simulation.get("sell_success", False)
            
            if not simulation.get("sell_success", False):
                result["is_honeypot"] = True
                result["reason"] = "Cannot sell tokens"
                return result
            
            # 2. Check for excessive taxes
            buy_tax = simulation.get("buy_tax", 0)
            sell_tax = simulation.get("sell_tax", 0)
            
            result["checks"]["buy_tax"] = buy_tax
            result["checks"]["sell_tax"] = sell_tax
            
            if buy_tax > 10 or sell_tax > 10:
                result["is_honeypot"] = True
                result["reason"] = f"Excessive taxes: Buy {buy_tax}%, Sell {sell_tax}%"
                return result
            
            # 3. Check holder distribution
            holders = await self.get_holder_distribution(mint_address)
            if holders:
                top_holder_percentage = holders[0]["percentage"] if holders else 0
                result["checks"]["top_holder"] = top_holder_percentage
                
                if top_holder_percentage > 50:
                    result["is_honeypot"] = True
                    result["reason"] = f"Centralized: Top holder owns {top_holder_percentage}%"
                    return result
            
            # 4. Check for blacklist function
            has_blacklist = await self.check_blacklist_function(mint_address)
            result["checks"]["has_blacklist"] = has_blacklist
            
            if has_blacklist:
                result["is_honeypot"] = True
                result["reason"] = "Contract has blacklist functionality"
                
        except Exception as e:
            logging.error(f"Honeypot check error: {e}")
            result["is_honeypot"] = True
            result["reason"] = "Failed to verify trading safety"
            
        return result
    
    def calculate_risk_score(self, validation_results: Dict) -> float:
        """Calculate overall risk score (0-1, higher is riskier)"""
        score = 0.0
        weights = {
            "mint_renounced": 0.2,
            "freeze_renounced": 0.15,
            "has_liquidity": 0.25,
            "liquidity_amount": 0.2,
            "honeypot": 0.2
        }
        
        checks = validation_results.get("checks", {})
        
        # Mint authority check
        if not checks.get("mint_renounced", False):
            score += weights["mint_renounced"]
            
        # Freeze authority check
        if not checks.get("freeze_renounced", False):
            score += weights["freeze_renounced"]
            
        # Liquidity check
        if not checks.get("has_liquidity", False):
            score += weights["has_liquidity"]
        elif validation_results.get("liquidity"):
            liq = validation_results["liquidity"].liquidity_usd
            if liq < 10000:
                score += weights["liquidity_amount"] * (1 - liq/10000)
        
        # Honeypot check
        if checks.get("honeypot", {}).get("is_honeypot", False):
            score += weights["honeypot"]
            
        return min(score, 1.0)
    
    def get_metadata(self, mint_address: str) -> Dict:
        """Fetch token metadata using Moralis API"""
        try:
            MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
            url = "https://solana-gateway.moralis.io/token/mainnet/V5cCiSixPLAiEDX2zZquT5VuLm4prr5t35PWmjNpump/metadata"

            headers = {
            "Accept": "application/json",
            "X-API-Key": MORALIS_API_KEY
            }

            response = requests.request("GET", url, headers=headers)
            metadata = response.json()
            print(f"Fetched metadata for {mint_address}: {response.text}")
            return metadata
        except Exception as e:
            logging.error(f"Metadata fetch error: {e}")
            return {"name": "Unknown", "symbol": "UNK"}
        
    async def get_metaplex_metadata(self, mint_address: str) -> Dict:
        """Fetch metadata from Metaplex"""
        try:
            # Calculate PDA for metadata
            mint_pubkey = Pubkey.from_string(mint_address)
            metadata_seeds = [
                b"metadata",
                bytes(self.metaplex_program_id),
                bytes(mint_pubkey)
            ]
            metadata_pda, _ = Pubkey.find_program_address(metadata_seeds, self.metaplex_program_id)

            # Fetch and parse with anchorpy
            metadata = await self.program.account["Metadata"].fetch(metadata_pda)

            #Logging
            logging.info(f"Retrieved metadata for {mint_address}: {metadata}")

            return metadata
        except Exception as e:
            logging.error(f"Metaplex metadata fetch error: {e}")
            return {"name": "Unknown", "symbol": "UNK"}

if __name__ == "__main__":
    import asyncio
    import logging

    logging.basicConfig(level=logging.INFO)
    print("Testing TokenValidator...")
    
    print("Initializing TokenValidator...")
    validator = TokenValidator("https://api.mainnet-beta.solana.com")
    
    print("Running validate_token...")
    test_contract = "V5cCiSixPLAiEDX2zZquT5VuLm4prr5t35PWmjNpump"
    print(f"Validating token: {test_contract}")
    result = asyncio.run(validator.get_token_info(test_contract))
    print("Token Info:")
    print(result)