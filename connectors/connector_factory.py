"""Connector Factory Implementation"""
from connectors.base_connector import CLOBConnector, AMMConnector
from connectors.binance import BinanceConnector
from connectors.bitget import BitgetConnector
from connectors.bybit import BybitConnector
from connectors.cube import CubeConnector
from connectors.coinbase import CoinbaseConnector
from connectors.hashkey import HashkeyConnector
from connectors.htx import HTXConnector
from connectors.okx import OKXConnector
from connectors.bitmart import BitmartConnector
from connectors.carbon import CarbonConnector
from connectors.openocean import OpenOceanConnector
from connectors.sushiswap import SushiswapConnector
from connectors.tinyman import TinymanConnector
from connectors.telos import TelosConnector
from connectors.vvs import VVSConnector
from connectors.xswap import XSwapConnector
from connectors.pancakeswap import PancakeSwapConnector
from connectors.curve import CurveConnector
from connectors.balancer import BalancerConnector
from connectors.etcswap import ETCSwapConnector

class ConnectorFactory:
    """Factory for creating exchange connectors"""
    
    CEX_MAPPING = {
        'binance': BinanceConnector,
        'bitget': BitgetConnector,
        'bybit': BybitConnector,
        'cube': CubeConnector,
        'coinbase': CoinbaseConnector,
        'hashkey': HashkeyConnector,
        'htx': HTXConnector,
        'okx': OKXConnector,
        'bitmart': BitmartConnector
    }
    
    DEX_MAPPING = {
        'carbon': CarbonConnector,
        'openocean': OpenOceanConnector,
        'sushiswap': SushiswapConnector,
        'tinyman': TinymanConnector,
        'telos': TelosConnector,
        'vvs': VVSConnector,
        'xswap': XSwapConnector,
        'pancakeswap': PancakeSwapConnector,
        'curve': CurveConnector,
        'balancer': BalancerConnector,
        'etcswap': ETCSwapConnector
    }
    
    @staticmethod
    def create_cex_connector(
        exchange: str,
        api_key: str,
        api_secret: str
    ) -> CLOBConnector:
        """Create a CEX connector"""
        if exchange not in ConnectorFactory.CEX_MAPPING:
            raise ValueError(f"Unsupported CEX: {exchange}")
        return ConnectorFactory.CEX_MAPPING[exchange](api_key, api_secret)
        
    @staticmethod
    def create_dex_connector(
        dex: str,
        rpc_url: str
    ) -> AMMConnector:
        """Create a DEX connector"""
        if dex not in ConnectorFactory.DEX_MAPPING:
            raise ValueError(f"Unsupported DEX: {dex}")
        return ConnectorFactory.DEX_MAPPING[dex](rpc_url)