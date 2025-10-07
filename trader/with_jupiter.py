from wallet.wallet_manager import WalletManager
import os
from dotenv import load_dotenv
import aiohttp
from decimal import Decimal
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class JupiterTrader:
    """
    Handles trading operations with the Jupiter API.
    """
    def __init__(self):
        self.wallet = WalletManager()
        self.jupiter_api_key = os.getenv("JUPITER_API_KEY")
        self.lite_base_url = "https://lite-api.jup.ag/ultra/v1/order"
        self.ultra_base_url = "https://api.jup.ag/ultra/v1/"
        self.sol_mint = "So11111111111111111111111111111111111111112"

    async def get_order_quote(self, input_mint: str, amount: int, output_mint: str):
        """
        Get a quote for a token swap from Jupiter API.

        Args:
            input_mint (str): The mint address of the token used to swap
            amount (int): The amount of input token to swap, in lamports for SOL and according to token decimals for SPL tokens
            output_mint (str): The mint address of the token to receive

        Returns:
            dict: A dictionary containing the quote details or an error message
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": self.jupiter_api_key,
            }
            params = {
                "inputMint": input_mint, #Base58 encoded mint address of the token I am using to swap
                "outputMint": output_mint, #Base58 encoded mint address of the token I want to receive
                "amount": amount, #Amount of input token to swap, in lamports (1 SOL = 10^9 lamports) for solana and according to token decimals for SPL tokens
                "taker": self.wallet.wallet_address, #Base58 encoded public key of the wallet performing the swap
                # TODO: Explore referral options later to monetize the bot
                #"referralAccount": os.getenv("DEV_WALLET_ADDRESS"), #Base58 encoded public key of the referral account
                #"referralBps": 25, #Basis points (bps) for the referral fee (1 bps = 0.01%)
            }
            async with session.get(f"{self.ultra_base_url}/order", headers=headers, params=params) as response:
                data = await response.json()
                if data.get("error"):
                    logger.error(f"Error get quote from Jupiter API. Here's the error: {data}")
                    return {"error": data.get("error")}
                
                logger.info(f"Successfully obtained the quote for {output_mint}")
                return {"request_id": data.get("requestId"), "transaction": data.get("transaction"), "ammKey": data["routePlan"][0]["ammKey"]}
            
    async def execute_swap(self, signedTransaction: str, request_id: str):
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": self.jupiter_api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "signedTransaction": signedTransaction,
                "requestId": request_id,
            }
            async with session.post(f"{self.ultra_base_url}/execute", headers=headers, json=payload) as response:
                data = await response.json()
                if data.get("status") == "Success":
                    message = "Swap executed successfully."
                    logger.info("Successfully swapped the token")
                    return {"status": "Success", "message": message, "received": data.get("outputAmountResult"), "spent": data.get("inputAmountResult")}
                else:
                    message = "Swap failed"
                    logger.error(f"Failed to swap a token. Here's the data: {data}")
                    return {"status": "Failed", "message": message, "error": data.get("error")}
                
    async def buy_token(self, token_mint: str, amount_sol: Decimal):
        """
        Buy a specified token using SOL
        Args:
            token_mint (str): The mint address of the token to buy.
            amount_sol (Decimal): The amount of SOL to spend. It'll be converted to lamports.
        Returns:
            dict: Result of the operation with status and details.
        """
        if amount_sol <= 0:
            return {"status": "Failed", "message": "Invalid amount: must be positive"}
        
        # SOL always has 9 decimals, so convert to lamports using Decimal for precision
        lamports = int(amount_sol * Decimal('1000000000'))  # Use Decimal to avoid float mixing
        
        quote = await self.get_order_quote(self.sol_mint, lamports, token_mint)
        if "error" in quote:
            logger.error(f"Error occured when getting a quote to buy the token {token_mint}")
            return {"status": "Failed", "message": quote["error"]}
        
        signed_tx = await self.wallet.sign_transaction(quote["transaction"])
        result = await self.execute_swap(signed_tx, quote["request_id"])
        logger.info(f"Successfully purchased {token_mint}")
        return {"data": result, "ammKey":quote.get("ammKey")}

    async def sell_token(self, token_mint: str, amount_token: Decimal):
        """
        Sell a specified token for SOL
        
        Args:
            token_mint (str): The mint address of the token to sell.
            amount_token (Decimal): The amount of the token to sell.

        Returns:
            dict: Result of the operation with status and details.
        """
        if amount_token <= 0:
            return {"status": "Failed", "message": "Invalid amount: must be positive"}
        
        # Convert the token amount to its raw integer representation
        raw_amount = int(amount_token)
        print(f"Raw amount to sell: {raw_amount}")
        
        quote = await self.get_order_quote(token_mint, raw_amount, self.sol_mint)
        if "error" in quote:
            logger.error(f"Error occured when getting a quote to sell the token {token_mint}")
            return {"status": "Failed", "message": quote["error"]}

        signed_tx = await self.wallet.sign_transaction(quote["transaction"])
        result = await self.execute_swap(signed_tx, quote["request_id"])
        logger.info(f"Successfully purchased {token_mint}")
        return {"data": result, "ammKey":quote.get("ammKey")}

if __name__ == "__main__":
    import asyncio

    async def main():
        trader = JupiterTrader()
        
        kindness_mint = "V5cCiSixPLAiEDX2zZquT5VuLm4prr5t35PWmjNpump"
        Bonk_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # For Bonk
        quote = await trader.get_order_quote(Bonk_mint, 3800000000, trader.sol_mint) # 0.001 SOL to Kindness
        print(quote)
        signed_tx = await trader.wallet.sign_transaction(quote["transaction"])
        print(signed_tx)

        # Execute the swap
        result = await trader.execute_swap(signed_tx, quote["request_id"])
        print(result)

    asyncio.run(main())