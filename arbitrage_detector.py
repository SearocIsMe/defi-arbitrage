import ccxt
import time

# 初始化选定的交易对和交易所列表
symbol = 'BTC/ETH'  # 示例交易对，实际应用中需要根据需求选择
exchange_ids = ['binance', 'huobipro', 'okex']  # 示例交易所ID，需替换为真实的API密钥和Secrets

# 加载各个交易所的API配置
configurations = {
    'binance': {
        'apiKey': 'your_binance_api_key',
        'secretKey': 'your_binance_secret_key'
    },
    'huobipro': {
        'apiKey': 'your_huobipro_api_key',
        'secretKey': 'your_huobipro_secret_key'
    },
    'okex': {
        'apiKey': 'your_okex_api_key',
        'secretKey': 'your_okex_secret_key'
    }
}

# 初始化交易所对象
exchanges = {}
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
        if price < average_price * 0.95:  # 示例阈值，实际可根据策略调整
            print(f"Arbitrage opportunity detected! {exchange_name} price is below average by {(average_price - price)/average_price*100}%")
            return True

    return False

# 主循环，定期检测套利机会
while True:
    print("Checking for arbitrage opportunities...")
    detect_arbitrage_opportunity()
    time.sleep(60)  # 每分钟检查一次，可根据需求调整频率

