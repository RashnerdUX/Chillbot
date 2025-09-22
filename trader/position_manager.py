from datetime import datetime
from decimal import Decimal
import logging

from trader.with_jupiter import JupiterTrader
from wallet.wallet_manager import WalletManager
from models.position_models import Position, PositionStatus

logging = logging.getLogger(__name__)
class PositionManager:
    def __init__(self):
        self.wallet = WalletManager()
        self.trader = JupiterTrader()
        self.active_positions: dict[str, Position] = {}

    async def open_position(self, token_mint: str, amount_sol: float):
        """
        Add a new position after buying a token.

        Args:
            token_mint (str): The mint address of the token to buy.
            amount_sol (float): The amount of SOL to invest.
        
        Returns:
            dict: Result of the operation with status and details.
        """
        # Some set variables that need to be set by user input or config
        target_roi = 5.0
        stop_loss = -2.0
        try:
            # Get the price before buying
            # TODO: Handle checking current price later
            # current_price = await self.trader.get_token_price(token_mint)
            current_price = 0.0  # Placeholder until we implement price fetching    

            # Calculate position size based on risk management
            position_size = await self.calculate_position_size(Decimal(amount_sol))

            # Execute swap via JupiterTrader
            buy_result = await self.trader.buy_token(token_mint, position_size)
            if buy_result.get("status") != "Success":
                logging.error(f"Failed to buy token {token_mint}: {buy_result.get('message')}")
                return {"status": "Failed", "message": buy_result.get("message")}

            # Record the position
            # TODO: Once we are using a database, store positions in memory only for active tracking and with their DB ids
            # If position exists, update it; otherwise, create a new one
            if token_mint in self.active_positions:
                self.active_positions[token_mint].entry_amount_sol += position_size
                self.active_positions[token_mint].token_amount = Decimal(str(buy_result.get("received")))
            else:
                self.active_positions[token_mint] = Position(
                    token_mint=token_mint,
                    entry_price=Decimal(str(buy_result.get("received"))) / position_size,
                    entry_amount_sol=position_size,
                    token_amount=Decimal(str(buy_result.get("received"))),
                    target_roi=target_roi,
                    stop_loss=stop_loss,
                    status=PositionStatus.OPEN,
                    created_at=datetime.now(),
                    entry_tx=buy_result.get("message"),
                    trailing_stop_enabled=True,
                    highest_price=Decimal(str(buy_result.get("received"))) / position_size
                )
            return{
                    'status': "Success",
                    'position_id': token_mint,
                    'entry_price': current_price,
                    'tokens_received': buy_result['received'],
                    # TODO: Consider sending the transaction hash later
                    # 'tx_hash': buy_result['tx_hash']
                }
        except Exception as e:
            logging.error(f"Error adding position for {token_mint}: {e}")
            return {"status": "Failed", "message": str(e)}

    async def close_position(self, token_mint: str, quantity: Decimal):
        """
        Remove or reduce a position after selling a token
        
        Args:
            token_mint (str): The mint address of the token to sell.
            quantity (Decimal): The amount of the token to sell.
        
        Returns:
            dict: Result of the operation with status and details.
        """

        try:
            # Retrieve the token
            # For now, we are using token_mint as the position ID
            open_position = self.active_positions[token_mint]
            open_position.status = PositionStatus.CLOSING

            # Reduce or sell all the holdings for the given token
            sell_result = await self.trader.sell_token(token_mint, quantity)

            # Check status of the sell
            if sell_result.get("status") != "Success":
                logging.error(f"Failed to sell token {token_mint}: {sell_result.get('message')}")
                return {"status": "Failed", "message": sell_result.get("message")}

            # Update the position once sell is successful
            open_position.token_amount -= quantity
            # If all tokens sold, close the position and record exit details
            if open_position.token_amount <= 0:
                del self.active_positions[token_mint]

        except KeyError:
            logging.error(f"No active position found for token {token_mint}")
            return {"status": "Failed", "message": "No active position found"}
        except Exception as e:
            logging.error(f"Error retrieving position for {token_mint}: {e}")
            return {"status": "Failed", "message": str(e)}

    def get_position(self, token_mint: str):
        return self.active_positions.get(token_mint, None)

    def get_all_positions(self):
        return self.active_positions

    async def calculate_position_size(self, requested_amount: Decimal) -> Decimal:
        """Calculate position size based on risk management rules"""
        # TODO: Do a more robust risk management strategy. E.g the user could set a specific sol amount or % of portfolio they want to risk per trade.
        # Get account balance
        result = await self.wallet.get_balance()
        total_balance = Decimal(str(result.get("total_balance", 0.0)))
        
        # Maximum 5% of portfolio per trade
        max_position = total_balance * Decimal('0.05')
        
        # Maximum 2 SOL per trade for safety
        max_sol = Decimal('2.0')
        
        return min(requested_amount, max_position, max_sol)
    

if __name__ == "__main__":
    import asyncio

    async def main():
        position_manager = PositionManager()
        token_mint = "7icvUrzYkTtBJCeNxgAPxb3RCAWkFzNW9vwyFhckpump"  # For JUP
        amount_sol = 0.001  # Amount in SOL to invest

        # Open a position
        open_result = await position_manager.open_position(token_mint, amount_sol)
        print(f"Open Position Result: {open_result}")
        if open_result.get("status") != "Success":
            return
        
        # Once successful, get the total quantity bought from the active positions in memory 
        total_quantity = position_manager.get_position(token_mint).token_amount

        await asyncio.sleep(10)  # Wait for some time before closing the position

        # Close 50% of the position
        print(f"Total Quantity: {total_quantity}")
        print(f"Closing 50% of position for {token_mint}")
        partial_quantity = float(total_quantity) * 0.5
        close_result = await position_manager.close_position(token_mint, partial_quantity)
        print(f"Close Position Result: {close_result}")

        # Close the remaining position after another wait
        await asyncio.sleep(10)
        print(f"Closing remaining position for {token_mint}")
        final_close_result = await position_manager.close_position(token_mint, total_quantity - partial_quantity)
        print(f"Final Close Position Result: {final_close_result}")

    asyncio.run(main())