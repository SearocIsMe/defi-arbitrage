import requests

def get_top_tokens():
    # 使用CoinMarketCap API获取所有代币数据
    url = "https://api.coinmarketcap.com/v2/ticker/?limit=100"
    response = requests.get(url)
    data = response.json()

    tokens = []
    for coin in data["data"]:
        if coin["symbol"] != "ETH":  # 排除以太坊本身
            tokens.append({
                "symbol": coin["symbol"],
                "volume_24h": float(coin["quotes"]["USD"]["volume_24hr"]),
            })

    # 按交易量排序并选择前50名
    tokens.sort(key=lambda x: -x["volume_24h"])
    top_tokens = tokens[:50]

    return [token["symbol"] for token in top_tokens]

# 使用示例：
top_tokens = get_top_tokens()
print(f"Top 50 tokens by 24h volume: {top_tokens}")
