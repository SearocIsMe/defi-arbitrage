from setuptools import setup, find_packages

setup(
    name='defi-arbitrage',
    version='0.1.0',
    description='Advanced DeFi Arbitrage Bot',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/defi-arbitrage',
    packages=find_packages(exclude=['tests*']),
    install_requires=[
        # Core dependencies
        'web3>=5.30.0',
        'python-dotenv>=0.19.0',
        'ccxt>=2.0.0',
        'asyncio>=3.4.3',
        'structlog>=21.1.0',
        
        # Blockchain and Crypto
        'eth-account>=0.5.9',
        'multicall>=0.1.0',
        
        # Data Processing
        'pandas>=1.3.0',
        'numpy>=1.21.0',
        
        # Error Tracking and Monitoring
        'sentry-sdk>=1.3.0',
        'prometheus-client>=0.12.0',
        
        # Configuration and Validation
        'jsonschema>=3.2.0',
        'pyyaml>=5.4.0',
        
        # Optional Advanced Features
        'ta-lib>=0.4.20',
        'flashbots>=0.4.0'
    ],
    extras_require={
        'dev': [
            'pytest>=6.2.0',
            'pytest-asyncio>=0.15.0',
            'mypy>=0.910',
            'black>=21.5b1',
            'flake8>=3.9.0'
        ],
        'monitoring': [
            'prometheus-client>=0.12.0',
            'grafana-api>=0.10.0'
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Office/Business :: Financial :: Investment'
    ],
    keywords='defi arbitrage cryptocurrency trading bot',
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'defi-arbitrage=arbitrage_detector:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/defi-arbitrage/issues',
        'Source': 'https://github.com/yourusername/defi-arbitrage',
    },
)