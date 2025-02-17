import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import yaml
import jsonschema

class ConfigManager:
    """
    Centralized configuration management for the arbitrage bot
    Supports loading from .env, JSON, YAML, and environment variables
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigManager
        
        Args:
            config_path (str, optional): Path to configuration file. 
                                         Defaults to .env or config.json/config.yaml
        """
        # Load environment variables
        load_dotenv()
        
        # Default configuration paths
        self._default_config_paths = [
            '.env',
            'config.json', 
            'config.yaml', 
            'config.yml'
        ]
        
        # Configuration schema for validation
        self._config_schema = {
            "type": "object",
            "properties": {
                "wallet_address": {"type": "string"},
                "web3_provider_url": {"type": "string"},
                "exchanges": {
                    "type": "object",
                    "properties": {
                        "binance": {
                            "type": "object",
                            "properties": {
                                "api_key": {"type": "string"},
                                "secret_key": {"type": "string"}
                            }
                        },
                        "okx": {
                            "type": "object",
                            "properties": {
                                "api_key": {"type": "string"},
                                "secret_key": {"type": "string"}
                            }
                        }
                    }
                },
                "arbitrage_settings": {
                    "type": "object",
                    "properties": {
                        "min_profit_percentage": {"type": "number"},
                        "max_trade_amount": {"type": "number"},
                        "check_interval": {"type": "number"}
                    }
                }
            },
            "required": ["wallet_address", "web3_provider_url"]
        }
        
        # Load configuration
        self._config = self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from various sources
        
        Args:
            config_path (str, optional): Specific configuration file path
        
        Returns:
            Dict[str, Any]: Loaded configuration
        """
        # If specific path provided, try loading from that
        if config_path:
            return self._load_config_file(config_path)
        
        # Try default paths
        for path in self._default_config_paths:
            try:
                return self._load_config_file(path)
            except FileNotFoundError:
                continue
        
        # Fallback to environment variables
        return self._load_env_config()
    
    def _load_config_file(self, path: str) -> Dict[str, Any]:
        """
        Load configuration from a specific file
        
        Args:
            path (str): Path to configuration file
        
        Returns:
            Dict[str, Any]: Loaded configuration
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        # Determine file type and load accordingly
        if path.endswith('.json'):
            with open(path, 'r') as f:
                config = json.load(f)
        elif path.endswith(('.yaml', '.yml')):
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        elif path.endswith('.env'):
            config = self._load_env_config()
        else:
            raise ValueError(f"Unsupported configuration file type: {path}")
        
        # Validate configuration against schema
        self._validate_config(config)
        
        return config
    
    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables
        
        Returns:
            Dict[str, Any]: Configuration from environment
        """
        config = {
            "wallet_address": os.getenv('WALLET_ADDRESS'),
            "web3_provider_url": os.getenv('WEB3_PROVIDER_URL'),
            "exchanges": {
                "binance": {
                    "api_key": os.getenv('BINANCE_API_KEY'),
                    "secret_key": os.getenv('BINANCE_SECRET_KEY')
                },
                "okx": {
                    "api_key": os.getenv('OKX_API_KEY'),
                    "secret_key": os.getenv('OKX_SECRET_KEY')
                }
            },
            "arbitrage_settings": {
                "min_profit_percentage": float(os.getenv('MIN_ARBITRAGE_PROFIT', 0.5)),
                "max_trade_amount": float(os.getenv('MAX_TRADE_AMOUNT', 1000)),
                "check_interval": int(os.getenv('ARBITRAGE_CHECK_INTERVAL', 60))
            }
        }
        
        # Validate configuration
        self._validate_config(config)
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]):
        """
        Validate configuration against predefined schema
        
        Args:
            config (Dict[str, Any]): Configuration to validate
        
        Raises:
            jsonschema.ValidationError: If configuration is invalid
        """
        try:
            jsonschema.validate(instance=config, schema=self._config_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value
        
        Args:
            key (str): Configuration key
            default (Any, optional): Default value if key not found
        
        Returns:
            Any: Configuration value
        """
        # Support nested key access
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value
    
    def update(self, updates: Dict[str, Any]):
        """
        Update configuration
        
        Args:
            updates (Dict[str, Any]): Configuration updates
        """
        # Merge updates with existing configuration
        self._config.update(updates)
        
        # Revalidate
        self._validate_config(self._config)
    
    def save(self, path: Optional[str] = None):
        """
        Save current configuration
        
        Args:
            path (str, optional): Path to save configuration
        """
        path = path or 'config.json'
        
        with open(path, 'w') as f:
            json.dump(self._config, f, indent=4)

# Singleton instance
config = ConfigManager()