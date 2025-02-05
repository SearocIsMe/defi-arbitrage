from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel

# Redis配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_KEY_PREFIX = 'arbitrage:'
REDIS_EXPIRY = 360000  # 100小时过期

# 初始化FastAPI
app = FastAPI(
    title="DeFi套利机会API",
    description="提供实时DEX/CEX套利机会数据",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化Redis连接
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

class ArbitrageOpportunity(BaseModel):
    """套利机会数据模型"""
    id: str
    timestamp: datetime
    symbol: str
    source_exchange: str
    target_exchange: str
    price_difference: float
    estimated_profit: float
    gas_cost: float
    transaction_details: Dict
    status: str

@app.get("/")
async def root():
    return {"status": "running", "service": "DeFi Arbitrage API"}

@app.get("/opportunities", response_model=List[ArbitrageOpportunity])
async def get_arbitrage_opportunities(
    symbol: Optional[str] = None,
    min_profit: Optional[float] = None,
    limit: int = 10
):
    """
    获取套利机会列表
    - symbol: 可选,筛选特定交易对
    - min_profit: 可选,最小预期收益
    - limit: 返回结果数量限制
    """
    try:
        # 获取所有套利机会键
        keys = redis_client.keys(f"{REDIS_KEY_PREFIX}*")
        opportunities = []
        
        for key in keys:
            data = redis_client.get(key)
            if data:
                opp = json.loads(data)
                
                # 应用过滤条件
                if symbol and opp['symbol'] != symbol:
                    continue
                if min_profit and opp['estimated_profit'] < min_profit:
                    continue
                    
                opportunities.append(ArbitrageOpportunity(**opp))
                
        # 按预期收益排序
        opportunities.sort(key=lambda x: x.estimated_profit, reverse=True)
        return opportunities[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/opportunities/{opportunity_id}", response_model=ArbitrageOpportunity)
async def get_arbitrage_opportunity(opportunity_id: str):
    """获取特定套利机会详情"""
    try:
        data = redis_client.get(f"{REDIS_KEY_PREFIX}{opportunity_id}")
        if not data:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return ArbitrageOpportunity(**json.loads(data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/symbols")
async def get_top_symbols(limit: int = 20):
    """获取交易量前N的交易对"""
    try:
        symbols_data = redis_client.get("top_trading_pairs")
        if not symbols_data:
            return {"error": "No symbol data available"}
        symbols = json.loads(symbols_data)
        return {"symbols": symbols[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_arbitrage_stats():
    """获取套利统计信息"""
    try:
        total_opportunities = len(redis_client.keys(f"{REDIS_KEY_PREFIX}*"))
        
        # 计算平均收益
        total_profit = 0
        opportunity_count = 0
        
        for key in redis_client.keys(f"{REDIS_KEY_PREFIX}*"):
            data = redis_client.get(key)
            if data:
                opp = json.loads(data)
                total_profit += opp['estimated_profit']
                opportunity_count += 1
        
        avg_profit = total_profit / opportunity_count if opportunity_count > 0 else 0
        
        return {
            "total_opportunities": total_opportunities,
            "average_profit": avg_profit,
            "last_update": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def store_arbitrage_opportunity(
    symbol: str,
    source_exchange: str,
    target_exchange: str,
    price_difference: float,
    estimated_profit: float,
    gas_cost: float,
    transaction_details: Dict,
    status: str = "pending"
) -> str:
    """
    存储套利机会到Redis
    返回: opportunity_id
    """
    opportunity_id = f"{datetime.now().timestamp()}-{symbol}-{source_exchange}-{target_exchange}"
    
    opportunity_data = {
        "id": opportunity_id,
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "source_exchange": source_exchange,
        "target_exchange": target_exchange,
        "price_difference": price_difference,
        "estimated_profit": estimated_profit,
        "gas_cost": gas_cost,
        "transaction_details": transaction_details,
        "status": status
    }
    
    redis_key = f"{REDIS_KEY_PREFIX}{opportunity_id}"
    redis_client.setex(
        redis_key,
        REDIS_EXPIRY,
        json.dumps(opportunity_data)
    )
    
    return opportunity_id

def store_top_trading_pairs(pairs: List[str]):
    """存储交易量前N的交易对"""
    redis_client.setex(
        "top_trading_pairs",
        REDIS_EXPIRY,
        json.dumps(pairs)
    )
