import pytest
from chain_config import (
    ChainConfigError,
    validate_chain_config,
    get_chain_config,
    validate_bridge_config,
    get_bridge_config
,
    validate_token_config,
    get_token_config
)

class TestChainConfig:
    """Test cases for chain configuration functionality"""
    
    def test_validate_chain_config_valid(self):
        """Test validate_chain_config with valid configuration"""
        valid_config = {
            'name': 'Test Chain',
            'chain_id': 1,
            'rpc': 'https://test.chain/rpc',
            'dex': {
                'test_dex': '0x1234567890123456789012345678901234567890'
            },
            'token_addresses': {
                'TEST': '0x1234567890123456789012345678901234567890'
            }
        }
        assert validate_chain_config('test_chain', valid_config) is True
       
    def test_validate_chain_config_missing_field(self):
        """Test validate_chain_config with missing required field"""
        invalid_config = {
            'name': 'Test Chain',
            'chain_id': 1,
            'rpc': 'https://test.chain/rpc',
            'dex': {
                'test_dex': '0x1234567890123456789012345678901234567890'
            }
            # Missing token_addresses
        }
        assert validate_chain_config('test_chain', invalid_config) is False

    def test_validate_chain_config_invalid_dex(self):
        """Test validate_chain_config with invalid DEX configuration"""
        invalid_config = {
            'name': 'Test Chain',
            'chain_id': 1,
            'rpc': 'https://test.chain/rpc',
            'dex': {},  # Empty DEX config
            'token_addresses': {
                'TEST': '0x1234567890123456789012345678901234567890'
            }
        }
        assert validate_chain_config('test_chain', invalid_config) is False

    def test_validate_chain_config_invalid_tokens(self):
        """Test validate_chain_config with invalid token addresses"""
        invalid_config = {
            'name': 'Test Chain',
            'chain_id': 1,
            'rpc': 'https://test.chain/rpc',
            'dex': {
                'test_dex': '0x1234567890123456789012345678901234567890'
            },
            'token_addresses': {}  # Empty token addresses
        }
        assert validate_chain_config('test_chain', invalid_config) is False
        
    def test_get_chain_config_valid(self):
        """Test get_chain_config with valid chain name"""
        chain_name = 'ethereum'
        config = get_chain_config(chain_name)
        assert isinstance(config, dict)
        assert 'name' in config
        assert 'chain_id' in config
        assert 'rpc' in config
        assert 'dex' in config
        assert 'token_addresses' in config
        
    def test_get_chain_config_invalid(self):
        """Test get_chain_config with invalid chain name"""
        with pytest.raises(ChainConfigError):
            get_chain_config('invalid_chain')

class TestBridgeConfig:
    """Test cases for bridge configuration functionality"""
    
    def test_validate_bridge_config_valid(self):
        """Test validate_bridge_config with valid configuration"""
        valid_config = {
            'name': 'Test Bridge',
            'chains': [1, 2],
            'contract_address': '0x1234567890123456789012345678901234567890',
            'supported_tokens': ['TEST']
        }
        assert validate_bridge_config('test_bridge', valid_config) is True
       
    def test_validate_bridge_config_invalid(self):
        """Test validate_bridge_config with invalid configuration"""
        invalid_config = {
            'name': 'Test Bridge',
            'chains': [1, 2],
            # Missing contract_address
            'supported_tokens': ['TEST']
        }
        assert validate_bridge_config('test_bridge', invalid_config) is False
       
    def test_get_bridge_config_valid(self):
        """Test get_bridge_config with valid bridge name"""
        bridge_name = 'test_bridge'
        config = get_bridge_config(bridge_name)
        assert isinstance(config, dict)
        assert 'name' in config
        assert 'chains' in config
        assert 'contract_address' in config
        assert 'supported_tokens' in config
        
    def test_get_bridge_config_invalid(self):
        """Test get_bridge_config with invalid bridge name"""
        with pytest.raises(ChainConfigError):
            get_bridge_config('invalid_bridge')

class TestTokenConfig:
    """Test cases for token configuration functionality"""
    
    def test_validate_token_config_valid(self):
        """Test validate_token_config with valid configuration"""
        valid_config = {
            'symbol': 'TEST',
            'name': 'Test Token',
            'decimals': 18,
            'chain_addresses': {
                1: '0x1234567890123456789012345678901234567890'
            }
        }
        assert validate_token_config('TEST', valid_config) is True
       
    def test_validate_token_config_invalid(self):
        """Test validate_token_config with invalid configuration"""
        invalid_config = {
            'symbol': 'TEST',
            'name': 'Test Token',
            'decimals': 18
            # Missing chain_addresses
        }
        assert validate_token_config('TEST', invalid_config) is False
       
    def test_get_token_config_valid(self):
        """Test get_token_config with valid token symbol"""
        token_symbol = 'TEST'
        config = get_token_config(token_symbol)
        assert isinstance(config, dict)
        assert 'symbol' in config
        assert 'name' in config
        assert 'decimals' in config
        assert 'chain_addresses' in config
        
    def test_get_token_config_invalid(self):
        """Test get_token_config with invalid token symbol"""
        with pytest.raises(ChainConfigError):
            get_token_config('INVALID')