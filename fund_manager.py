import os
import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union

from web3 import Web3
from web3.contract import Contract

from logger_config import get_logger
from error_handler import ErrorHandler, ArbitrageError, ErrorSeverity
from config_manager import config

class Position:
    """
    Represents a trading position with detailed tracking
    """
    def __init__(
        self, 
        token: str, 
        amount: Decimal, 
        exchange: str, 
        entry_price: Decimal
    ):
        """
        Initialize a trading position
        
        Args:
            token (str): Token symbol
            amount (Decimal): Position size
            exchange (str): Exchange where position is held
            entry_price (Decimal): Price at position entry
        """
        self.token = token
        self.amount = amount
        self.exchange = exchange
        self.entry_price = entry_price
        self.entry_timestamp = asyncio.get_event_loop().time()
        
        # Risk management attributes
        self.stop_loss = None
        self.take_profit = None
    
    def calculate_pnl(self, current_price: Decimal) -> Decimal:
        """
        Calculate Profit and Loss
        
        Args:
            current_price (Decimal): Current market price
        
        Returns:
            Decimal: Profit or loss percentage
        """
        return ((current_price - self.entry_price) / self.entry_price) * 100

class FundManager:
    """
    Manages funds, positions, and risk across multiple exchanges
    """
    def __init__(
        self, 
        w3: Web3, 
        gas_manager: Any,
        initial_capital: Decimal = Decimal('10000')
    ):
        """
        Initialize FundManager
        
        Args:
            w3 (Web3): Web3 instance for blockchain interactions
            gas_manager (Any): Gas management instance
            initial_capital (Decimal): Starting capital in USD
        """
        self.logger = get_logger('fund_manager')
        self.w3 = w3
        self.gas_manager = gas_manager
        
        # Capital and risk management
        self.total_capital = initial_capital
        self.available_capital = initial_capital
        self.max_risk_per_trade = Decimal(
            config.get('risk_management.max_risk_per_trade', '0.02')
        )
        
        # Position tracking
        self.active_positions: Dict[str, Position] = {}
        self.position_history: List[Position] = []
    
    @ErrorHandler.critical_error_handler
    async def allocate_funds(
        self, 
        token_pair: str, 
        exchange: str, 
        trade_amount: Optional[Decimal] = None
    ) -> Decimal:
        """
        Allocate funds for a specific trade
        
        Args:
            token_pair (str): Trading pair
            exchange (str): Exchange for trade
            trade_amount (Decimal, optional): Specific trade amount
        
        Returns:
            Decimal: Allocated trade amount
        """
        # Calculate trade size based on risk management
        if trade_amount is None:
            trade_amount = self._calculate_optimal_trade_size(token_pair)
        
        # Validate available capital
        if trade_amount > self.available_capital:
            raise ArbitrageError(
                f"Insufficient funds for trade: {token_pair} on {exchange}",
                severity=ErrorSeverity.HIGH
            )
        
        # Update capital
        self.available_capital -= trade_amount
        
        return trade_amount
    
    def _calculate_optimal_trade_size(self, token_pair: str) -> Decimal:
        """
        Calculate optimal trade size based on risk management
        
        Args:
            token_pair (str): Trading pair
        
        Returns:
            Decimal: Optimal trade amount
        """
        max_risk_amount = self.total_capital * self.max_risk_per_trade
        
        # Additional risk calculation based on token volatility
        volatility_factor = self._get_token_volatility(token_pair)
        
        return max_risk_amount * volatility_factor
    
    def _get_token_volatility(self, token_pair: str) -> Decimal:
        """
        Estimate token volatility
        
        Args:
            token_pair (str): Trading pair
        
        Returns:
            Decimal: Volatility factor
        """
        # Placeholder for more sophisticated volatility calculation
        # Could integrate with external volatility APIs or historical data
        return Decimal('1.0')
    
    @ErrorHandler.critical_error_handler
    async def open_position(
        self, 
        token: str, 
        amount: Decimal, 
        exchange: str, 
        entry_price: Decimal
    ) -> Position:
        """
        Open a new trading position
        
        Args:
            token (str): Token symbol
            amount (Decimal): Position size
            exchange (str): Exchange
            entry_price (Decimal): Entry price
        
        Returns:
            Position: Created trading position
        """
        position = Position(token, amount, exchange, entry_price)
        
        # Store position
        self.active_positions[f"{token}_{exchange}"] = position
        self.position_history.append(position)
        
        self.logger.info(
            f"Opened position: {token} on {exchange}, "
            f"Amount: {amount}, Entry Price: {entry_price}"
        )
        
        return position
    
    @ErrorHandler.critical_error_handler
    async def close_position(
        self, 
        position: Position, 
        exit_price: Decimal
    ) -> Dict[str, Any]:
        """
        Close an existing trading position
        
        Args:
            position (Position): Position to close
            exit_price (Decimal): Price at position closure
        
        Returns:
            Dict: Position closure details
        """
        # Calculate PnL
        pnl_percentage = position.calculate_pnl(exit_price)
        pnl_amount = position.amount * (exit_price / position.entry_price - 1)
        
        # Update available capital
        self.available_capital += position.amount * exit_price
        
        # Remove from active positions
        del self.active_positions[f"{position.token}_{position.exchange}"]
        
        closure_details = {
            'token': position.token,
            'exchange': position.exchange,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'pnl_percentage': pnl_percentage,
            'pnl_amount': pnl_amount
        }
        
        self.logger.info(f"Closed position: {closure_details}")
        
        return closure_details

# Utility function for decimal conversion
def to_decimal(value: Union[int, float, str, Decimal]) -> Decimal:
    """
    Safely convert various types to Decimal
    
    Args:
        value (Union[int, float, str, Decimal]): Value to convert
    
    Returns:
        Decimal: Converted value
    """
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        raise ValueError(f"Cannot convert {value} to Decimal")
