import aiohttp
import asyncio
import json
from typing import List, Dict
from logger_config import get_logger

logger = get_logger()

class DexLiquidityManager:
    """管理DEX流动性数据获取和分析"""
    
    def __init__(self):
        # Uniswap V3 Graph API
        self.uniswap_url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        # SushiSwap Graph API
        self.sushiswap_url = "https://api.thegraph.com/subgraphs/name/sushiswap/exchange"
        # PancakeSwap Graph API
        self.pancakeswap_url = "https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v2"

    async def fetch_graph_data(self, url: str, query: str) -> Dict:
        """从Graph API获取数据"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={'query': query}) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {})
                    else:
                        logger.error(f"Error fetching data from {url}: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error in fetch_graph_data: {e}")
            return {}

    async def get_uniswap_top_pairs(self) -> List[Dict]:
        """获取Uniswap V3前30的交易对"""
        query = """
        {
          pools(
            first: 30,
            orderBy: totalValueLockedUSD,
            orderDirection: desc
          ) {
            id
            token0 {
              symbol
              decimals
            }
            token1 {
              symbol
              decimals
            }
            totalValueLockedUSD
            volumeUSD
          }
        }
        """
        data = await self.fetch_graph_data(self.uniswap_url, query)
        return [
            {
                'dex': 'Uniswap V3',
                'pair': f"{pool['token0']['symbol']}/{pool['token1']['symbol']}",
                'tvl': float(pool['totalValueLockedUSD']),
                'volume': float(pool['volumeUSD'])
            }
            for pool in data.get('pools', [])
        ]

    async def get_sushiswap_top_pairs(self) -> List[Dict]:
        """获取SushiSwap前30的交易对"""
        query = """
        {
          pairs(
            first: 30,
            orderBy: reserveUSD,
            orderDirection: desc
          ) {
            id
            token0 {
              symbol
            }
            token1 {
              symbol
            }
            reserveUSD
            volumeUSD
          }
        }
        """
        data = await self.fetch_graph_data(self.sushiswap_url, query)
        return [
            {
                'dex': 'SushiSwap',
                'pair': f"{pair['token0']['symbol']}/{pair['token1']['symbol']}",
                'tvl': float(pair['reserveUSD']),
                'volume': float(pair['volumeUSD'])
            }
            for pair in data.get('pairs', [])
        ]

    async def get_pancakeswap_top_pairs(self) -> List[Dict]:
        """获取PancakeSwap前30的交易对"""
        query = """
        {
          pairs(
            first: 30,
            orderBy: reserveUSD,
            orderDirection: desc
          ) {
            id
            token0 {
              symbol
            }
            token1 {
              symbol
            }
            reserveUSD
            volumeUSD
          }
        }
        """
        data = await self.fetch_graph_data(self.pancakeswap_url, query)
        return [
            {
                'dex': 'PancakeSwap',
                'pair': f"{pair['token0']['symbol']}/{pair['token1']['symbol']}",
                'tvl': float(pair['reserveUSD']),
                'volume': float(pair['volumeUSD'])
            }
            for pair in data.get('pairs', [])
        ]

    def merge_and_sort_pairs(self, pairs_list: List[List[Dict]]) -> List[str]:
        """合并和排序所有DEX的交易对"""
        # 合并所有交易对
        all_pairs = []
        for pairs in pairs_list:
            all_pairs.extend(pairs)

        # 按TVL和交易量排序
        sorted_pairs = sorted(
            all_pairs,
            key=lambda x: (x['tvl'] * 0.7 + x['volume'] * 0.3),
            reverse=True
        )

        # 提取唯一的交易对符号
        unique_pairs = []
        seen_pairs = set()
        for pair in sorted_pairs:
            if pair['pair'] not in seen_pairs:
                seen_pairs.add(pair['pair'])
                unique_pairs.append(pair['pair'])

        return unique_pairs[:30]  # 返回前30个唯一交易对

    async def get_top_trading_pairs(self) -> List[str]:
        """获取所有DEX的前30个交易对"""
        try:
            # 并行获取所有DEX的数据
            tasks = [
                self.get_uniswap_top_pairs(),
                self.get_sushiswap_top_pairs(),
                self.get_pancakeswap_top_pairs()
            ]
            results = await asyncio.gather(*tasks)
            
            # 合并和排序交易对
            top_pairs = self.merge_and_sort_pairs(results)
            logger.info(f"Successfully fetched top {len(top_pairs)} trading pairs")
            return top_pairs

        except Exception as e:
            logger.error(f"Error in get_top_trading_pairs: {e}")
            # 返回默认交易对
            return ['WETH/USDC', 'WBTC/USDT', 'ETH/USDT']

async def update_trading_pairs(redis_client) -> None:
    """更新Redis中的交易对数据"""
    try:
        dex_manager = DexLiquidityManager()
        top_pairs = await dex_manager.get_top_trading_pairs()
        
        # 存储到Redis
        redis_client.setex(
            "top_trading_pairs",
            360000,  # 100小时过期
            json.dumps(top_pairs)
        )
        logger.info(f"Updated top trading pairs in Redis: {top_pairs}")
        
    except Exception as e:
        logger.error(f"Error updating trading pairs: {e}")
