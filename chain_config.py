from typing import Dict, Any, List, Optional
import os
import json
import yaml
import jsonschema
from decimal import Decimal

class ChainConfigurationError(Exception):
    """Custom exception for chain configuration errors"""
    pass

def validate_chain_config(config: Dict[str, Any]):
    """
    Validate blockchain configuration
    
    Args:
        config (Dict[str, Any]): Chain configuration to validate
    
    Raises:
        ChainConfigurationError: If configuration is invalid
    """
    chain_config_schema = {
        "type": "object",
        "patternProperties": {
            "^[a-z_]+$": {
                "type": "object",
                "required": ["chain_id", "rpc_url"],
                "properties": {
                    "chain_id": {"type": "number"},
                    "rpc_url": {"type": "string"},
                    "native_token": {
                        "type": "object",
                        "required": ["symbol", "decimals"],
                        "properties": {
                            "symbol": {"type": "string"},
                            "decimals": {"type": "number"}
                        }
                    },
                    "dexes": {
                        "type": "object",
                        "patternProperties": {
                            "^[a-z_]+$": {
                                "type": "object",
                                "required": ["router_address"],
                                "properties": {
                                    "router_address": {"type": "string"},
                                    "factory_address": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    try:
        jsonschema.validate(instance=config, schema=chain_config_schema)
    except jsonschema.ValidationError as e:
        raise ChainConfigurationError(f"Invalid chain configuration: {e}")

# Predefined chain configurations
CHAIN_CONFIG: Dict[str, Any] = {
    "ethereum": {
        "chain_id": 1,
        "rpc_url": "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID",
        "native_token": {
            "symbol": "ETH",
            "decimals": 18
        },
        "dexes": {
            "uniswap_v3": {
                "router_address": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "factory_address": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
            },
            "sushiswap": {
                "router_address": "0xd9e1cE17f2241b764c9A52b68E5C51Dc9881D56A",
                "factory_address": "0xC0AEe478e3658e2610c5661424308f0A5d179F52"
            }
        }
    },
    "binance_smart_chain": {
        "chain_id": 56,
        "rpc_url": "https://bsc-dataseed.binance.org/",
        "native_token": {
            "symbol": "BNB",
            "decimals": 18
        },
        "dexes": {
            "pancakeswap": {
                "router_address": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "factory_address": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
            }
        }
    },
    "polygon": {
        "chain_id": 137,
        "rpc_url": "https://polygon-rpc.com",
        "native_token": {
            "symbol": "MATIC",
            "decimals": 18
        },
        "dexes": {
            "quickswap": {
                "router_address": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
                "factory_address": "0x5757371414417b8C6CAad45b7f503a9c27A7A4A5"
            }
        }
    }
}

# Bridge configuration for cross-chain arbitrage
BRIDGE_CONFIG: Dict[str, Any] = {
    "bridges": {
        "multichain": {
            "router_address": "0x6b7a87899490EcE95443e979cA9485CBE7E71954",
            "supported_chains": ["ethereum", "binance_smart_chain", "polygon"]
        },
        "hop_protocol": {
            "supported_chains": ["ethereum", "polygon", "optimism", "arbitrum"]
        }
    }
}

# Gas limit configurations
GAS_LIMITS: Dict[str, int] = {
    "uniswap_v3_swap": 200000,
    "sushiswap_swap": 150000,
    "pancakeswap_swap": 180000
}

# Default tokens for arbitrage
DEFAULT_TOKENS: Dict[str, Dict[str, str]] = {
    "ethereum": {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    },
    "binance_smart_chain": {
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
        "USDT": "0x55d398326f99059fF775485246999027B3197955"
    }
}

class ChainConfigManager:
    """
    Manage and interact with blockchain configurations
    """
    
    @staticmethod
    def load_custom_config(path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load custom chain configuration from file
        
        Args:
            path (str, optional): Path to configuration file
        
        Returns:
            Dict[str, Any]: Loaded configuration
        """
        if not path:
            # Check for common config file locations
            possible_paths = [
                'chain_config.json', 
                'chain_config.yaml', 
                'chain_config.yml',
                os.path.join(os.getcwd(), 'config', 'chain_config.json')
            ]
            
            for possible_path in possible_paths:
                if os.path.exists(possible_path):
                    path = possible_path
                    break
        
        if not path or not os.path.exists(path):
            return {}
        
        # Determine file type and load
        if path.endswith('.json'):
            with open(path, 'r') as f:
                config = json.load(f)
        elif path.endswith(('.yaml', '.yml')):
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file type: {path}")
        
        # Validate loaded configuration
        validate_chain_config(config)
        
        return config
    
    @staticmethod
    def get_chain_rpc_url(chain_name: str) -> str:
        """
        Get RPC URL for a specific chain
        
        Args:
            chain_name (str): Name of the blockchain
        
        Returns:
            str: RPC URL
        
        Raises:
            ChainConfigurationError: If chain not found
        """
        chain_config = CHAIN_CONFIG.get(chain_name)
        if not chain_config:
            raise ChainConfigurationError(f"Chain not found: {chain_name}")
        
        return chain_config['rpc_url']
    
    @staticmethod
    def get_dex_router_address(
        chain_name: str, 
        dex_name: str
    ) -> str:
        """
        Get router address for a specific DEX on a chain
        
        Args:
            chain_name (str): Blockchain name
            dex_name (str): Decentralized exchange name
        
        Returns:
            str: Router contract address
        
        Raises:
            ChainConfigurationError: If chain or DEX not found
        """
        chain_config = CHAIN_CONFIG.get(chain_name)
        if not chain_config:
            raise ChainConfigurationError(f"Chain not found: {chain_name}")
        
        dexes = chain_config.get('dexes', {})
        dex_config = dexes.get(dex_name)
        
        if not dex_config:
            raise ChainConfigurationError(
                f"DEX {dex_name} not found on chain {chain_name}"
            )
        
        return dex_config['router_address']
