"""Base CEX Connector Implementation"""
from typing import Dict, Optional, Any

class BaseCEXConnector:
    """Base class for centralized exchange connectors"""
    
    def __init__(self, exchange_name: str, api_key: str, api_secret: str):
        """
        Initialize a CEX connector
        
        Args:
            exchange_name (str): Name of the exchange
            api_key (str): API key for authentication
            api_secret (str): API secret for authentication
        """
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        
    def get_name(self) -> str:
        """
        Get the name of the exchange
        
        Returns:
            str: Exchange name
        """
        return self.exchange_name
        
    async def get_balances(self) -> Dict[str, float]:
        """
        Get account balances
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement get_balances method")
        
    async def place_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float
    ) -> Optional[str]:
        """
        Place an order
        
        Args:
            symbol (str): Trading pair symbol
            side (str): Order side (buy/sell)
            price (float): Order price
            quantity (float): Order quantity
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement place_order method")
        
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id (str): Unique identifier for the order to cancel
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement cancel_order method")
    
    async def fetch_order_book(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch the order book for a given symbol
        
        Args:
            symbol (str): Trading pair symbol
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement fetch_order_book method")