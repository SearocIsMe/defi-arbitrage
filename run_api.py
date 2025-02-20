import os
import sys
import asyncio
import argparse


# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_service import run_api_service
from arbitrage_detector import ArbitrageDetector
from config_manager import config
from logger_config import configure_logging
from error_handler import setup_error_tracking

def parse_arguments():
    """
    Parse command-line arguments
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="DeFi Arbitrage Bot")
    
    parser.add_argument(
        '--mode', 
        choices=['api', 'arbitrage', 'both'], 
        default='both',
        help='Run mode: API service, arbitrage detection, or both'
    )
    
    parser.add_argument(
        '--host', 
        default='0.0.0.0', 
        help='Host for API service'
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8000, 
        help='Port for API service'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level'
    )
    
    parser.add_argument(
        '--config', 
        help='Path to custom configuration file'
    )
    
    return parser.parse_args()

def setup_environment(args):
    """
    Set up application environment
    
    Args:
        args (argparse.Namespace): Parsed command-line arguments
    """
    # Configure logging
    configure_logging(log_level=args.log_level)
    
    # Setup error tracking
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn:
        setup_error_tracking(sentry_dsn)
    
    # Load custom configuration if provided
    if args.config:
        config.load_config(args.config)

async def run_arbitrage_bot():
    """
    Run the main arbitrage detection loop
    """
    wallet_address = config.get('wallet_address')
    if not wallet_address:
        raise ValueError("Wallet address not configured")
    
    detector = ArbitrageDetector(wallet_address)
    await detector.main_arbitrage_loop()

def main():
    """
    Main entry point for the application
    """
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Setup environment
        setup_environment(args)
        
        # Run based on selected mode
        if args.mode in ['arbitrage', 'both']:
            asyncio.run(run_arbitrage_bot())
        
        if args.mode in ['api', 'both']:
            run_api_service(host=args.host, port=args.port)
    
    except KeyboardInterrupt:
        print("\nApplication shutdown initiated.")
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
