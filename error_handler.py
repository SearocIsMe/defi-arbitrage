import traceback
from typing import Optional, Any, Dict
import logging
import sentry_sdk
from enum import Enum, auto

class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

class ArbitrageError(Exception):
    """Base exception for arbitrage-related errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an ArbitrageError
        
        Args:
            message (str): Error description
            error_code (str, optional): Unique error identifier
            severity (ErrorSeverity): Error severity level
            context (dict, optional): Additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.severity = severity
        self.context = context or {}
        
        # Log the error
        self._log_error()
        
        # Report to error tracking service
        self._report_error()
    
    def _generate_error_code(self) -> str:
        """
        Generate a unique error code based on the error message
        
        Returns:
            str: Generated error code
        """
        import hashlib
        return hashlib.md5(self.message.encode()).hexdigest()[:8]
    
    def _log_error(self):
        """Log error using the logging system"""
        logger = logging.getLogger('arbitrage_error')
        
        log_method = {
            ErrorSeverity.LOW: logger.info,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.CRITICAL: logger.critical
        }.get(self.severity, logger.error)
        
        log_method(
            f"Error: {self.message} "
            f"(Code: {self.error_code}, "
            f"Severity: {self.severity.name})"
        )
    
    def _report_error(self):
        """
        Report error to error tracking service (Sentry)
        
        Captures additional context and stack trace
        """
        try:
            sentry_sdk.capture_exception(
                error=self,
                extra={
                    'error_code': self.error_code,
                    'severity': self.severity.name,
                    'context': self.context
                }
            )
        except Exception as e:
            logging.error(f"Failed to report error to Sentry: {e}")

class ExchangeConnectionError(ArbitrageError):
    """Error related to exchange connection issues"""
    def __init__(
        self, 
        exchange: str, 
        reason: str, 
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Connection error with {exchange}: {reason}",
            error_code=f"EXCHANGE_CONN_{exchange.upper()}",
            severity=ErrorSeverity.HIGH,
            context=context or {}
        )
        self.exchange = exchange

class ArbitrageProfitError(ArbitrageError):
    """Error related to arbitrage profit calculation"""
    def __init__(
        self, 
        token_pair: str, 
        source_market: str, 
        dest_market: str, 
        reason: str
    ):
        super().__init__(
            message=f"Arbitrage profit error for {token_pair} between {source_market} and {dest_market}: {reason}",
            error_code=f"ARBI_PROFIT_{token_pair.replace('/', '_')}",
            severity=ErrorSeverity.MEDIUM,
            context={
                'token_pair': token_pair,
                'source_market': source_market,
                'dest_market': dest_market
            }
        )

class ErrorHandler:
    """
    Centralized error handling and management
    """
    
    @staticmethod
    def handle_error(
        error: Exception, 
        context: Optional[Dict[str, Any]] = None
    ) -> ArbitrageError:
        """
        Handle and transform various exceptions
        
        Args:
            error (Exception): Original exception
            context (dict, optional): Additional context
        
        Returns:
            ArbitrageError: Standardized error
        """
        if isinstance(error, ArbitrageError):
            return error
        
        # Map standard exceptions to ArbitrageError
        if isinstance(error, ConnectionError):
            return ExchangeConnectionError(
                exchange="Unknown", 
                reason=str(error),
                context=context
            )
        
        # Generic error handling
        return ArbitrageError(
            message=str(error),
            severity=ErrorSeverity.HIGH,
            context={
                'original_error': type(error).__name__,
                'traceback': traceback.format_exc(),
                **(context or {})
            }
        )
    
    @staticmethod
    def critical_error_handler(func):
        """
        Decorator to handle critical errors in methods
        
        Wraps method to catch and handle exceptions,
        preventing application crash
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = ErrorHandler.handle_error(e)
                logging.critical(f"Critical error in {func.__name__}: {error}")
                # Optionally re-raise or take recovery action
                raise
        return wrapper

# Global error tracking setup
def setup_error_tracking(dsn: Optional[str] = None):
    """
    Initialize global error tracking
    
    Args:
        dsn (str, optional): Sentry DSN for error tracking
    """
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            # Add more Sentry configuration as needed
        )