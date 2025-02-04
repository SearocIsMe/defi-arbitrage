import ccxt
import time
import os
import random
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from web3 import Web3

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

# MEV保护实现类
class MEVProtector:
    def __init__(self, config):
        self.w3 = Web3(Web3.HTTPProvider(config['rpc']))
        self.flashbots_rpc = FLASHBOTS_CONFIG['rpc']
        self.signer_key = FLASHBOTS_CONFIG['signer_key']
        self.account = self.w3.eth.account.from_key(self.signer_key)
        
        # 添加Flashbots中间件
        self.w3.middleware_onion.add(
            self.construct_flashbots_middleware()
        )

    def construct_flashbots_middleware(self):
        from flashbots import construct_flashbots_middleware
        return construct_flashbots_middleware(
            self.w3.eth,
            self.account
        )

    def get_optimal_gas_params(self):
        """获取动态Gas参数"""
        try:
            base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
            max_priority = self.w3.eth.max_priority_fee
            return {
                'maxFeePerGas': int(base_fee * 1.25),
                'maxPriorityFeePerGas': int(max_priority * 1.2),
                'type': '0x2'  # EIP-1559交易类型
            }
        except Exception as e:
            print(f"Error getting gas params: {e}")
            return None

    def protect_transaction(self, tx):
        """交易保护处理（防抢跑）"""
        try:
            # 添加随机数据防止交易哈希碰撞
            tx['data'] += hex(random.randint(0, 0xFFFF))[2:]
            signed_tx = self.account.sign_transaction(tx)
            return signed_tx.rawTransaction
        except Exception as e:
            print(f"Transaction protection failed: {e}")
            return None

    def simulate_bundle(self, raw_tx):
        """交易模拟检查"""
        from flashbots import FlashbotBundle
        bundle = FlashbotBundle([raw_tx])
        return self.w3.flashbots.simulate_bundle(bundle)

# 添加MEV保护配置
FLASHBOTS_CONFIG = {
    'rpc': 'https://relay.flashbots.net',
    'signer_key': os.getenv('FLASHBOTS_SIGNER_KEY')  # 从环境变量读取
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
        # 动态获取实时Gas价格并计算成本
        w3 = Web3(Web3.HTTPProvider(DEX_CONFIG['ethereum']['rpc']))
        gas_price = w3.eth.gas_price / 1e9  # 转换为Gwei
        gas_limit = 350000  # 包含跨链操作的新预估
        arbitrage_amount = 0.5  # 降低单次套利规模
        threshold = max(0.005, 0.002 + (gas_price * gas_limit / arbitrage_amount * 1e-9))  # 动态最低阈值
        
        if price < average_price * (1 - threshold):  
            print(f"Arbitrage opportunity detected! {exchange_name} price is below average by {(average_price - price)/average_price*100}%")
            
            # 初始化MEV保护
            mev_protector = MEVProtector(DEX_CONFIG['ethereum'])
            
            # 构建跨链套利交易
            arbitrage_tx = {
                'chainId': 1,
                'to': DEX_CONFIG['ethereum']['bridge'],
                'value': Web3.to_wei(0.1, 'ether'),
                'data': '0x',
                'gas': 350000
            }
            
            # 获取最优Gas参数
            gas_params = mev_protector.get_optimal_gas_params()
            if gas_params:
                arbitrage_tx.update(gas_params)
                
                # MEV保护处理
                protected_tx = mev_protector.protect_transaction(arbitrage_tx)
                if protected_tx:
                    # 交易模拟检查
                    simulation = mev_protector.simulate_bundle(protected_tx)
                    if simulation and simulation.get('success'):
                        print(f"Simulation success! Estimated profit: {simulation['profit']} ETH")
                        # 实际交易执行（需要用户确认）
                        # tx_hash = mev_protector.w3.eth.send_raw_transaction(protected_tx)
                        # print(f"Transaction sent: {tx_hash.hex()}")
                        return True
            
            print("Failed to execute protected arbitrage transaction")
            return False

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
            },
            'apiKey': os.getenv('DEX_API_KEY'),
            'secret': os.getenv('DEX_API_SECRET')
        })
    },
    'pancakeswap': {
        'class': ccxt.dex({
            'exchange': 'pancakeswap',
            'blockchain': 'bsc',
            'provider': {
                'url': 'https://bsc-dataseed.binance.org/',
                'chainId': 56
            },
            'apiKey': os.getenv('DEX_API_KEY'),
            'secret': os.getenv('DEX_API_SECRET')
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
    # 初始化DEX交易所（修正参数传递）
    for dex_name, config in DEX_EXCHANGES.items():
        exchanges[dex_name] = config['class']({
            'apiKey': os.getenv('DEX_API_KEY'),
            'secret': os.getenv('DEX_API_SECRET'),
            'options': config['class'].options
        })
    
    # 添加CEX交易所
    for exchange_id in exchange_ids:
        exchanges[exchange_id] = getattr(ccxt, exchange_id)(configurations[exchange_id])
    
    main_loop()
