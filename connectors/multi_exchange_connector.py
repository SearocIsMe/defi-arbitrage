"""OKX Connector Implementation with Multi-Exchange Support"""
import os
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional


class MultiExchangeConnector:
    # Load environment variables at the start of the class
    load_dotenv()

    """
    Multi-exchange connector with support for CEX and DEX markets
    
    Supports different API types:
    - Native (direct API integration)
    - CCXT (standardized exchange library)
    - Web3 (blockchain-based exchanges)
    """
    
    def __init__(self, config_path: str = 'config/exchanges.yaml'):
        """
        Initialize multi-exchange connector
        
        Args:
            config_path (str): Path to exchanges configuration file
        """
        self.config = self._load_config(config_path)
        self.exchanges = {}
        self._initialize_exchanges()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load exchange configuration from YAML file
        
        Args:
            config_path (str): Path to configuration file
        
        Returns:
            Dict containing exchange configurations
        """
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading exchange configuration: {e}")
            return {'cex_exchanges': [], 'dex_exchanges': []}
    
    def _initialize_exchanges(self):
        """
        Initialize supported exchanges based on configuration
        """
        # Initialize CEX exchanges
        for exchange_config in self.config.get('cex_exchanges', []):
            try:
                self._initialize_cex_exchange(exchange_config)
            except Exception as e:
                print(f"Error initializing CEX {exchange_config['name']}: {e}")
        
        # Initialize DEX exchanges
        for exchange_config in self.config.get('dex_exchanges', []):
            try:
                self._initialize_dex_exchange(exchange_config)
            except Exception as e:
                print(f"Error initializing DEX {exchange_config['name']}: {e}")
    
    def _initialize_cex_exchange(self, exchange_config: Dict[str, Any]):
        """
        Initialize a CEX exchange connector
        
        Args:
            exchange_config (Dict): Configuration for the exchange
        """
        exchange_name = exchange_config['name']
        api_type = exchange_config.get('api_type', 'ccxt')
        
        # Retrieve API credentials from environment
        api_key = os.getenv(f"{exchange_name.upper()}_API_KEY")
        api_secret = os.getenv(f"{exchange_name.upper()}_SECRET_KEY")
        
        if not (api_key and api_secret):
            print(f"Skipping {exchange_name}: Missing API credentials")
            return
        
        if api_type == 'ccxt':
            # Use CCXT for standardized exchange integration
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True
            })
            self.exchanges[exchange_name] = exchange
        elif api_type == 'native':
            # Use native API for specific exchanges (like OKX)
            if exchange_name == 'okx':
                from connectors.base_cex_connector import BaseCEXConnector
                exchange = BaseCEXConnector(exchange_name, api_key, api_secret)
                self.exchanges[exchange_name] = exchange
    
    def _initialize_dex_exchange(self, exchange_config: Dict[str, Any]):
        """
        Initialize a DEX exchange connector
        
        Args:
            exchange_config (Dict): Configuration for the DEX exchange
        """
        exchange_name = exchange_config['name']
        chain = exchange_config.get('chain', 'ethereum')
        
        # Retrieve RPC URL from environment or chain configuration
        # Retrieve RPC URL with multiple fallback mechanisms
        rpc_url = (
            # 1. Try chain-specific RPC URL from environment
            os.getenv(f"{chain.upper()}_RPC_URL") or 
            # 2. Use global WEB3_PROVIDER_URL from .env
            os.getenv('WEB3_PROVIDER_URL') or 
            # 3. Fallback to default local provider
            'http://localhost:8545'
        )
        # Use Web3 for DEX initialization
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Placeholder for DEX-specific initialization
            # In a real implementation, you'd use specific DEX contract ABIs
            self.exchanges[f"{exchange_name}_{chain}"] = {
                'web3': w3,
                'chain': chain,
                'name': exchange_name
            }
        except Exception as e:
            print(f"Error initializing DEX {exchange_name} on {chain}: {e}")
    
    async def fetch_top_trading_pairs(self, limit: int = 50) -> Dict[str, Dict[str, Any]]:
        """
        Fetch top trading pairs across all initialized exchanges
        
        Args:
            limit (int): Number of top pairs to fetch
        
        Returns:
            Dict of top trading pairs from different exchanges
        """
        top_pairs = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                if hasattr(exchange, 'fetch_tickers'):
                    # CCXT-style exchanges
                    tickers = await exchange.fetch_tickers()
                    sorted_pairs = sorted(
                        tickers.items(), 
                        key=lambda x: float(x[1].get('quoteVolume', 0) or 0), 
                        reverse=True
                    )[:limit]
                    
                    top_pairs[exchange_name] = {
                        pair: {
                            'volume': ticker.get('quoteVolume', 0),
                            'last_price': ticker.get('last', 0)
                        } 
                        for pair, ticker in sorted_pairs
                    }
                elif isinstance(exchange, dict) and 'web3' in exchange:
                    # DEX placeholder (would need actual implementation)
                    top_pairs[exchange_name] = self._fetch_dex_pairs(exchange, limit)
            except Exception as e:
                print(f"Error fetching pairs from {exchange_name}: {e}")
        
        return top_pairs
    
    def _fetch_dex_pairs(self, dex_info: Dict[str, Any], limit: int) -> Dict[str, Dict[str, float]]:
        """
        Placeholder method for fetching DEX trading pairs
        
        Args:
            dex_info (Dict): DEX exchange information
            limit (int): Number of pairs to fetch
        
        Returns:
            Dict of top DEX trading pairs
        """
        # Placeholder implementation
        return {
            'ETH/USDT': {'volume': 1000000, 'last_price': 2000},
            'WBTC/USDT': {'volume': 500000, 'last_price': 40000}
        }
    
    async def calculate_momentum(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calculate trading pair momentum across exchanges
        
        Args:
            symbol (str): Trading pair symbol
            period (int): Number of historical periods to analyze
        
        Returns:
            Optional momentum value
        """
        momentums = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                if hasattr(exchange, 'fetch_ohlcv'):
                    historical_data = await exchange.fetch_ohlcv(symbol, '1d', limit=period)
                    
                    price_changes = [
                        (historical_data[i][4] - historical_data[i-1][4]) / historical_data[i-1][4] 
                        for i in range(1, len(historical_data))
                    ]
                    
                    momentum = sum(price_changes) / len(price_changes) if price_changes else None
                    momentums[exchange_name] = momentum
            except Exception as e:
                print(f"Momentum calculation error for {symbol} on {exchange_name}: {e}")
        
        # Return average momentum across exchanges
        valid_momentums = [m for m in momentums.values() if m is not None]
        return sum(valid_momentums) / len(valid_momentums) if valid_momentums else None
