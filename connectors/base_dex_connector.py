"""Base DEX Connector Implementation"""
from typing import Dict, Optional, Any, List
from abc import ABC, abstractmethod
from web3 import Web3
import logging

class BaseDEXConnector(ABC):
    """Abstract base class for decentralized exchange connectors"""
    
    def __init__(
        self, 
        w3: Web3, 
        chain_config: Dict[str, Any]
    ):
        """
        Initialize DEX Connector
        
        Args:
            w3 (Web3): Web3 instance for blockchain interactions
            chain_config (Dict[str, Any]): Configuration for the specific DEX and chain
        """
        self.w3 = w3
        self.chain_name = chain_config.get('chain', 'unknown')
        self.router_address = chain_config.get('router_address')
        self.factory_address = chain_config.get('factory_address')
        
        # Validate critical configuration
        if not self.router_address or not self.factory_address:
            raise ValueError(f"Invalid DEX configuration for {self.chain_name}")
        
        # Setup logging
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Contract instances (to be set by subclasses)
        self.router_contract = None
        self.factory_contract = None
    
    @abstractmethod
    async def fetch_market_data(self) -> Dict[str, float]:
        """
        Fetch current market data for supported token pairs
        
        Returns:
            Dict[str, float]: Market data with token pairs and their prices
        """
        pass
    
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
    
    def get_name(self) -> str:
        """
        Get a human-readable name for this DEX connector
        
        Returns:
            str: Name of the DEX connector
        """
        return f"{self.chain_name}_dex"
    
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
    
    def _get_token_decimals(self, token_address: str) -> int:
        """
        Get token decimals
        
        Args:
            token_address (str): Token contract address
        
        Returns:
            int: Number of decimals for the token
        """
        try:
            # Minimal ERC20 ABI for decimals function
            abi = [{
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }]
            
            token_contract = self.w3.eth.contract(address=token_address, abi=abi)
            return token_contract.functions.decimals().call()
        except Exception as e:
            self.logger.warning(f"Could not fetch decimals for {token_address}: {e}")
            return 18  # Default to 18 decimals