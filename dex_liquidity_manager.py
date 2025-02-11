"""
Updated Dex Liquidity Manager using Connector System
"""
import asyncio
from typing import List, Dict, Optional
from connectors.connector_factory import ConnectorFactory
from logger_config import get_logger
from web3.types import TxReceipt
from eth_typing import ChecksumAddress

logger = get_logger("dex_liquidity_manager")
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from connectors.exceptions import ConnectorError, RateLimitError, NetworkError

class DexLiquidityManager:
    """Manages DEX liquidity data using connector system"""
    
    def __init__(self):
        self.connectors = {
            'uniswap_v3': {
                'chain': 'ethereum',
                'rpc_url': 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID',
                'router_address': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                'factory_address': '0x1F98431c8aD98523631AE4a59f267346ea31F984'
            },
            # Add other DEX configurations here
        }
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((NetworkError, RateLimitError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {retry_state.fn.__name__} after {retry_state.attempt_number} attempts"
        )
    )
    async def get_connector(self, dex_name: str) -> Optional[BaseConnector]:
        """Get connector instance for DEX"""
        try:
            config = self.connectors.get(dex_name)
            if not config:
                logger.warning(f"No configuration found for DEX: {dex_name}")
                return None
                
            return ConnectorFactory.get_connector(
                connector_type=dex_name,
                chain=config['chain'],
                rpc_url=config['rpc_url'],
                router_address=config['router_address'],
                factory_address=config['factory_address']
            )
        except ConnectorError as e:
            logger.error(f"Failed to get connector for {dex_name}: {str(e)}")
            return None
            
    async def get_top_pairs(self, dex_name: str) -> List[Dict]:
        """Get top trading pairs for a DEX"""
        connector = await self.get_connector(dex_name)
        if not connector:
            return []
            
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((NetworkError, RateLimitError)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying get_top_pairs after {retry_state.attempt_number} attempts"
            )
        )
        def _get_markets() -> Dict:
            """Internal function to get markets with retry logic"""
            return connector.get_available_markets()
            
        try:
            markets = _get_markets()
            if not markets:
                logger.warning(f"No markets found for DEX: {dex_name}")
                return []
                
            return [
                {
                    'dex': dex_name,
                    'pair': pair,
                    'tvl': float(market.get('tvl', 0)),
                    'volume': float(market.get('volume', 0))
                }
                for pair, market in markets.items()
            ]
        except (ConnectorError, ValueError) as e:
            logger.error(f"Failed to get top pairs for {dex_name}: {str(e)}")
            return []
            
    async def get_price(self, dex_name: str, base_token: str, quote_token: str, amount: float) -> Optional[Tuple[float, float]]:
        """Get price for a token pair"""
        connector = await self.get_connector(dex_name)
        if not connector:
            return None
            
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((NetworkError, RateLimitError)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying get_price after {retry_state.attempt_number} attempts"
            )
        )
        def _get_price() -> Optional[Tuple[float, float]]:
            """Internal function to get price with retry logic"""
            return connector.get_price(base_token, quote_token, amount)
            
        try:
            price = _get_price()
            if not price or price[0] <= 0 or price[1] <= 0:
                logger.warning(f"Invalid price returned for {base_token}/{quote_token} on {dex_name}")
                return None
                
            return price
        except (ConnectorError, ValueError) as e:
            logger.error(f"Price calculation failed for {dex_name}: {str(e)}")
            return None
            
    async def execute_swap(
        self,
        dex_name: str,
        base_token: str,
        quote_token: str,
        amount: float,
        slippage: float,
        wallet_address: ChecksumAddress
    ) -> Optional[TxReceipt]:
        """Execute token swap"""
        connector = await self.get_connector(dex_name)
        if not connector:
            return None
            
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((NetworkError, RateLimitError)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying execute_swap after {retry_state.attempt_number} attempts"
            )
        )
        def _execute_swap() -> Optional[TxReceipt]:
            """Internal function to execute swap with retry logic"""
            return connector.swap_tokens(
                base_token,
                quote_token,
                amount,
                slippage,
                wallet_address
            )
            
        try:
            tx_receipt = _execute_swap()
            if not tx_receipt:
                logger.error(f"Swap transaction failed for {base_token}/{quote_token} on {dex_name}")
                return None
                
            logger.info(f"Swap executed successfully: {tx_receipt.transactionHash.hex()}")
            return tx_receipt
        except (ConnectorError, ValueError) as e:
            logger.error(f"Swap execution failed for {dex_name}: {str(e)}")
            return None
            
    async def get_top_trading_pairs(self) -> List[str]:
        """Get top trading pairs across all DEXs"""
        try:
            tasks = [
                self.get_top_pairs(dex_name)
                for dex_name in self.connectors.keys()
            ]
            results = await asyncio.gather(*tasks)
            
            # Merge and sort pairs
            all_pairs = [pair for sublist in results for pair in sublist]
            sorted_pairs = sorted(
                all_pairs,
                key=lambda x: (x['tvl'] * 0.7 + x['volume'] * 0.3),
                reverse=True
            )
            
            # Extract unique pairs
            unique_pairs = []
            seen_pairs = set()
            for pair in sorted_pairs:
                if pair['pair'] not in seen_pairs:
                    seen_pairs.add(pair['pair'])
                    unique_pairs.append(pair['pair'])
                    
            return unique_pairs[:30]
        except Exception as e:
            logger.error(f"Failed to get top trading pairs: {str(e)}")
            return ['WETH/USDC', 'WBTC/USDT', 'ETH/USDT']
