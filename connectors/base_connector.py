"""Base Connector Implementation"""
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
from web3 import Web3

class BaseConnector(ABC):
    """Abstract base class for all exchange connectors"""
    
    def __init__(
        self, 
        w3: Web3, 
        config: Dict[str, Any]
    ):
        """
        Initialize base connector
        
        Args:
            w3 (Web3): Web3 instance for blockchain interactions
            config (Dict[str, Any]): Configuration for the connector
        """
        self.w3 = w3
        self.config = config
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get a human-readable name for this connector
        
        Returns:
            str: Name of the connector
        """
        pass
    
    @abstractmethod
    async def fetch_market_data(self) -> Dict[str, Any]:
        """
        Fetch current market data
        
        Returns:
            Dict[str, Any]: Market data for supported assets
        """
        pass
    
    def _validate_address(self, address: str) -> bool:
        """
        Validate Ethereum address
        
        Args:
            address (str): Ethereum address to validate
        
        Returns:
            bool: Whether the address is valid
        """
        try:
            return self.w3.is_address(address)
        except Exception:
            return False

class AMMConnector(BaseConnector):
    """Abstract base class for Automated Market Maker connectors"""
    
    @abstractmethod
    async def get_pool_reserves(
        self, 
        token_a: str, 
        token_b: str
    ) -> Dict[str, float]:
        """
        Get pool reserves for a specific token pair
        
        Args:
            token_a (str): Address of first token
            token_b (str): Address of second token
        
        Returns:
            Dict[str, float]: Reserves for the token pair
        """
        pass
    
    @abstractmethod
    async def swap_tokens(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        min_amount_out: float,
        sender_address: str
    ) -> Dict[str, Any]:
        """
        Execute a token swap
        
        Args:
            token_in (str): Address of input token
            token_out (str): Address of output token
            amount_in (float): Amount of input token to swap
            min_amount_out (float): Minimum acceptable output amount
            sender_address (str): Address executing the swap
        
        Returns:
            Dict[str, Any]: Swap transaction details
        """
        pass
    
    @abstractmethod
    async def add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: float,
        amount_b: float,
        sender_address: str
    ) -> Dict[str, Any]:
        """
        Add liquidity to a token pair pool
        
        Args:
            token_a (str): Address of first token
            token_b (str): Address of second token
            amount_a (float): Amount of first token to add
            amount_b (float): Amount of second token to add
            sender_address (str): Address providing liquidity
        
        Returns:
            Dict[str, Any]: Liquidity addition transaction details
        """
        pass