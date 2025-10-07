# price_monitor.py
import asyncio
import websockets
import json
from decimal import Decimal
from typing import Dict, Callable
from datetime import datetime
import logging
import os

from utils.token_usd_price import determine_usd_price
from models.position_models import PriceUpdate, Position, PositionStatus
from trader.position_manager import PositionManager

# TODO: Replace with the global logger class
logger = logging.getLogger(__name__)

class PriceMonitor:
    def __init__(self, positions_manager):
        """
        Monitor cryptocurrency prices and manage trading positions.

        Args:
            positions_manager (PositionManager): An instance of the PositionManager class to manage positions based on price updates and the user's preferred ROI and loss threshold.
        """
        self.positions_manager:PositionManager = positions_manager
        self.active_subscriptions: list[dict] = [{"ammKey": "CbfFQCuzkmrnZwBi1gCVm3qwdN9igcSm2BzNXBUyuaDs", "token_mint": "2RfXjaiepngcBuGgPLtdnH22g68eetpgzCDX44Hnpump"}]  # Example token subscription
        self.price_callbacks = {}
        self.ws_connections = {}
        
    async def start_monitoring(self):
        """Start price monitoring service"""
        # At start of service, set the positions that will be monitored
        # NOTE: Since I plan to cache the price for a token and then allow other users access it from the cache so I need to apply a more robust logic here to ensure each token mint is unique. Maybe convert to a tuple and then back to list or something
        # TODO: Consider the note above when the product is serving more than one user
        self.active_subscriptions = [{"token_mint": p.token_mint, "ammKey": p.ammKey} for p in self.positions_manager.positions.values()]

        # Set the tasks that will run continously 
        tasks = [
            self.connect_solana_stream(),
            # TODO: To use BirdEye, I'll need to set up an account and get API keys. Paying a shit ton that I can't afford yet
        ]
        await asyncio.gather(*tasks)

    async def stop_monitoring(self):
        """
        Stop price monitoring service
        """
        pass 
    
    async def connect_solana_stream(self):
        """Connect to Solana price stream"""
        api_key = os.getenv("SOLANA_STREAMING_API_KEY", "solana_streaming_default_key")
        # For debugging purposes
        print(f"Using Solana Streaming API Key: {api_key}")
        uri = 'wss://api.solanastreaming.com/'
        headers = {
            "X-API-KEY": api_key
        }

        while True:
            try:
                async with websockets.connect(
                        uri, 
                        additional_headers=headers, 
                        ping_interval=10, 
                        ping_timeout=5, 
                        close_timeout=5
                    ) as websocket:
                        self.ws_connections['solana_streaming'] = websocket

                        # Subscribe to tokens using their pair address from Dexscreener
                        for index, token in enumerate(self.active_subscriptions):
                            pair_address = token.get('ammKey')
                            # For debugging purposes
                            logger.info(f"Subscribing to Solana stream for pair address: {pair_address}")
                            await websocket.send(json.dumps({
                                    "id": index + 1,
                                    "method": "swapSubscribe",
                                    "params": {
                                        "include": {
                                            "ammAccount": [
                                                pair_address #This will be the pair address so that we get updates from the largest liquidity pool for the token and only that to avoid false price updates
                                            ]
                                        }
                                    }
                                }))
                        
                        # Listen for updates
                        async for message in websocket:
                            try:
                                # Debugging purposes
                                logger.info(f"Received Solana stream message: {message}")
                                data = json.loads(message)
                                asyncio.create_task(self.handle_price_update('solana_streaming', data))
                            except json.JSONDecodeError as e:
                                logger.exception(f"An error occured when parsing the data")
                            except Exception as e:
                                logger.exception(f"Error occured when parsing message from websocket")
            except websockets.exceptions.ConnectionClosedError as e:
                # If the connection closes, retry the connection after 5 seconds
                logger.exception(f"Connection closed. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                # If any other error occurs, retry the connection after 5 seconds
                logger.exception("Error occured when accessing the Websocket for Solana Streaming...")
                await asyncio.sleep(5)
    
    async def handle_price_update(self, source: str, data: Dict):
        """Process incoming price update"""

        # The first response from the Solana Streaming API is usually a notification that the subscription was successful so skip
        if not data.get("params"):
            print(f"No price data sent in this message")
            return 
        
        # Send the price data once it comes through
        price_data = data.get("params")
        swap_data = price_data.get("swap")

        try:
            sol_price = Decimal(swap_data.get('quotePrice'))
            usd_price = await determine_usd_price(sol_price)

            price_update = PriceUpdate(
                token_mint=swap_data.get("baseTokenMint"),
                price_sol= sol_price,
                price_usd= usd_price,
                timestamp=datetime.now(),
                source=source,
                volume_24h=data.get('volume24h', 0),
                liquidity_usd=data.get('liquidity', 0)
            )
            
            # Check exit conditions
            # This is where trades will be closed if there's an SL or TP set by the user
            await self.check_exit_conditions(price_update)
            
            # Execute callbacks
            if price_update.token_mint in self.price_callbacks:
                for callback in self.price_callbacks[price_update.token_mint]:
                    await callback(price_update)
                    
        except Exception as e:
            logger.exception(f"Error handling price update")
    
    async def check_exit_conditions(self, price_update: PriceUpdate):
        """Check if any positions should be closed"""

        logger.info("Checking the exit conditions...")
        positions: list[Position] = self.positions_manager.get_active_positions(
            token_mint=price_update.token_mint
        )

        if not positions.__len__ > 0:
            logger.warning(f"There is no open position for {price_update.token_mint} to check for exit conditions")
            await self.stop_monitoring()
        
        for position in positions:
            # Calculate current ROI
            entry_price = position.entry_price
            current_price = price_update.price_usd
            roi = ((current_price - entry_price) / entry_price) * 100
            
            # Check take profit
            if roi >= position.target_roi:
                await self.execute_take_profit(position, current_price, roi)
            
            # Check stop loss
            elif roi <= position.stop_loss:
                await self.execute_stop_loss(position, current_price, roi)

            #TODO: Implement trailing stop in V2
    
    async def execute_take_profit(self, position:Position, current_price:Decimal, roi:Decimal):
        """Execute take profit order"""
        
        try:
            # Execute sell order
            result = await self.positions_manager.close_position(
                token_mint=position.token_mint,
                reason=f"Take profit @ {current_price}",
                quantity= position.token_amount, #Sell everything at TP
            )
            
            if result['status'] == "success":
                logger.info(f"Take profit triggered for {position.token_mint}: ROI {roi:.2f}%")
                await self.notify_exit(position, "TAKE PROFIT", roi, result['tx_hash'])
        except Exception as e:
            logger.exception("Error occured when closing trade for Take Profit")
    
    async def execute_stop_loss(self, position:Position, current_price:Decimal, roi:Decimal):
        """Execute stop loss order"""
        
        try:
            # Execute sell order immediately
            result = await self.positions_manager.close_position(
                token_mint=position.token_mint,
                reason=f"Stop loss @ {current_price}",
                quantity= position.token_amount, #Sell everything at SL
            )
            
            if result['status'] == "success":
                logger.info(f"Stop loss triggered for {position.token_mint}: ROI {roi:.2f}%")
                await self.notify_exit(position, "STOP LOSS", roi, result['tx_hash'])
        except Exception as e:
            logger.exception("Error occured when closing trade for Stop Loss")

    async def notify_exit(self, position: Position, action:str, roi:Decimal, tx_hash:str):
        """
        Notify the user that a position has been closed on his/her behalf

        Args:
            position (Position): The position that was closed
            action (str): Why the position was closed
            roi (float): The ROI gotten from the trade
            tx_hash (str): _description_
        """
        # TODO: This would be used for notifying the user like a websocket
        logger.info(f"The position for {position.token_mint} has been closed because of {action} and the ROI is {roi}. Here's the tx_id = {tx_hash}")


if __name__ == "__main__":
    import asyncio

    async def main():
        from trader.position_manager import PositionManager
        print("Initializing Position Manager and Price Monitor...")
        position_manager = PositionManager()
        mock_position = Position(
            token_mint= "2RfXjaiepngcBuGgPLtdnH22g68eetpgzCDX44Hnpump",
            token_amount= 200000000,
            entry_price= Decimal("0.0002786"),
            entry_amount_sol= Decimal("0.002"),
            target_roi = 50.0,
            status= PositionStatus.OPEN,
            stop_loss=25.0,
            created_at=datetime.now(),
        )
        position_manager.positions["2RfXjaiepngcBuGgPLtdnH22g68eetpgzCDX44Hnpump"] = mock_position
        price_monitor = PriceMonitor(position_manager)

        print("Connecting to Solana Stream...")
        await price_monitor.connect_solana_stream()

    print("Starting Price Monitor...")
    asyncio.run(main())