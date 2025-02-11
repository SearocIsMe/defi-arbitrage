"""
Base Connector Interfaces
Defines standard interfaces for CLOB and AMM connectors
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from web3.types import TxReceipt
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address

class BaseConnectorError(Exception):
    """Base exception for connector errors"""
    pass

class PriceError(BaseConnectorError):
    """Exception for price-related errors"""
    pass

class TradeError(BaseConnectorError):
    """Exception for trade execution errors"""
    pass

class BaseConnector(ABC):
    """Base interface for all connectors"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get connector name"""
        pass
    
    @abstractmethod
    def get_chain(self) -> str:
        """Get chain name"""
        pass
    
    @abstractmethod
    def get_available_markets(self) -> Dict[str, Dict]:
        """Get available trading markets"""
        pass
    
    @abstractmethod
    def get_balances(self, wallet_address: ChecksumAddress) -> Dict[str, float]:
        """Get token balances for wallet"""
        pass

class CLOBConnector(BaseConnector):
    """Central Limit Order Book Connector Interface"""
    
    @abstractmethod
    def get_order_book(self, market: str) -> Dict:
        """Get order book for market"""
        pass
    
    @abstractmethod
    def place_limit_order(
        self,
        market: str,
        side: str,
        price: float,
        amount: float,
        wallet_address: ChecksumAddress
    ) -> str:
        """Place limit order"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        pass

class AMMConnector(BaseConnector):
    """Automated Market Maker Connector Interface"""
    
    @abstractmethod
    def get_price(
        self,
        base_token: str,
        quote_token: str,
        amount: float
    ) -> Tuple[float, float]:
        """Get price for swap"""
        pass
    
    @abstractmethod
    def swap_tokens(
        self,
        base_token: str,
        quote_token: str,
        amount: float,
        slippage: float,
        wallet_address: ChecksumAddress
    ) -> TxReceipt:
        """Execute token swap"""
        pass
    
    @abstractmethod
    def add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: float,
        amount_b: float,
        wallet_address: ChecksumAddress
    ) -> TxReceipt:
        """Add liquidity to pool"""
        pass
    
    @abstractmethod
    def remove_liquidity(
        self,
        token_a: str,
        token_b: str,
        liquidity: float,
        wallet_address: ChecksumAddress
    ) -> TxReceipt:
        """Remove liquidity from pool"""
        pass