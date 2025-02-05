import ccxt
import time
import os
import random
from datetime import datetime
from gql import gql, Client
from logger_config import get_logger
from api_service import store_arbitrage_opportunity, store_top_trading_pairs

# 初始化logger
logger = get_logger()
from gql.transport.requests import RequestsHTTPTransport
from web3 import Web3
from decimal import Decimal
from multi_source_gas_manager import GasManager
from fund_manager import FundManager, Position

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
            logger.error(f"Error getting gas params: {e}", exc_info=True)
            return None

    def protect_transaction(self, tx):
        """交易保护处理(防抢跑)"""
        try:
            # 添加随机数据防止交易哈希碰撞
            tx['data'] += hex(random.randint(0, 0xFFFF))[2:]
            signed_tx = self.account.sign_transaction(tx)
            return signed_tx.rawTransaction
        except Exception as e:
            logger.error(f"Transaction protection failed: {e}", exc_info=True)
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
        logger.error(f"Error fetching price from {exchange.name}: {e}", exc_info=True)
        return None

async def detect_arbitrage_opportunity(gas_manager: GasManager, fund_manager: FundManager, wallet_address: str):
    """
    检测套利机会,比较不同交易所的交易对价格。
    增加了gas价格和资金管理的优化。
    返回: (bool, str) - (是否发现机会, 机会ID)
    """
    prices = {}
    for exchange_id in exchanges:
        exchange = exchanges[exchange_id]
        price = get_ticker_price(exchange, symbol)
        if price is not None:
            prices[exchange.name] = Decimal(str(price))
        else:
            continue

    if not prices:
        logger.warning("No valid price data available.")
        return False, None

    # 计算平均价格和价格差异
    average_price = sum(prices.values()) / Decimal(str(len(prices)))
    price_differences = {
        exchange: (average_price - price) / average_price * 100 
        for exchange, price in prices.items()
    }
    logger.info(f"Current prices: {prices}")
    logger.info(f"Price differences: {price_differences}%")

    # 获取钱包余额和gas价格
    balance = await fund_manager.get_wallet_balance(wallet_address)
    gas_limit = 350000  # 包含跨链操作的预估
    gas_cost = Decimal(str(gas_manager.estimate_transaction_gas_cost(gas_limit)))
    
    # 检查gas价格是否合理
    if not gas_manager.is_gas_price_reasonable():
        logger.warning("Gas price too high, skipping arbitrage")
        return False, None
        
    # 分析gas价格趋势
    trend = gas_manager.get_gas_price_trend()
    if trend == 'increasing':
        logger.info("Gas price trend is increasing, waiting for better conditions")
        return False, None
    
    # 获取优化后的gas价格
    gas_prices = gas_manager.get_optimal_gas_price()
    logger.info(f"Current optimized gas prices: {gas_prices}")

    # 检查是否有交易所的价格显著低于平均价(套利机会)
    for exchange_name, price in prices.items():
        # 计算动态阈值(考虑gas成本)
        threshold = max(
            Decimal('0.005'),
            Decimal('0.002') + (gas_cost / Decimal('0.5'))
        )
        
        if price < average_price * (Decimal('1') - threshold):
            price_diff_percentage = (average_price - price)/average_price*100
            logger.info(f"Arbitrage opportunity detected! {exchange_name} price is below average by {price_diff_percentage}%")
            
            # 记录交易详情
            tx_details = {
                'source_price': float(price),
                'target_price': float(average_price),
                'price_difference_percentage': float(price_diff_percentage),
                'timestamp': datetime.now().isoformat()
            }
            logger.debug(f"Transaction details: {tx_details}")
            
            # 计算最大仓位大小(考虑杠杆)
            position_params = fund_manager.calculate_max_position_size(
                balance=balance,
                current_price=price,
                leverage=Decimal('2'),  # 使用2倍杠杆
                gas_limit=gas_limit
            )
            
            if position_params['max_size'] <= 0:
                logger.warning(f"Insufficient balance for arbitrage. Required: {position_params['required_margin']}, Available: {balance}")
                continue
                
            # 创建头寸对象
            position = Position(
                size=position_params['max_size'],
                leverage=Decimal('2'),
                entry_price=price,
                liquidation_price=position_params['liquidation_price'],
                margin=position_params['required_margin']
            )
            
            # 检查预期收益是否合理
            expected_profit = (average_price - price) * position.size
            if expected_profit <= gas_cost:
                logger.warning(f"Expected profit ({float(expected_profit)}) too low compared to gas cost ({float(gas_cost)})")
                continue
            
            # 初始化MEV保护
            mev_protector = MEVProtector(DEX_CONFIG['ethereum'])
            
            # 构建跨链套利交易
            arbitrage_tx = {
                'chainId': 1,
                'to': DEX_CONFIG['ethereum']['bridge'],
                'value': Web3.to_wei(str(position.size), 'ether'),
                'data': '0x',
                'gas': gas_limit
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
                        logger.info(f"Simulation success! Estimated profit: {simulation['profit']} ETH")
                        # 存储套利机会
                        opportunity_id = store_arbitrage_opportunity(
                            symbol=symbol,
                            source_exchange=exchange_name,
                            target_exchange="Average",
                            price_difference=float(price_diff_percentage),
                            estimated_profit=float(expected_profit),
                            gas_cost=float(gas_cost),
                            transaction_details={
                                **tx_details,
                                'arbitrage_tx': arbitrage_tx,
                                'gas_params': gas_params,
                                'position': position.__dict__
                            },
                            status="simulated"
                        )
                        logger.info(f"Stored arbitrage opportunity with ID: {opportunity_id}")
                        return True, opportunity_id
            
            logger.error("Failed to execute protected arbitrage transaction")
            return False, None

    return False, None

# DEX接口配置
DEX_EXCHANGES = {
    'uniswap': {
        'router': DEX_CONFIG['ethereum']['dex']['uniswap_v3'],
        'chain_id': 1,
        'provider': Web3(Web3.HTTPProvider(DEX_CONFIG['ethereum']['rpc'])),
        'abi': [
            # Uniswap V3 Router ABI
            {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"}],"name":"exactInput","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"},
            {"inputs":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint256","name":"amountIn","type":"uint256"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}
        ]
    },
    'pancakeswap': {
        'router': '0x10ED43C718714eb63d5aA57B78B54704E256024E',  # PancakeSwap Router v2
        'chain_id': 56,
        'provider': Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/')),
        'abi': [
            # PancakeSwap Router ABI
            {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}
        ]
    }
}

def get_dex_price(dex_name, token_in, token_out, amount_in=Web3.to_wei(1, 'ether')):
    """
    获取DEX交易所价格
    @param dex_name: DEX名称
    @param token_in: 输入代币地址
    @param token_out: 输出代币地址
    @param amount_in: 输入金额(默认1 ETH)
    @return: 输出金额
    """
    try:
        dex = DEX_EXCHANGES[dex_name]
        contract = dex['provider'].eth.contract(
            address=dex['router'],
            abi=dex['abi']
        )
        
        if dex_name == 'uniswap':
            # Uniswap V3使用quoteExactInputSingle
            amount_out = contract.functions.quoteExactInputSingle(
                token_in,
                token_out,
                3000,  # 0.3% fee tier
                amount_in
            ).call()
        else:
            # PancakeSwap使用getAmountsOut
            amounts = contract.functions.getAmountsOut(
                amount_in,
                [token_in, token_out]
            ).call()
            amount_out = amounts[1]
            
        return Web3.from_wei(amount_out, 'ether')
    except Exception as e:
        logger.error(f"Error fetching DEX price from {dex_name}: {e}", exc_info=True)
        return None

async def fetch_top_pairs():
    """获取并更新交易量前30的交易对"""
    try:
        from dex_liquidity_manager import DexLiquidityManager
        dex_manager = DexLiquidityManager()
        pairs = await dex_manager.get_top_trading_pairs()
        # 存储到Redis
        store_top_trading_pairs(pairs)
        return pairs
    except Exception as e:
        logger.error(f"Error fetching top pairs: {e}", exc_info=True)
        return ['WETH/USDC', 'WBTC/USDT']  # 默认交易对

async def main_loop(gas_manager: GasManager, fund_manager: FundManager, wallet_address: str):
    """带信号处理的主循环"""
    logger.info("Arbitrage bot started. Press Ctrl+C to exit.")
    
    # 创建停止标志
    stop_flag = asyncio.Event()
    
    # 设置信号处理
    def signal_handler():
        logger.info("Gracefully shutting down...")
        stop_flag.set()
    
    # 注册信号处理器
    loop = asyncio.get_running_loop()
    for signal_name in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(
                getattr(signal, signal_name),
                signal_handler
            )
        except NotImplementedError:
            # Windows不支持SIGTERM
            pass
    
    try:
        while not stop_flag.is_set():
            # 获取并更新交易对列表
            pairs = await fetch_top_pairs()
            if not pairs:
                logger.warning("No trading pairs available, using default")
                pairs = ['WETH/USDC']
            
            # 遍历所有交易对检查套利机会
            for pair in pairs:
                if stop_flag.is_set():
                    break
                    
                global symbol
                symbol = pair
                logger.info(f"Checking {symbol} opportunities...")
                success, opp_id = await detect_arbitrage_opportunity(gas_manager, fund_manager, wallet_address)
                if success:
                    logger.info(f"Stored arbitrage opportunity with ID: {opp_id}")
                
                # 每个交易对检查间隔2秒
                try:
                    await asyncio.wait_for(stop_flag.wait(), timeout=2)
                except asyncio.TimeoutError:
                    continue
            
            # 完成一轮检查后等待58秒再开始下一轮
            try:
                await asyncio.wait_for(stop_flag.wait(), timeout=58)
            except asyncio.TimeoutError:
                continue
    finally:
        # 执行清理操作
        logger.info("Cleaning up resources...")
        for exchange in exchanges.values():
            if hasattr(exchange, 'close'):
                await exchange.close() if asyncio.iscoroutinefunction(exchange.close) else exchange.close()
        
        # 清理其他资源
        await fund_manager.cleanup() if hasattr(fund_manager, 'cleanup') and asyncio.iscoroutinefunction(fund_manager.cleanup) else None
        await gas_manager.cleanup() if hasattr(gas_manager, 'cleanup') and asyncio.iscoroutinefunction(gas_manager.cleanup) else None

if __name__ == "__main__":
    # 导入所需模块
    import asyncio
    import signal
    
    # 初始化gas管理器和资金管理器
    w3 = Web3(Web3.HTTPProvider(DEX_CONFIG['ethereum']['rpc']))
    gas_manager = GasManager()
    fund_manager = FundManager(w3, gas_manager)
    wallet_address = os.getenv('WALLET_ADDRESS')
    
    if not wallet_address:
        logger.error("WALLET_ADDRESS environment variable not set")
        exit(1)
    
    # 初始化DEX合约
    for dex_name, config in DEX_EXCHANGES.items():
        try:
            contract = config['provider'].eth.contract(
                address=config['router'],
                abi=config['abi']
            )
            exchanges[dex_name] = {
                'contract': contract,
                'provider': config['provider']
            }
            logger.info(f"Initialized {dex_name} contract at {config['router']}")
        except Exception as e:
            logger.error(f"Failed to initialize {dex_name}: {e}", exc_info=True)
    
    # 添加CEX交易所
    for exchange_id in exchange_ids:
        exchanges[exchange_id] = getattr(ccxt, exchange_id)(configurations[exchange_id])
    
    try:
        # 启动主循环
        asyncio.run(main_loop(gas_manager, fund_manager, wallet_address))
    except KeyboardInterrupt:
        logger.info("Shutdown complete.")
