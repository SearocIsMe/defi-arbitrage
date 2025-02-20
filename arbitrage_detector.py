import os
import asyncio
from datetime import datetime

# Add dotenv for environment variable management
from dotenv import load_dotenv
load_dotenv()

# Import external libraries
from web3 import Web3

# Import local modules
from logger_config import get_logger
from api_service import store_arbitrage_opportunity, store_top_trading_pairs
from chain_config import CHAIN_CONFIG, validate_chain_config
from gas_manager import GasManager
from fund_manager import FundManager
from connectors.connector_factory import ConnectorFactory

# Import logging
logger = get_logger()

class ArbitrageDetector:
    def __init__(self, wallet_address):
        """
        Initialize ArbitrageDetector with wallet and multi-exchange connections
        
        Args:
            wallet_address (str): User's wallet address for transactions
        """
        # Validate environment and configuration
        self._validate_environment()
        
        self.wallet_address = wallet_address
        self.w3 = self._initialize_web3()
        self.gas_manager = GasManager(self.w3)
        self.fund_manager = FundManager(self.w3, self.gas_manager)
        
        # Initialize multi-exchange connector
        self.multi_exchange_connector = self._initialize_multi_exchange_connector()
        
        # Configuration parametersCould not establish Web3 connection to any provider
        self.min_arbitrage_profit = float(os.getenv('MIN_ARBITRAGE_PROFIT', 0.5))
        self.max_pairs_to_track = int(os.getenv('MAX_PAIRS_TO_TRACK', 50))
        
        # Arbitrage settings
        self.cross_chain_arbitrage_enabled = os.getenv('CROSS_CHAIN_ARBITRAGE_ENABLED', 'true').lower() == 'true'
        self.cross_dex_arbitrage_enabled = os.getenv('CROSS_DEX_ARBITRAGE_ENABLED', 'true').lower() == 'true'
    
    def _validate_environment(self):
        """
        Validate critical environment variables and configurations
        """
        # Validate chain configuration
        try:
            validate_chain_config(CHAIN_CONFIG)
        except ValueError as e:
            logger.error(f"Invalid chain configuration: {e}")
            raise
        
        # Check critical environment variables
        required_vars = [
            'WALLET_ADDRESS', 
            'WEB3_PROVIDER_URL',
            'MIN_ARBITRAGE_PROFIT',
            'ARBITRAGE_CHECK_INTERVAL'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing critical environment variables: {', '.join(missing_vars)}")
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")
    
    def _initialize_web3(self):
        """Initialize Web3 provider with fallback mechanism and chain configuration support"""
        # Use chain configuration to get RPC URLs
        web3_provider_url = os.getenv('WEB3_PROVIDER_URL')
        
        if not web3_provider_url:
            error_msg = "WEB3_PROVIDER_URL environment variable is not set. Cannot initialize Web3 connection."
            logger.error(error_msg)
            raise EnvironmentError(error_msg)
        
        provider_urls = [web3_provider_url]
        
        # Add fallback RPC URLs from chain configuration
        for chain_config in CHAIN_CONFIG.items():
            if 'rpc_url' in chain_config:
                provider_urls.append(chain_config['rpc_url'])
        
        for url in provider_urls:
            try:
                w3 = Web3(Web3.HTTPProvider(url))
                if w3.is_connected():
                    logger.info(f"Successfully connected to Web3 provider: {url}")
                    return w3
            except Exception as e:
                logger.warning(f"Failed to connect to Web3 provider {url}: {e}")
        
        raise ConnectionError("Could not establish Web3 connection to any provider")
    
    def _initialize_multi_exchange_connector(self):
        """
        Initialize multi-exchange connector
        
        Returns:
            MultiExchangeConnector: Initialized connector with multiple exchanges
        """
        try:
            # Use ConnectorFactory to create multi-exchange connector
            connector = ConnectorFactory.create_connector()
            logger.info("Initialized multi-exchange connector")
            return connector
        except Exception as e:
            logger.error(f"Failed to initialize multi-exchange connector: {e}")
            return None
    
    async def fetch_top_trading_pairs(self):
        """
        Dynamically fetch top trading pairs from multiple exchanges
        
        Returns:
            dict: Top trading pairs with their market data
        """
        if not self.multi_exchange_connector:
            logger.warning("Multi-exchange connector not initialized")
            return {}
        
        try:
            top_pairs = await self.multi_exchange_connector.fetch_top_trading_pairs(
                limit=self.max_pairs_to_track
            )
            
            # Store top trading pairs for monitoring
            store_top_trading_pairs(top_pairs)
            
            return top_pairs
        except Exception as e:
            logger.error(f"Error fetching top trading pairs: {e}")
            return {}
    
    async def detect_arbitrage_opportunities(self, market_data):
        """
        Detect potential arbitrage opportunities across multiple markets

        Logs detailed information about the arbitrage detection process
        
        Args:
            market_data (dict): Market data from different exchanges
        
        Returns:
            list: List of arbitrage opportunities
        """
        # Determine market types
        def get_market_type(market_name):
            cex_markets = ['okx', 'binance', 'coinbase']
            dex_markets = ['uniswap', 'pancakeswap', 'sushiswap']
            
            if market_name in cex_markets:
                return 'cex'
            elif market_name in dex_markets:
                return 'dex'
            else:
                return 'unknown'
        
        opportunities = []
        logger.debug(f"Starting arbitrage detection with {len(market_data)} markets")
        logger.debug(f"Markets: {list(market_data.keys())}")
        
        # Cross-market price comparison
        for source_market, source_pairs in market_data.items():
            for dest_market, dest_pairs in market_data.items():
                # Skip same market comparisons
                if source_market == dest_market:
                    continue
                
                # Determine market types
                source_market_type = get_market_type(source_market)
                dest_market_type = get_market_type(dest_market)
                
                # Skip cross-chain or cross-DEX arbitrage if disabled
                if not self.cross_chain_arbitrage_enabled and source_market_type != dest_market_type:
                    logger.debug(
                        f"Skipping arbitrage between {source_market} and {dest_market}: "
                        f"Cross-chain arbitrage is disabled. "
                        f"Source market type: {source_market_type}, Destination market type: {dest_market_type}"
                    )
                    continue
                
                if not self.cross_dex_arbitrage_enabled and source_market_type == 'dex' and dest_market_type == 'dex':
                    logger.debug(
                        f"Skipping arbitrage between {source_market} and {dest_market}: "
                        f"Cross-DEX arbitrage is disabled. "
                        f"Source market type: {source_market_type}, Destination market type: {dest_market_type}"
                    )
                    continue
                
                for token_pair, source_price_data in source_pairs.items():
                    if token_pair in dest_pairs:
                        dest_price_data = dest_pairs[token_pair]
                        
                        # Extract last price for comparison
                        source_price = source_price_data.get('last_price', 0)
                        dest_price = dest_price_data.get('last_price', 0)
                        
                        # Calculate potential profit percentage
                        if source_price > 0 and dest_price > 0:
                            profit_percentage = abs((source_price - dest_price) / source_price * 100)
                            
                            if profit_percentage > self.min_arbitrage_profit:
                                opportunity = {
                                    'source_market': source_market,
                                    'dest_market': dest_market,
                                    'token_pair': token_pair,
                                    'source_price': source_price,
                                    'dest_price': dest_price,
                                    'profit_percentage': profit_percentage,
                                    'timestamp': datetime.now().isoformat()
                                }
                
                                logger.info(f"Arbitrage Opportunity Detected: {opportunity}")
                                opportunities.append(opportunity)
                            else:
                                logger.debug(
                                    f"No arbitrage opportunity for {token_pair} between {source_market} and {dest_market}: "
                                    f"Profit {profit_percentage:.2f}% < {self.min_arbitrage_profit}%"
                                )
        
        logger.debug(f"Arbitrage detection complete. Found {len(opportunities)} opportunities")
        return opportunities
    
    async def main_arbitrage_loop(self):
        """Main arbitrage detection and execution loop"""
        check_interval = int(os.getenv('ARBITRAGE_CHECK_INTERVAL', 60))
        
        while True:
            try:
                # Fetch top trading pairs
                top_pairs = await self.fetch_top_trading_pairs()
                
                # Detect arbitrage opportunities
                opportunities = await self.detect_arbitrage_opportunities(top_pairs)
                
                # Process and potentially execute opportunities
                for opportunity in opportunities:
                    try:
                        if opportunity['profit_percentage'] > self.min_arbitrage_profit:
                            # Store arbitrage opportunity
                            store_arbitrage_opportunity(opportunity)
                            
                            # Optional: Add logic for trade execution
                            # This would involve checking fund availability, 
                            # calculating optimal trade size, and executing cross-market trade
                    except Exception as e:
                        logger.error(f"Error processing arbitrage opportunity: {e}")
                
                # Wait before next iteration
                await asyncio.sleep(check_interval)
            
            except Exception as e:
                logger.error(f"Error in arbitrage detection loop: {e}")
                await asyncio.sleep(30)

def main():
    try:
        # Get wallet address from environment
        wallet_address = os.getenv('WALLET_ADDRESS')
        if not wallet_address:
            raise EnvironmentError("WALLET_ADDRESS environment variable not set")
        
        # Initialize and run arbitrage detector
        detector = ArbitrageDetector(wallet_address)
        asyncio.run(detector.main_arbitrage_loop())
    
    except KeyboardInterrupt:
        logger.info("Arbitrage bot shutdown initiated by user.")
    except Exception as e:
        logger.error(f"Critical error in arbitrage bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
