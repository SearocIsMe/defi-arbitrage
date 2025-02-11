"""Base CEX Connector Implementation"""
from typing import Dict, Optional
from connectors.base_connector import CLOBConnector

class BaseCEXConnector(CLOBConnector):
    """Base class for centralized exchange connectors"""
    
    def __init__(self, exchange_name: str, api_key: str, api_secret: str):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        
    def get_name(self) -> str:
        return self.exchange_name
        
    def get_balances(self) -> Dict[str, float]:
        """Get account balances"""
        # Common implementation for CEX balance fetching
        pass
        
    def place_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float
    ) -> Optional[str]:
        """Place an order"""
        # Common order placement logic
        pass
        
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        # Common order cancellation logic
        pass