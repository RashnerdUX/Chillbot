# price_monitor.py
import asyncio
import websockets
import json
from decimal import Decimal
from typing import Dict, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

logging = logging.getLogger(__name__)

@dataclass
class PriceUpdate:
    token_mint: str
    price_usd: Decimal
    timestamp: datetime
    source: str
    volume_24h: float
    liquidity_usd: float

class PriceMonitor:
    def __init__(self, positions_manager):
        self.positions_manager = positions_manager
        self.active_subscriptions = {}
        self.price_callbacks = {}
        self.ws_connections = {}
        
    async def start_monitoring(self):
        """Start price monitoring service"""
        tasks = [
            self.connect_jupiter_stream(),
            self.connect_birdeye_stream(),
            self.poll_backup_prices()
        ]
        await asyncio.gather(*tasks)
    
    async def connect_jupiter_stream(self):
        """Connect to Jupiter price stream"""
        uri = "wss://price.jup.ag/v1/stream"
        
        async with websockets.connect(uri) as websocket:
            self.ws_connections['jupiter'] = websocket
            
            # Subscribe to tokens
            for token in self.active_subscriptions.keys():
                await websocket.send(json.dumps({
                    "op": "subscribe",
                    "channel": "price",
                    "markets": [token]
                }))
            
            # Listen for updates
            async for message in websocket:
                await self.handle_price_update('jupiter', json.loads(message))
    
    async def handle_price_update(self, source: str, data: Dict):
        """Process incoming price update"""
        try:
            price_update = PriceUpdate(
                token_mint=data.get('mint'),
                price_usd=Decimal(str(data.get('price', 0))),
                timestamp=datetime.utcnow(),
                source=source,
                volume_24h=data.get('volume24h', 0),
                liquidity_usd=data.get('liquidity', 0)
            )
            
            # Update position tracking
            await self.positions_manager.update_price(price_update)
            
            # Check exit conditions
            await self.check_exit_conditions(price_update)
            
            # Execute callbacks
            if price_update.token_mint in self.price_callbacks:
                for callback in self.price_callbacks[price_update.token_mint]:
                    await callback(price_update)
                    
        except Exception as e:
            logging.error(f"Error handling price update: {e}")
    
    async def check_exit_conditions(self, price_update: PriceUpdate):
        """Check if any positions should be closed"""
        positions = await self.positions_manager.get_active_positions(
            token_mint=price_update.token_mint
        )
        
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
            
            # Check trailing stop
            elif position.trailing_stop_enabled:
                await self.check_trailing_stop(position, current_price, roi)
    
    async def execute_take_profit(self, position, current_price, roi):
        """Execute take profit order"""
        logging.info(f"Take profit triggered for {position.token_mint}: ROI {roi:.2f}%")
        
        # Execute sell order
        result = await self.positions_manager.close_position(
            position_id=position.id,
            reason="take_profit",
            exit_price=current_price,
            roi=roi
        )
        
        if result['success']:
            await self.notify_exit(position, "TAKE PROFIT", roi, result['tx_hash'])
    
    async def execute_stop_loss(self, position, current_price, roi):
        """Execute stop loss order"""
        logging.warning(f"Stop loss triggered for {position.token_mint}: ROI {roi:.2f}%")
        
        # Execute sell order immediately
        result = await self.positions_manager.close_position(
            position_id=position.id,
            reason="stop_loss",
            exit_price=current_price,
            roi=roi,
            priority_fee=50000  # Higher priority for stop loss
        )
        
        if result['success']:
            await self.notify_exit(position, "STOP LOSS", roi, result['tx_hash'])


if __name__ == "__main__":
    import asyncio

    async def main():
        from trader.position_manager import PositionManager
        position_manager = PositionManager()
        price_monitor = PriceMonitor(position_manager)
        await price_monitor.start_monitoring()

    asyncio.run(main())