from typing import Dict, List

class BaseCLOBConnector:
    """Base class for Central Limit Order Book (CLOB) connectors"""
    
    def place_order(self, *args, **kwargs):
        """Placeholder method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement place_order method")
    
    def cancel_order(self, *args, **kwargs):
        """Placeholder method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement cancel_order method")
    
    def get_order_book(self, *args, **kwargs):
        """Placeholder method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_order_book method")
    
    def get_balances(self, *args, **kwargs):
        """Placeholder method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_balances method")