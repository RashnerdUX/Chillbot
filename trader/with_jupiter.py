from wallet.wallet_manager import WalletManager
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

class JupiterTrader:
    def __init__(self):
        self.wallet = WalletManager()
        self.jupiter_api_key = os.getenv("JUPITER_API_KEY")
        self.lite_base_url = "https://lite-api.jup.ag/ultra/v1/order"
        self.ultra_base_url = "https://api.jup.ag/ultra/v1/"
        self.sol_mint = "So11111111111111111111111111111111111111112"

    async def get_order_quote(self, input_mint: str, amount: int, output_mint: str):
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": self.jupiter_api_key,
            }
            params = {
                "inputMint": input_mint, #Base58 encoded mint address of the token I am using to swap
                "outputMint": output_mint, #Base58 encoded mint address of the token I want to receive
                "amount": amount, #Amount of input token to swap, in lamports (1 SOL = 10^9 lamports)
                "taker": self.wallet.wallet_address, #Base58 encoded public key of the wallet performing the swap
                # TODO: Explore referral options later to monetize the bot
                #"referralAccount": os.getenv("DEV_WALLET_ADDRESS"), #Base58 encoded public key of the referral account
                #"referralBps": 25, #Basis points (bps) for the referral fee (1 bps = 0.01%)
            }
            async with session.get(f"{self.ultra_base_url}/order", headers=headers, params=params) as response:
                data = await response.json()
                if data.get("error"):
                    return {"error": data.get("error")}
                return {"request_id": data.get("requestId"), "transaction": data.get("transaction")}
            
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
                    return {"status": "Success", "message": message, "received": data.get("outputAmountResult"), "spent": data.get("inputAmountResult")}
                else:
                    message = "Swap failed"
                    return {"status": "Failed", "message": message, "error": data.get("error")}
                
if __name__ == "__main__":
    import asyncio

    async def main():
        trader = JupiterTrader()
        
        kindness_mint = "V5cCiSixPLAiEDX2zZquT5VuLm4prr5t35PWmjNpump"
        quote = await trader.get_order_quote(trader.sol_mint, 1000000, kindness_mint) # 0.001 SOL to Kindness
        print(quote)
        signed_tx = await trader.wallet.sign_transaction(quote["transaction"])
        print(signed_tx)

        # Execute the swap
        result = await trader.execute_swap(signed_tx, quote["request_id"])
        print(result)

    asyncio.run(main())