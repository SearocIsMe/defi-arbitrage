from abc import ABC, abstractmethod
from typing import Dict, List
import asyncio
import websockets
import json

class BaseCLOBConnector(ABC):
    """Base class for CLOB exchange connectors"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_url = None
        self.websocket = None
        
    @abstractmethod
    async def connect(self):
        """Establish WebSocket connection"""
        pass
        
    @abstractmethod
    async def subscribe_order_book(self, symbol: str):
        """Subscribe to order book updates for a symbol"""
        pass
        
    @abstractmethod
    async def get_order_book(self, symbol: str) -> Dict:
        """Get current order book snapshot"""
        pass
        
    @abstractmethod
    async def place_order(self, order: Dict):
        """Place a new order"""
        pass
        
    @abstractmethod
    async def cancel_order(self, order_id: str):
        """Cancel an existing order"""
        pass
        
    @abstractmethod
    async def get_balances(self) -> Dict[str, float]:
        """Get account balances"""
        pass
        
    async def _send_ws_message(self, message: Dict):
        """Send WebSocket message"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            
    async def _receive_ws_message(self):
        """Receive WebSocket message"""
        if self.websocket:
            return await self.websocket.recv()
        return None
        
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()