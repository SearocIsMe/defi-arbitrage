import os
import logging
import structlog
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
import sys

def configure_logging(log_level=None):
    """
    Configure comprehensive logging with multiple handlers
    
    Args:
        log_level (str, optional): Logging level. Defaults to INFO.
    
    Returns:
        structlog logger instance
    """
    # Determine log level
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, log_level)

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Configure base logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console Handler
            logging.StreamHandler(sys.stdout),
            
            # File Handler with Rotation
            RotatingFileHandler(
                os.path.join(log_dir, 'arbitrage_bot.log'),
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            ),
            
            # Time-based Rotation Handler
            TimedRotatingFileHandler(
                os.path.join(log_dir, 'arbitrage_bot_daily.log'),
                when='midnight',
                interval=1,
                backupCount=30
            )
        ]
    )

    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level to each event
            structlog.stdlib.add_log_level,
            
            # Add caller information
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            
            # Render as JSON for easier parsing
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create a logger
    logger = structlog.get_logger('arbitrage_bot')

    # Add error tracking (optional, requires sentry-sdk)
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=numeric_level,        # Capture errors at this level
            event_level=logging.ERROR   # Send error events to Sentry
        )

        sentry_sdk.init(
            dsn=os.getenv('SENTRY_DSN', ''),
            integrations=[sentry_logging],
            traces_sample_rate=0.2  # Adjust as needed
        )
    except ImportError:
        logger.warning("Sentry SDK not installed. Error tracking disabled.")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")

    return logger

def get_logger(name='arbitrage_bot'):
    """
    Convenience method to get a logger
    
    Args:
        name (str, optional): Logger name. Defaults to 'arbitrage_bot'.
    
    Returns:
        structlog logger instance
    """
    return structlog.get_logger(name)
