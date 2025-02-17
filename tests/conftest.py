import pytest
import os
import sys
import logging

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def pytest_configure(config):
    """
    Configure pytest settings and logging
    """
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tests/test_logs/pytest.log')
        ]
    )

    # Create test logs directory if it doesn't exist
    os.makedirs('tests/test_logs', exist_ok=True)

def pytest_addoption(parser):
    """
    Add custom command-line options for pytest
    """
    parser.addoption(
        "--runslow", 
        action="store_true", 
        default=False, 
        help="run slow tests"
    )
    parser.addoption(
        "--env", 
        action="store", 
        default="test", 
        help="environment to run tests in"
    )

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection based on custom options
    """
    # Skip slow tests by default
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

@pytest.fixture(scope="session")
def test_environment(request):
    """
    Fixture to manage test environment configuration
    """
    env = request.config.getoption("--env")
    
    # Load environment-specific configuration
    if env == "test":
        # Load test environment variables or configuration
        os.environ['TESTING'] = 'true'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    elif env == "staging":
        # Load staging environment configuration
        pass
    
    # Cleanup after tests
    def fin():
        # Reset or cleanup test environment
        if 'TESTING' in os.environ:
            del os.environ['TESTING']
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
    
    request.addfinalizer(fin)
    return env

@pytest.fixture(scope="function")
def mock_exchanges():
    """
    Fixture to provide mock exchanges for testing
    """
    from unittest.mock import MagicMock
    
    # Create mock exchanges with predefined behaviors
    exchanges = {
        'binance': MagicMock(),
        'okx': MagicMock(),
        'coinbase': MagicMock()
    }
    
    # Configure default mock behaviors
    exchanges['binance'].fetch_ticker.return_value = {'bid': 2000}
    exchanges['okx'].fetch_ticker.return_value = {'bid': 1950}
    exchanges['coinbase'].fetch_ticker.return_value = {'bid': 1975}
    
    return exchanges

@pytest.fixture(scope="function")
def mock_web3_provider():
    """
    Fixture to provide a mock Web3 provider
    """
    from unittest.mock import MagicMock
    from web3 import Web3
    
    # Create a mock Web3 provider
    mock_provider = MagicMock()
    mock_w3 = Web3(mock_provider)
    
    # Configure basic mock behaviors
    mock_w3.is_connected.return_value = True
    mock_w3.eth.get_block.return_value = {
        'baseFeePerGas': Web3.to_wei(20, 'gwei')
    }
    
    return mock_w3

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Add custom summary information to pytest output
    """
    # Print additional test run information
    terminalreporter.write_line("")
    terminalreporter.write_line("Test Environment Summary:")
    terminalreporter.write_line(f"Python Version: {sys.version}")
    terminalreporter.write_line(f"Test Environment: {config.getoption('--env')}")