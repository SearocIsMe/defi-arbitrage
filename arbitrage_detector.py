import ccxt
import time

# 跨链套利配置
DEX_CONFIG = {
    'ethereum': {
        'rpc': f"https://mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}",
        'dex': {
            'uniswap_v3': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
            'sushiswap': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
        },
        'bridge': '0x3F4A885ed8d9cDF10f3349357E3b243F3695b24A'  # LayerZero主网桥接地址
    },
    'arbitrum': {
        'rpc': 'https://arb1.arbitrum.io/rpc',
        'dex': {
            'uniswap_v3': '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'
        }
    }
}

# 添加MEV保护配置
FLASHBOTS_CONFIG = {
    'rpc': 'https://relay.flashbots.net',
    'signer_key': 'YOUR_FLASHBOTS_SIGNER_KEY'
}

# 初始化交易参数
symbol = 'WETH/USDC'  # 使用主流稳定币交易对
exchange_ids = ['binance', 'okx']  # 修正交易所名称拼写错误

# 加载交易所API配置
configurations = {
    'binance': {
        'apiKey': 'your_binance_api_key',
        'secretKey': 'your_binance_secret_key',
        'options': {'adjustForTimeDifference': True}
    },
    'okx': {
        'apiKey': 'your_okx_api_key',  # 确保使用OKX官方API名称
        'secret': 'your_okx_secret_key',  # 修正参数名为secret
        'password': 'your_trade_password',  # 添加OKX必需的交易密码
        'options': {
            'adjustForTimeDifference': True,
            'recvWindow': 10000
        }
    }
}

# 初始化交易所对象
exchanges = {}
web3_instances = {}
for exchange_id in exchange_ids:
    exchanges[exchange_id] = getattr(ccxt, exchange_id)(configurations[exchange_id])

def get_ticker_price(exchange, symbol):
    """
    获取指定交易所和交易对的当前价格。
    """
    try:
        return exchange.fetch_ticker(symbol)['bid']
    except Exception as e:
        print(f"Error fetching price from {exchange.name}: {e}")
        return None

def detect_arbitrage_opportunity():
    """
    检测套利机会，比较不同交易所的交易对价格。
    """
    prices = {}
    for exchange_id in exchanges:
        exchange = exchanges[exchange_id]
        price = get_ticker_price(exchange, symbol)
        if price is not None:
            prices[exchange.name] = price
        else:
            continue  # 跳过无法获取价格的交易所

    if not prices:
        print("No valid price data available.")
        return False

    # 计算平均价格
    average_price = sum(prices.values()) / len(prices)
    print(f"Current prices: {prices}")
    print(f"Average price: {average_price}")

    # 检查是否有交易所的价格显著低于平均价（套利机会）
    for exchange_name, price in prices.items():
        # 动态计算套利阈值（基础0.3% + Gas成本补偿）
        gas_price = 30  # 默认30 Gwei
        gas_limit = 250000  # 预估Gas消耗量
        arbitrage_amount = 1  # 套利数量(ETH)
        threshold = 0.003 + (gas_price * gas_limit / arbitrage_amount * 1e-9)  # 转换单位
        
        if price < average_price * (1 - threshold):  
            print(f"Arbitrage opportunity detected! {exchange_name} price is below average by {(average_price - price)/average_price*100}%")
            return True

    return False

# 添加DEX交易所支持
DEX_EXCHANGES = {
    'uniswap': {
        'class': ccxt.dex({
            'exchange': 'uniswap',
            'blockchain': 'ethereum',
            'provider': {
                'url': DEX_CONFIG['ethereum']['rpc'],
                'chainId': 1
            }
        })
    },
    'pancakeswap': {
        'class': ccxt.dex({
            'exchange': 'pancakeswap',
            'blockchain': 'bsc',
            'provider': {
                'url': 'https://bsc-dataseed.binance.org/',
                'chainId': 56
            }
        })
    }
}

def get_dex_price(dex, symbol):
    """获取DEX交易所价格"""
    try:
        market = dex.load_markets()[symbol]
        orderbook = dex.fetch_order_book(market['symbol'])
        return orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
    except Exception as e:
        print(f"Error fetching DEX price: {e}")
        return None

def fetch_top_pairs():
    """通过The Graph获取交易量前50的交易对"""
    query = """
    {
        pairs(first: 50, orderBy: volumeUSD, orderDirection: desc) {
            id
            token0 { symbol }
            token1 { symbol }
            volumeUSD
        }
    }
    """
    try:
        client = Client(transport=RequestsHTTPTransport(url="https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"))
        result = client.execute(gql(query))
        return [f"{pair['token0']['symbol']}/{pair['token1']['symbol']}" for pair in result['pairs']]
    except Exception as e:
        print(f"Error fetching top pairs: {e}")
        return ['WETH/USDC', 'WBTC/USDT']  # 默认交易对

def main_loop():
    """带信号处理的主循环"""
    print("Arbitrage bot started. Press Ctrl+C to exit.")
    try:
        while True:
            global symbol
            symbol = fetch_top_pairs()[0]  # 使用交易量最大的交易对
            print(f"Checking {symbol} opportunities...")
            detect_arbitrage_opportunity()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nGracefully shutting down...")
        # 执行清理操作
        for exchange in exchanges.values():
            if hasattr(exchange, 'close'):
                exchange.close()

if __name__ == "__main__":
    # 初始化DEX交易所
    for dex_name, config in DEX_EXCHANGES.items():
        exchanges[dex_name] = config['class'](config['params'])
    
    # 添加CEX交易所
    for exchange_id in exchange_ids:
        exchanges[exchange_id] = getattr(ccxt, exchange_id)(configurations[exchange_id])
    
    main_loop()
