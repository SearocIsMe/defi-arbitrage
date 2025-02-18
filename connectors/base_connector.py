from web3 import Web3

class BaseConnector:
    """Base class for blockchain connectors"""
    
    def __init__(self, web3_provider: str = None):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider)) if web3_provider else None
    
    def connect(self, *args, **kwargs):
        """Placeholder method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement connect method")
    
    def disconnect(self, *args, **kwargs):
        """Placeholder method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement disconnect method")