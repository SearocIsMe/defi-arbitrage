"""
Connector Factory
Manages creation and caching of connector instances
"""
from typing import Dict, Type
from connectors.base_connector import BaseConnector, CLOBConnector, AMMConnector
from connectors.uniswap_v3 import UniswapV3Connector
from logger_config import get_logger

logger = get_logger("connector_factory")

class ConnectorFactory:
    """Factory for creating and managing connector instances"""
    
    _connector_registry: Dict[str, Type[BaseConnector]] = {
        'uniswap_v3': UniswapV3Connector,
        # Add other connectors here
    }
    
    _instances: Dict[str, BaseConnector] = {}
    
    @classmethod
    def get_connector(
        cls,
        connector_type: str,
        chain: str,
        rpc_url: str,
        router_address: str,
        factory_address: str
    ) -> BaseConnector:
        """Get connector instance"""
        cache_key = f"{connector_type}_{chain}"
        
        if cache_key in cls._instances:
            return cls._instances[cache_key]
            
        if connector_type not in cls._connector_registry:
            raise ValueError(f"Unsupported connector type: {connector_type}")
            
        connector_class = cls._connector_registry[connector_type]
        
        try:
            instance = connector_class(
                chain=chain,
                rpc_url=rpc_url,
                router_address=router_address,
                factory_address=factory_address
            )
            cls._instances[cache_key] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to create connector: {str(e)}")
            raise
        
    @classmethod
    def register_connector(
        cls,
        connector_type: str,
        connector_class: Type[BaseConnector]
    ):
        """Register new connector type"""
        if not issubclass(connector_class, (CLOBConnector, AMMConnector)):
            raise ValueError("Connector must implement CLOBConnector or AMMConnector")
            
        cls._connector_registry[connector_type] = connector_class
        logger.info(f"Registered new connector type: {connector_type}")