"""Connector Factory Implementation with Multi-Exchange Support"""
from typing import Union, Optional
from connectors.multi_exchange_connector import MultiExchangeConnector

class ConnectorFactory:
    """Factory for creating multi-exchange connectors"""
    
    @staticmethod
    def create_connector(
        config_path: str = 'config/exchanges.yaml'
    ) -> MultiExchangeConnector:
        """
        Create a multi-exchange connector
        
        Args:
            config_path (str): Path to exchanges configuration file
        
        Returns:
            MultiExchangeConnector: Initialized multi-exchange connector
        """
        return MultiExchangeConnector(config_path)
    
    @staticmethod
    def create_web3_wallet(
        exchange: str,
        api_key: str,
        api_secret: str,
        web3_api_key: str
    ) -> Union[dict, None]:
        """
        Create a Web3 wallet using the specified exchange's API
        
        Args:
            exchange (str): Exchange name
            api_key (str): CEX API key
            api_secret (str): CEX API secret
            web3_api_key (str): Web3 API key
        
        Returns:
            Dict containing wallet creation details or None
        """
        try:
            # Use MultiExchangeConnector to create wallet
            connector = MultiExchangeConnector()
            
            # Placeholder for wallet creation method
            # In a real implementation, this would use the specific exchange's Web3 API
            wallet_details = {
                'exchange': exchange,
                'wallet_address': None,  # Would be populated by actual API call
                'creation_timestamp': None
            }
            
            return wallet_details
        
        except Exception as e:
            print(f"Web3 wallet creation error: {e}")
            return None
    
    @staticmethod
    def get_supported_exchanges(
        config_path: str = 'config/exchanges.yaml'
    ) -> dict:
        """
        Retrieve supported exchanges from configuration
        
        Args:
            config_path (str): Path to exchanges configuration file
        
        Returns:
            Dict of supported CEX and DEX exchanges
        """
        try:
            import yaml
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            return {
                'cex': [ex['name'] for ex in config.get('cex_exchanges', [])],
                'dex': [ex['name'] for ex in config.get('dex_exchanges', [])]
            }
        
        except Exception as e:
            print(f"Error reading exchange configuration: {e}")
            return {'cex': [], 'dex': []}