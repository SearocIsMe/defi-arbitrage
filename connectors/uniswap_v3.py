"""
Uniswap V3 Connector Implementation
"""
from typing import Dict, Optional, Any
from web3 import Web3
from web3.contract import Contract
from connectors.base_dex_connector import BaseDEXConnector
from logger_config import get_logger

logger = get_logger("uniswap_v3_connector")

class UniswapV3Connector(BaseDEXConnector):
    """Uniswap V3 DEX Connector Implementation"""
    
    def __init__(self, w3: Web3, chain_config: Dict[str, Any]):
        """
        Initialize Uniswap V3 Connector
        
        Args:
            w3 (Web3): Web3 instance for blockchain interactions
            chain_config (Dict[str, Any]): Configuration for Uniswap V3 on this chain
        """
        super().__init__(w3, chain_config)
        
        # Load router and factory contracts
        router_abi = chain_config.get('router_abi', [])
        factory_abi = chain_config.get('factory_abi', [])
        
        try:
            self.router_contract = self.w3.eth.contract(
                address=self.router_address, 
                abi=router_abi
            )
            self.factory_contract = self.w3.eth.contract(
                address=self.factory_address, 
                abi=factory_abi
            )
        except Exception as e:
            self.logger.error(f"Failed to load Uniswap V3 contracts: {e}")
            raise
        
        # Supported tokens and pools
        self.supported_tokens = chain_config.get('supported_tokens', [])
        
    async def fetch_market_data(self) -> Dict[str, float]:
        """
        Fetch current market data for supported token pairs
        
        Returns:
            Dict[str, float]: Market data with token pairs and their prices
        """
        market_data = {}
        
        try:
            # Iterate through supported token pairs
            for i in range(len(self.supported_tokens)):
                for j in range(i+1, len(self.supported_tokens)):
                    token_a = self.supported_tokens[i]
                    token_b = self.supported_tokens[j]
                    
                    # Get pool address for this token pair
                    pool_address = self._get_pool_address(token_a, token_b)
                    
                    if pool_address:
                        # Fetch pool data
                        pool_data = await self._fetch_pool_data(pool_address)
                        
                        # Calculate price
                        price = self._calculate_price(pool_data)
                        
                        # Store market data
                        market_data[f"{token_a}/{token_b}"] = price
        
        except Exception as e:
            self.logger.error(f"Error fetching market data: {e}")
        
        return market_data
    
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
        try:
            # Get pool address
            pool_address = self._get_pool_address(token_a, token_b)
            
            if not pool_address:
                return {}
            
            # Create pool contract
            pool_abi = self.config.get('pool_abi', [])
            pool_contract = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Fetch reserves
            reserves = pool_contract.functions.getReserves().call()
            
            return {
                token_a: reserves[0],
                token_b: reserves[1]
            }
        
        except Exception as e:
            self.logger.error(f"Error getting pool reserves: {e}")
            return {}
    
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
        try:
            # Validate addresses
            if not all(self._validate_address(addr) for addr in [token_in, token_out, sender_address]):
                raise ValueError("Invalid token or sender address")
            
            # Get token decimals
            token_in_decimals = self._get_token_decimals(token_in)
            
            # Convert amount to integer representation
            amount_in_int = int(amount_in * (10 ** token_in_decimals))
            
            # Prepare swap transaction
            swap_tx = self.router_contract.functions.exactInputSingle({
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': 3000,  # Default to 0.3% fee tier
                'recipient': sender_address,
                'deadline': self.w3.eth.get_block('latest')['timestamp'] + 300,  # 5 minutes
                'amountIn': amount_in_int,
                'amountOutMinimum': int(min_amount_out * (10 ** self._get_token_decimals(token_out))),
                'sqrtPriceLimitX96': 0
            })
            
            # Estimate gas
            gas_estimate = swap_tx.estimate_gas({'from': sender_address})
            
            # Build transaction
            tx = swap_tx.build_transaction({
                'from': sender_address,
                'gas': gas_estimate,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(sender_address)
            })
            
            return {
                'transaction': tx,
                'estimated_gas': gas_estimate
            }
        
        except Exception as e:
            self.logger.error(f"Token swap failed: {e}")
            return {
                'error': str(e)
            }
    
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
        try:
            # Validate addresses
            if not all(self._validate_address(addr) for addr in [token_a, token_b, sender_address]):
                raise ValueError("Invalid token or sender address")
            
            # Get token decimals
            decimals_a = self._get_token_decimals(token_a)
            decimals_b = self._get_token_decimals(token_b)
            
            # Convert amounts to integer representation
            amount_a_int = int(amount_a * (10 ** decimals_a))
            amount_b_int = int(amount_b * (10 ** decimals_b))
            
            # Prepare liquidity addition transaction
            add_liquidity_tx = self.router_contract.functions.addLiquidity({
                'tokenA': token_a,
                'tokenB': token_b,
                'fee': 3000,  # Default to 0.3% fee tier
                'tickLower': -887272,  # Minimum tick
                'tickUpper': 887272,   # Maximum tick
                'amount0Desired': amount_a_int,
                'amount1Desired': amount_b_int,
                'amount0Min': int(amount_a_int * 0.95),  # Allow 5% slippage
                'amount1Min': int(amount_b_int * 0.95),
                'recipient': sender_address,
                'deadline': self.w3.eth.get_block('latest')['timestamp'] + 300  # 5 minutes
            })
            
            # Estimate gas
            gas_estimate = add_liquidity_tx.estimate_gas({'from': sender_address})
            
            # Build transaction
            tx = add_liquidity_tx.build_transaction({
                'from': sender_address,
                'gas': gas_estimate,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(sender_address)
            })
            
            return {
                'transaction': tx,
                'estimated_gas': gas_estimate
            }
        
        except Exception as e:
            self.logger.error(f"Liquidity addition failed: {e}")
            return {
                'error': str(e)
            }
    
    def _get_pool_address(self, token_a: str, token_b: str) -> Optional[str]:
        """
        Get pool address for a token pair
        
        Args:
            token_a (str): Address of first token
            token_b (str): Address of second token
        
        Returns:
            Optional[str]: Pool address or None if not found
        """
        try:
            # Sort tokens to match Uniswap V3 pool address generation
            tokens = sorted([token_a, token_b])
            
            # Get pool address using factory contract
            pool_address = self.factory_contract.functions.getPool(
                tokens[0], 
                tokens[1], 
                3000  # Default 0.3% fee tier
            ).call()
            
            return pool_address
        
        except Exception as e:
            self.logger.error(f"Error getting pool address: {e}")
            return None
    
    async def _fetch_pool_data(self, pool_address: str) -> Dict[str, Any]:
        """
        Fetch detailed data for a specific pool
        
        Args:
            pool_address (str): Address of the liquidity pool
        
        Returns:
            Dict[str, Any]: Pool data
        """
        try:
            # Load pool contract
            pool_abi = self.config.get('pool_abi', [])
            pool_contract = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Fetch pool data
            slot0 = pool_contract.functions.slot0().call()
            
            return {
                'sqrt_price_x96': slot0[0],
                'tick': slot0[1]
            }
        
        except Exception as e:
            self.logger.error(f"Error fetching pool data: {e}")
            return {}
    
    def _calculate_price(self, pool_data: Dict[str, Any]) -> float:
        """
        Calculate price from pool data
        
        Args:
            pool_data (Dict[str, Any]): Pool data from Uniswap V3
        
        Returns:
            float: Calculated price
        """
        try:
            # Convert sqrt price to actual price
            sqrt_price_x96 = pool_data.get('sqrt_price_x96', 0)
            
            # Price calculation for Uniswap V3
            price = (sqrt_price_x96 / (2 ** 96)) ** 2
            
            return price
        
        except Exception as e:
            self.logger.error(f"Price calculation failed: {e}")
            return 0.0