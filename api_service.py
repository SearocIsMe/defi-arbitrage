from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import redis
import json
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum

from fund_manager import FundManager, GasManager
from logger_config import get_logger

# Redis配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_KEY_PREFIX = 'arbitrage:'
REDIS_EXPIRY = 360000  # 100小时过期

logger = get_logger("api_service")

class ArbitrageStatus(str, Enum):
    """套利状态枚举"""
    PENDING = "pending"
    SIMULATED = "simulated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

# 初始化FastAPI
app = FastAPI(
    title="DeFi套利机会API",
    description="""
    提供实时DEX/CEX套利机会数据和监控接口。
    
    主要功能:
    * 获取实时套利机会
    * 查询交易对数据
    * 监控系统状态
    * 获取历史统计
    """,
    version="1.0.0",
    docs_url=None,
    redoc_url=None
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="DeFi套利系统API",
        version="1.0.0",
        description="跨链套利自动化交易系统API文档",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DeFi套利系统API文档",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
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
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    redis_client.ping()  # Test connection
    logger.info("Successfully connected to Redis")
except redis.ConnectionError as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    redis_client = None

class ArbitrageOpportunity(BaseModel):
    """套利机会数据模型"""
    id: str = Field(..., description="套利机会唯一标识")
    timestamp: datetime = Field(..., description="创建时间")
    symbol: str = Field(..., description="交易对符号")
    source_exchange: str = Field(..., description="源交易所")
    target_exchange: str = Field(..., description="目标交易所")
    price_difference: float = Field(..., description="价格差异百分比")
    estimated_profit: float = Field(..., description="预估收益(ETH)")
    gas_cost: float = Field(..., description="Gas成本(ETH)")
    transaction_details: Dict = Field(..., description="交易详情")
    status: ArbitrageStatus = Field(..., description="当前状态")

    class Config:
        schema_extra = {
            "example": {
                "id": "1643673600-WETH-USDC-binance-uniswap",
                "timestamp": "2024-02-05T12:00:00",
                "symbol": "WETH/USDC",
                "source_exchange": "Binance",
                "target_exchange": "Uniswap",
                "price_difference": 0.8,
                "estimated_profit": 0.05,
                "gas_cost": 0.02,
                "transaction_details": {
                    "source_price": 2000.0,
                    "target_price": 2016.0,
                    "position_size": 1.0
                },
                "status": "simulated"
            }
        }

class WalletResponse(BaseModel):
    """钱包创建响应模型"""
    address: str = Field(..., description="钱包地址")
    private_key: str = Field(..., description="钱包私钥 (仅用于演示)")
    message: str = Field(..., description="安全提示信息")

@app.get("/")
async def root():
    return {"status": "running", "service": "DeFi Arbitrage API"}

@app.get(
    "/opportunities", 
    response_model=List[ArbitrageOpportunity],
    summary="获取套利机会列表",
    description="获取当前可用的套利机会列表,支持按交易对和最小收益过滤"
)
async def get_arbitrage_opportunities(
    symbol: Optional[str] = Query(None, description="交易对符号,例如: WETH/USDC"),
    min_profit: Optional[float] = Query(None, description="最小预期收益(ETH)"),
    status: Optional[ArbitrageStatus] = Query(None, description="套利状态过滤"),
    limit: int = Query(10, description="返回结果数量限制", ge=1, le=100)
):
    """
    获取套利机会列表
    - symbol: 可选,筛选特定交易对
    - min_profit: 可选,最小预期收益
    - limit: 返回结果数量限制
    """
    opportunities = []
    
    if not redis_client:
        logger.error("Redis client is not initialized")
        return opportunities

    try:
        keys = redis_client.keys(f"{REDIS_KEY_PREFIX}*")
    except redis.RedisError as e:
        logger.error(f"Failed to fetch keys from Redis: {str(e)}")
        return opportunities

    for key in keys:
        try:
            data = redis_client.get(key)
            if data:
                opp = json.loads(data)
                
                # 应用过滤条件
                if symbol and opp['symbol'] != symbol:
                    continue
                if min_profit and opp['estimated_profit'] < min_profit:
                    continue
                    
                opportunities.append(ArbitrageOpportunity(**opp))
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error processing key {key}: {str(e)}")
            continue
            
    # 按预期收益排序
    opportunities.sort(key=lambda x: x.estimated_profit, reverse=True)
    return opportunities[:limit]

@app.get(
    "/opportunities/{opportunity_id}", 
    response_model=ArbitrageOpportunity,
    summary="获取套利机会详情",
    description="根据ID获取特定套利机会的详细信息"
)
async def get_arbitrage_opportunity(
    opportunity_id: str = Path(..., description="套利机会ID")
):
    """获取特定套利机会详情"""
    if not redis_client:
        logger.error("Redis client is not initialized")
        return {"error": "Redis service unavailable"}

    try:
        data = redis_client.get(f"{REDIS_KEY_PREFIX}{opportunity_id}")
        if not data:
            logger.error(f"Opportunity {opportunity_id} not found")
            return {"error": "Opportunity not found"}
        return ArbitrageOpportunity(**json.loads(data))
    except redis.RedisError as e:
        logger.error(f"Redis error while fetching opportunity {opportunity_id}: {str(e)}")
        return {"error": "Redis service error"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data for opportunity {opportunity_id}: {str(e)}")
        return {"error": "Data format error"}
    except Exception as e:
        logger.error(f"Unexpected error in get_arbitrage_opportunity: {str(e)}")
        return {"error": "Internal server error"}

@app.get(
    "/symbols",
    summary="获取热门交易对",
    description="获取按交易量排序的热门交易对列表"
)
async def get_top_symbols(
    limit: int = Query(20, description="返回结果数量", ge=1, le=100)
):
    """获取交易量前N的交易对"""
    if not redis_client:
        logger.error("Redis client is not initialized")
        return {"error": "Redis service unavailable"}

    try:
        symbols_data = redis_client.get("top_trading_pairs")
        if not symbols_data:
            logger.warning("No top trading pairs data available")
            return {"symbols": []}
        symbols = json.loads(symbols_data)
        return {"symbols": symbols[:limit]}
    except redis.RedisError as e:
        logger.error(f"Redis error while fetching top symbols: {str(e)}")
        return {"error": "Failed to fetch symbols data"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data for top symbols: {str(e)}")
        return {"error": "Invalid symbols data format"}
    except Exception as e:
        logger.error(f"Unexpected error in get_top_symbols: {str(e)}")
        return {"error": "Internal server error"}

@app.get(
    "/stats",
    summary="获取系统统计信息",
    description="获取系统运行状态和套利统计数据"
)
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
        logger.error(f"Unexpected error in get_arbitrage_stats: {str(e)}")
        return {"error": "Internal server error"}

@app.post(
    "/wallets",
    response_model=WalletResponse,
    summary="创建新的以太坊钱包",
    description="生成新的以太坊钱包地址和私钥"
)
async def create_wallet():
    """创建新的以太坊钱包"""
    try:
        # 初始化Web3和GasManager
        from web3 import Web3
        from multi_source_gas_manager import GasManager
        
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))  # 使用本地节点
        gas_manager = GasManager()
        fund_manager = FundManager(w3, gas_manager)
        
        wallet = fund_manager.create_wallet()
        return {
            "address": wallet["address"],
            "private_key": wallet["private_key"],
            "message": "请妥善保管私钥，生产环境不应暴露私钥"
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
) -> Optional[str]:
    """
    存储套利机会到Redis
    返回: opportunity_id
    """
    if not redis_client:
        logger.error("Redis client is not initialized")
        return None

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
    try:
        redis_client.setex(
            redis_key,
            REDIS_EXPIRY,
            json.dumps(opportunity_data)
        )
        logger.info(f"Successfully stored arbitrage opportunity: {opportunity_id}")
        return opportunity_id
    except redis.RedisError as e:
        logger.error(f"Failed to store arbitrage opportunity: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in store_arbitrage_opportunity: {str(e)}")
        return None

def store_top_trading_pairs(pairs: List[str]) -> bool:
    """存储交易量前N的交易对"""
    if not redis_client:
        logger.error("Redis client is not initialized")
        return False

    try:
        redis_client.setex(
            "top_trading_pairs",
            REDIS_EXPIRY,
            json.dumps(pairs)
        )
        logger.info("Successfully stored top trading pairs")
        return True
    except redis.RedisError as e:
        logger.error(f"Failed to store top trading pairs: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in store_top_trading_pairs: {str(e)}")
        return False
