"""
Chain and Bridge Configuration Module
Provides configuration for supported chains and cross-chain bridges
"""
import os
from typing import Dict, Optional
from logger_config import get_logger

logger = get_logger("chain_config")

class ChainConfigError(Exception):
    """Custom exception for chain configuration errors"""
    pass

def validate_chain_config(chain_name: str, config: Dict) -> bool:
    """
    Validates chain configuration
    Returns True if valid, False if invalid
    """
    required_fields = ['name', 'chain_id', 'rpc', 'dex', 'token_addresses']
    try:
        # Check required fields
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field '{field}' in chain config for {chain_name}")
                return False
        
        # Validate DEX addresses
        if not isinstance(config['dex'], dict) or not config['dex']:
            logger.error(f"Invalid DEX configuration for chain {chain_name}")
            return False
            
        # Validate token addresses
        if not isinstance(config['token_addresses'], dict) or not config['token_addresses']:
            logger.error(f"Invalid token addresses for chain {chain_name}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validating chain config for {chain_name}: {str(e)}")
        return False

def get_chain_config(chain_name: str) -> Optional[Dict]:
    """
    Safely get chain configuration
    Returns None if chain is not supported or invalid
    """
    try:
        if chain_name not in CHAIN_CONFIG:
            logger.warning(f"Unsupported chain: {chain_name}")
            return None
            
        config = CHAIN_CONFIG[chain_name]
        if not validate_chain_config(chain_name, config):
            logger.error(f"Invalid configuration for chain: {chain_name}")
            return None
            
        return config
    except Exception as e:
        logger.error(f"Error getting chain config for {chain_name}: {str(e)}")
        return None

# Chain configurations including Layer 2s and independent chains
CHAIN_CONFIG = {
    # Layer 2 Networks
    'arbitrum': {
        'name': 'Arbitrum One',
        'chain_id': 42161,
        'rpc': 'https://arb1.arbitrum.io/rpc',
        'dex': {
            'uniswap_v3': '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
            'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
        },
        'token_addresses': {
            'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
            'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'
        }
    },
    'optimism': {
        'name': 'Optimism',
        'chain_id': 10,
        'rpc': 'https://mainnet.optimism.io',
        'dex': {
            'uniswap_v3': '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
            'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
        },
        'token_addresses': {
            'WETH': '0x4200000000000000000000000000000000000006',
            'USDC': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607'
        }
    },
    'zksync': {
        'name': 'zkSync Era',
        'chain_id': 324,
        'rpc': 'https://mainnet.era.zksync.io',
        'dex': {
            'syncswap': '0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295',
            'mute': '0x8B791913eB07C32779a16750e3868aA8495F5964'
        },
        'token_addresses': {
            'WETH': '0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91',
            'USDC': '0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4'
        }
    },
    'base': {
        'name': 'Base',
        'chain_id': 8453,
        'rpc': 'https://mainnet.base.org',
        'dex': {
            'uniswap_v3': '0x2626664c2603336E57B271c5C0b26F421741e481',
            'baseswap': '0x327Df1E6de05895d2ab08513aaDD9313Fe505d86'
        },
        'token_addresses': {
            'WETH': '0x4200000000000000000000000000000000000006',
            'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
        }
    },

    # Independent Chains
    'bsc': {
        'name': 'BNB Chain',
        'chain_id': 56,
        'rpc': 'https://bsc-dataseed.binance.org',
        'dex': {
            'pancakeswap': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
            'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
        },
        'token_addresses': {
            'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
            'USDT': '0x55d398326f99059fF775485246999027B3197955',
            'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
        }
    },
    'avalanche': {
        'name': 'Avalanche C-Chain',
        'chain_id': 43114,
        'rpc': 'https://api.avax.network/ext/bc/C/rpc',
        'dex': {
            'traderjoe': '0x60aE616a2155Ee3d9A68541Ba4544862310933d4',
            'pangolin': '0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106'
        },
        'token_addresses': {
            'WAVAX': '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7',
            'USDC': '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E'
        }
    },
    'polygon': {
        'name': 'Polygon PoS',
        'chain_id': 137,
        'rpc': 'https://polygon-rpc.com',
        'dex': {
            'quickswap': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff',
            'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
        },
        'token_addresses': {
            'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
            'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
        }
    },
    'fantom': {
        'name': 'Fantom Opera',
        'chain_id': 250,
        'rpc': 'https://rpc.ftm.tools',
        'dex': {
            'spookyswap': '0xF491e7B69E4244ad4002BC14e878a34207E38c29',
            'spiritswap': '0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52'
        },
        'token_addresses': {
            'WFTM': '0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83',
            'USDC': '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75'
        }
    },
    
    # Base Ethereum network (for reference)
    'ethereum': {
        'name': 'Ethereum',
        'chain_id': 1,
        'rpc': f"https://mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}",
        'dex': {
            'uniswap_v3': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
            'sushiswap': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
        },
        'token_addresses': {
            'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
        }
    }
}

# Cross-chain bridge configurations
BRIDGE_CONFIG = {
    'layerzero': {
        'name': 'LayerZero',
        'contracts': {
            'ethereum': '0x66A71Dcef29A0fFBDBE3c6a460a3B5BC225Cd675',
            'arbitrum': '0x3c2269811836af69497E5F486A85D7316753cf62',
            'optimism': '0x3c2269811836af69497E5F486A85D7316753cf62',
            'bsc': '0x3c2269811836af69497E5F486A85D7316753cf62',
            'avalanche': '0x3c2269811836af69497E5F486A85D7316753cf62',
            'polygon': '0x3c2269811836af69497E5F486A85D7316753cf62',
            'fantom': '0x3c2269811836af69497E5F486A85D7316753cf62'
        }
    },
    'stargate': {
        'name': 'Stargate',
        'contracts': {
            'ethereum': '0x8731d54E9D02c286767d56ac03e8037C07e01e98',
            'arbitrum': '0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614',
            'optimism': '0x4200000000000000000000000000000000000010',
            'bsc': '0x4a364f8c717cAAD9A442737Eb7b8A55cc6cf18D8',
            'avalanche': '0x45A01E4e04F14f7A4a6702c74187c5F6222033cd',
            'polygon': '0x45A01E4e04F14f7A4a6702c74187c5F6222033cd',
            'fantom': '0x45A01E4e04F14f7A4a6702c74187c5F6222033cd'
        }
    },
    'multichain': {
        'name': 'Multichain',
        'contracts': {
            'ethereum': '0x6b7a87899490EcE95443e979cA9485CBE7E71522',
            'arbitrum': '0x6b7a87899490EcE95443e979cA9485CBE7E71522',
            'optimism': '0x6b7a87899490EcE95443e979cA9485CBE7E71522',
            'bsc': '0x6b7a87899490EcE95443e979cA9485CBE7E71522',
            'avalanche': '0x6b7a87899490EcE95443e979cA9485CBE7E71522',
            'polygon': '0x6b7a87899490EcE95443e979cA9485CBE7E71522',
            'fantom': '0x6b7a87899490EcE95443e979cA9485CBE7E71522'
        }
    },
    'celer': {
        'name': 'Celer',
        'contracts': {
            'ethereum': '0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820',
            'arbitrum': '0x1619DE6B6B20eD217a58d00f37B9d47C7663feca',
            'optimism': '0x9D39Fc627A6d9d9F8C831c16995b209548cc3401',
            'bsc': '0xdd90E5E87A2081Dcf0391920868eBc2FFB81a1aF',
            'avalanche': '0xef3c714c9425a8F3697A9C969Dc1af30ba82e5d4',
            'polygon': '0x1619DE6B6B20eD217a58d00f37B9d47C7663feca',
            'fantom': '0x374B8a9f3eC5eB2D97ECA84Ea27aCa45aa1C57EF'
        }
    }
}

def validate_bridge_config(bridge_name: str, config: Dict) -> bool:
    """
    Validates bridge configuration
    Returns True if valid, False if invalid
    """
    try:
        if 'name' not in config or 'contracts' not in config:
            logger.error(f"Missing required fields in bridge config for {bridge_name}")
            return False
            
        if not isinstance(config['contracts'], dict) or not config['contracts']:
            logger.error(f"Invalid contracts configuration for bridge {bridge_name}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validating bridge config for {bridge_name}: {str(e)}")
        return False

def get_bridge_config(bridge_name: str) -> Optional[Dict]:
    """
    Safely get bridge configuration
    Returns None if bridge is not supported or invalid
    """
    try:
        if bridge_name not in BRIDGE_CONFIG:
            logger.warning(f"Unsupported bridge: {bridge_name}")
            return None
            
        config = BRIDGE_CONFIG[bridge_name]
        if not validate_bridge_config(bridge_name, config):
            logger.error(f"Invalid configuration for bridge: {bridge_name}")
            return None
            
        return config
    except Exception as e:
        logger.error(f"Error getting bridge config for {bridge_name}: {str(e)}")
        return None

# Gas limit configurations for different operation types
GAS_LIMITS = {
    'swap': 200000,
    'bridge': 350000,
    'approve': 50000
}

# Default tokens for price monitoring
DEFAULT_TOKENS = {
    'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
}
