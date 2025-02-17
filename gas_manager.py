import asyncio
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from web3 import Web3
from web3.middleware import geth_poa_middleware

from logger_config import get_logger
from error_handler import ErrorHandler, ArbitrageError, ErrorSeverity
from config_manager import config

class GasStrategy:
    """
    Represents a gas pricing strategy
    """
    def __init__(
        self, 
        base_fee: Decimal, 
        priority_fee: Decimal,
        max_fee: Optional[Decimal] = None
    ):
        """
        Initialize gas strategy
        
        Args:
            base_fee (Decimal): Base blockchain gas fee
            priority_fee (Decimal): Miner tip/priority fee
            max_fee (Decimal, optional): Maximum acceptable gas fee
        """
        self.base_fee = base_fee
        self.priority_fee = priority_fee
        self.max_fee = max_fee or base_fee * Decimal('2')
    
    def calculate_gas_price(self) -> Dict[str, Decimal]:
        """
        Calculate optimal gas pricing
        
        Returns:
            Dict[str, Decimal]: Gas pricing parameters
        """
        max_priority_fee = min(
            self.priority_fee * Decimal('1.2'),  # 20% buffer
            self.max_fee - self.base_fee
        )
        
        return {
            'base_fee': self.base_fee,
            'priority_fee': max_priority_fee,
            'max_fee_per_gas': self.max_fee
        }

class GasManager:
    """
    Manages gas pricing and optimization across different blockchains
    """
    def __init__(self, w3: Web3):
        """
        Initialize GasManager
        
        Args:
            w3 (Web3): Web3 instance for blockchain interactions
        """
        # Add POA middleware for networks like BSC
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.w3 = w3
        self.logger = get_logger('gas_manager')
        
        # Configuration
        self.max_gas_price = Decimal(
            config.get('gas.max_price_gwei', '500')
        )
        self.gas_price_multiplier = Decimal(
            config.get('gas.price_multiplier', '1.2')
        )
    
    @ErrorHandler.critical_error_handler
    async def get_gas_price(self, chain: str = 'ethereum') -> GasStrategy:
        """
        Fetch current gas price for a specific blockchain
        
        Args:
            chain (str, optional): Blockchain name. Defaults to 'ethereum'.
        
        Returns:
            GasStrategy: Calculated gas pricing strategy
        """
        try:
            # Fetch gas price based on blockchain
            if chain == 'ethereum':
                base_fee = await self._get_ethereum_base_fee()
                priority_fee = await self._get_ethereum_priority_fee()
            elif chain == 'binance_smart_chain':
                base_fee = await self._get_bsc_base_fee()
                priority_fee = await self._get_bsc_priority_fee()
            else:
                raise ValueError(f"Unsupported chain: {chain}")
            
            # Create and return gas strategy
            return GasStrategy(
                base_fee=base_fee,
                priority_fee=priority_fee,
                max_fee=self.max_gas_price
            )
        
        except Exception as e:
            self.logger.error(f"Gas price retrieval error for {chain}: {e}")
            raise ArbitrageError(
                f"Failed to retrieve gas price for {chain}",
                severity=ErrorSeverity.HIGH
            )
    
    async def _get_ethereum_base_fee(self) -> Decimal:
        """
        Get Ethereum base fee (EIP-1559)
        
        Returns:
            Decimal: Base fee in Gwei
        """
        latest_block = self.w3.eth.get_block('latest')
        base_fee_per_gas = latest_block.get('baseFeePerGas', 0)
        return Decimal(str(self.w3.from_wei(base_fee_per_gas, 'gwei')))
    
    async def _get_ethereum_priority_fee(self) -> Decimal:
        """
        Get Ethereum priority fee (miner tip)
        
        Returns:
            Decimal: Priority fee in Gwei
        """
        # Use Web3 max priority fee method
        try:
            max_priority_fee = self.w3.eth.max_priority_fee
            return Decimal(str(self.w3.from_wei(max_priority_fee, 'gwei')))
        except Exception:
            # Fallback to static priority fee
            return Decimal('2')
    
    async def _get_bsc_base_fee(self) -> Decimal:
        """
        Get Binance Smart Chain base fee
        
        Returns:
            Decimal: Base fee in Gwei
        """
        gas_price = self.w3.eth.gas_price
        return Decimal(str(self.w3.from_wei(gas_price, 'gwei')))
    
    async def _get_bsc_priority_fee(self) -> Decimal:
        """
        Get Binance Smart Chain priority fee
        
        Returns:
            Decimal: Priority fee in Gwei
        """
        return Decimal('1')
    
    def estimate_transaction_cost(
        self, 
        gas_limit: int, 
        gas_strategy: GasStrategy
    ) -> Decimal:
        """
        Estimate total transaction cost
        
        Args:
            gas_limit (int): Estimated gas limit for transaction
            gas_strategy (GasStrategy): Gas pricing strategy
        
        Returns:
            Decimal: Estimated transaction cost in native token
        """
        total_gas_price = (
            gas_strategy.base_fee + 
            gas_strategy.priority_fee
        )
        
        return Decimal(gas_limit) * total_gas_price / Decimal('1e9')
    
    async def monitor_gas_prices(self, interval: int = 60):
        """
        Continuously monitor and log gas prices
        
        Args:
            interval (int): Monitoring interval in seconds
        """
        while True:
            try:
                # Check gas prices for multiple chains
                chains = ['ethereum', 'binance_smart_chain']
                gas_prices = {}
                
                for chain in chains:
                    gas_strategy = await self.get_gas_price(chain)
                    gas_prices[chain] = gas_strategy.calculate_gas_price()
                
                # Log gas prices
                self.logger.info(f"Current Gas Prices: {gas_prices}")
                
                await asyncio.sleep(interval)
            
            except Exception as e:
                self.logger.error(f"Gas price monitoring error: {e}")
                await asyncio.sleep(interval)
