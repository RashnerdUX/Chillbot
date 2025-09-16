# token_validator.py
import json
import os
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from anchorpy import Provider, Program, Idl
from typing import Optional, Dict
import base58
import struct
from models.tokens import TokenMetadata, LiquidityInfo, RouteInfo
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
        self.sol_mint = "So11111111111111111111111111111111111111112"
        self.jupiter_api = "https://lite-api.jup.ag/price/v3"
        self.jupiter_quote_api = "https://quote-api.jup.ag/v6/quote"
        self.rugcheck_api = "https://api.rugcheck.xyz/v1"
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
                
                # TODO: Add functionality to LiquidityInfo model to check minimum liquidity
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
        """Check liquidity across DEXs using Jupiter as primary source."""
        input_amount_sol = 0.1  # Amount of SOL to simulate swap
        slippage_threshold = 0.5  # 0.5% acceptable slippage
        amount_lamports = int(input_amount_sol * 1_000_000_000)  # 1 SOL = 1e9 lamports

        params = {
            "inputMint": self.sol_mint,
            "outputMint": mint_address,
            "amount": amount_lamports,
            "slippageBps": int(slippage_threshold * 100),  # bps = % * 100
        }

        try:
            JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
            response = requests.get(JUPITER_QUOTE_API, params=params)

            if response.status_code == 200:
                data = response.json()
                print(f"Jupiter quote response for {mint_address}: {response.text}")

                # Build route info for LiquidityInfo model
                dex_routes = []
                for route in data.get("routePlan", []):
                    swap_info = route.get("swapInfo", {})
                    dex_routes.append(
                        RouteInfo(
                            amm=swap_info.get("label", "Unknown"),
                            pool_address=swap_info.get("ammKey", "Unknown"),
                            in_amount=float(swap_info.get("inAmount", 0)) / 1e9,  # convert lamports to SOL
                            out_amount=float(swap_info.get("outAmount", 0)),
                            fee_amount=float(swap_info.get("feeAmount", 0)) / 1e9,
                            fee_mint=swap_info.get("feeMint", "Unknown"),
                        )
                    )

                liquidity_info = LiquidityInfo(
                    tradable=data.get("priceImpact", 0) < slippage_threshold,
                    price_impact_pct=data.get("priceImpact", 0),
                    expected_out=data.get("outAmount", 0),
                    min_out=data.get("otherAmountThreshold", 0),
                    usd_value_in=data.get("swapUsdValue", 0),
                    input_amount_sol=input_amount_sol,
                    dex_routes=dex_routes,
                    reason=None if data.get("priceImpact", 0) < slippage_threshold else "High slippage / low liquidity",
                )
                return liquidity_info

            # Fallback (Raydium or other check)
            # return await self.check_raydium_pools(mint_address)
            return None

        except Exception as e:
            logging.error(f"Error checking liquidity: {e}")
            return None
    
    async def check_honeypot(self, mint_address: str) -> Dict:
        """Check for honeypot characteristics"""
        
        try:
            #1. use Rugcheck API to check for any risks
            rugcheck = self.get_rugcheck_report_summary(mint_address)
            if rugcheck.get("risk") != "low":
                # 2. If the rugcheck score isn't low then we simulate swaps to confirm
                simulation = await self.simulate_swap(mint_address, 0.1)
                # If either buy or sell fails, it's a honeypot
                if not (simulation.get("buy_success") and simulation.get("sell_success")):
                    return {"is_honeypot": True, "reason": "Swap simulation failed"}
            
            """  
            TODO: Additional checks can be implemented here as later on          
            # 3. Check for excessive taxes
            
            # 4. Check holder distribution
            
            # 5. Check for blacklist function
            """
            return {"is_honeypot": False, "reason": "No honeypot characteristics detected"}     
        except Exception as e:
            logging.error(f"Honeypot check error: {e}")
            return {"is_honeypot": True, "reason": "Failed to verify trading safety"}

    def simulate_swap(self, mint_address: str, amount_sol: float) -> Dict:
        """Simulate a buy/sell swap to check for taxes and trading ability"""
        params = {
            "inputMint": self.sol_mint,
            "outputMint": mint_address,
            "amount": int(amount_sol * 1_000_000_000),  # in lamports
            "slippageBps": 50,  # 0.5%
        }

        try:
            # Simulate buy
            buy_response = requests.get(self.jupiter_quote_api, params=params)
            logging.info(f"Buy swap simulation response for {mint_address}: {buy_response.text}")
            if buy_response.status_code != 200:
                return {"buy_success": False, "sell_success": False}

            buy_data = buy_response.json()
            # Set the output amount for the sell simulation
            if not buy_data.get("outAmount"):
                return {"buy_success": False, "sell_success": False}
            sell_out_amount = buy_data["outAmount"]
            
            # Simulate sell (reverse swap)
            sell_params = {
                "inputMint": mint_address,
                "outputMint": self.sol_mint,
                "amount": sell_out_amount,
                "slippageBps": 50,
            }

            sell_response = requests.get(self.jupiter_quote_api, params=sell_params)
            logging.info(f"Sell swap simulation response for {mint_address}: {sell_response.text}")
            # Ensure that sell works out
            if sell_response.status_code != 200:
                return {"buy_success": True, "sell_success": False}
            
            # If both succeed, return success
            return {"buy_success": True,"sell_success": True}
        except Exception as e:
            logging.error(f"Swap simulation error: {e}")
            return {"buy_success": False, "sell_success": False}
    
    def get_rugcheck_report_summary(self, mint_address:str) -> Dict:
        """Fetch token risk report summary from Rugcheck"""
        try:
            url = f"{self.rugcheck_api}/tokens/{mint_address}/report/summary"
            token_report_summary = requests.get(url=url)
            if token_report_summary.status_code == 200:
                data = token_report_summary.json()

                if data.get("score_normalised") > 70:
                    return {"risk": "high", "reason": "High risk score from Rugcheck", "report": data}
                
                if len(data.get("risks")) > 0:
                    if any(risk.get("severity") == "high" for risk in data.get("risks", [])):
                        return {"risk": "high", "reason": "High severity risks from Rugcheck", "report": data}

                    if any(risk.get("severity") == "medium" for risk in data.get("risks", [])):
                        return {"risk": "medium", "reason": "Medium severity risks from Rugcheck", "report": data}

                    if any(risk.get("severity") == "low" for risk in data.get("risks", [])):
                        return {"risk": "low", "reason": "Low severity risks from Rugcheck", "report": data}

                return {"risk": "low", "reason": "Low risk score from Rugcheck", "report": data}
        except Exception as e:
            logging.error(f"Was unable to retrieve token report summary for {mint_address}, this is the error: {e}")
            return {"error": str(e)}

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
        """ 
        TODO: Implement minimum liquidity check when LiquidityInfo model supports it
        elif validation_results.get("liquidity"):
        liq = validation_results["liquidity"].liquidity_usd
        if liq < 10000:
            score += weights["liquidity_amount"] * (1 - liq/10000)
        """
        # For now, liquidity amount check is skipped and the full score is awarded
        score += 0.0

        # Honeypot check
        if checks.get("honeypot", {}).get("is_honeypot", False):
            score += weights["honeypot"]
            
        return min(score, 1.0)
    
    def get_metadata(self, mint_address: str) -> Dict:
        """Fetch token metadata using Moralis API"""
        try:
            MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
            url = f"https://solana-gateway.moralis.io/token/mainnet/{mint_address}/metadata"

            headers = {
            "Accept": "application/json",
            "X-API-Key": MORALIS_API_KEY
            }

            response = requests.request("GET", url, headers=headers)
            metadata = response.json()
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
    result = asyncio.run(validator.validate_token(test_contract))
    print("Result:")
    print(result)