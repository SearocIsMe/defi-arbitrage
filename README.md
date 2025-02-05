# defi-arbitrage

跨链套利自动化交易系统,支持CEX/DEX价格套利及MEV保护。

## 系统架构

### 核心功能
- 多源价格监控 (CEX + DEX)
- 跨链套利执行
- MEV保护机制
- 动态资金管理
- Gas费用多源优化
- 智能风控系统

### 已实现特性
- 支持主流CEX (Binance, OKX)
- 集成DEX协议 (Uniswap V3, Sushiswap, PancakeSwap)
- 跨链支持 (Ethereum, Arbitrum)
- Flashbots保护
- 动态仓位计算
- 2倍杠杆交易
- 多源Gas价格聚合
- 智能Gas价格预测
- 自动交易对选择
  * 多DEX流动性数据聚合
  * TVL和交易量加权排名
  * 自动更新热门交易对

#### 优化方向
- 将跨链支持做成可配置,支持以下成熟链:
  * Layer 2:
    - Arbitrum: 高EVM兼容性,低gas费用,快速终局性
    - Optimism: 强EVM兼容性,Bedrock升级后性能提升
    - zkSync Era: 零知识证明,高吞吐量,即时终局性
    - Base: Coinbase支持的L2,与Optimism技术相同
  * 独立公链:
    - BNB Chain (BSC): 高吞吐量,活跃的DeFi生态
    - Avalanche: 子网架构,高性能,强去中心化
    - Polygon PoS: 成熟稳定,丰富的DeFi应用
    - Fantom: 高速确认,低费用,EVM兼容
  * 跨链桥:
    - LayerZero: 去中心化程度高,安全性强
    - Stargate: 基于LayerZero,流动性聚合
    - Multichain: 支持链种类多,成熟稳定
    - Celer: 快速跨链,支持多种资产
    
  * 链选择考虑因素:
    - 流动性: TVL > $500M的链优先考虑
    - 安全性: 主网稳定运行时间 > 1年
    - 兼容性: 优先支持EVM兼容链
    - 跨链桥: 
      * 日交易量 > $10M
      * 无重大安全事故历史
      * 多重签名或去中心化验证
      * 完善的预言机支持
    - 生态:
      * 活跃开发者 > 100
      * 日活用户 > 10000
      * DEX总锁仓量 > $100M



## 系统组件

### 核心模块
- arbitrage_detector.py: 套利机会检测与执行
- fund_manager.py: 资金管理与风控
- gas_manager.py: 基础Gas管理
- multi_source_gas_manager.py: 多源Gas价格聚合与优化
- dex_liquidity_manager.py: DEX流动性数据管理
  * 多源数据聚合 (Uniswap V3, SushiSwap, PancakeSwap)
  * 智能交易对排名
  * Redis缓存支持

## 关键优化方向

### Gas价格优化
当前实现:
- 多源Gas价格数据聚合系统
- 支持多个数据源:
  * Web3以太坊节点
  * DEX实时数据
  * 链上Gas统计
- 智能Gas价格预测
- EIP-1559定价机制
- 动态Gas费用调整

优化建议:
1. 扩展Gas数据源:
   - 整合更多DEX的Gas数据
   - 添加专业Gas预测服务
   - 实现跨链Gas对比
2. 增强Gas优化策略:
   - 机器学习预测模型
   - 历史数据分析
   - 网络拥堵预警
3. 智能调度系统:
   - Gas价格趋势分析
   - 最优执行时间预测
   - 自动任务调度

### 资金管理优化
当前实现:
- 支持2倍杠杆交易
- 基础仓位大小计算
- 智能止损机制
- 动态风险评估

优化建议:
1. 高级杠杆管理:
   - 动态杠杆倍数 (1-3倍)
   - 实时清算价格计算
   - 多层级止损策略
   - 自动减仓机制
2. 资金效率优化:
   - 多策略资金分配
   - 动态仓位调整
   - 风险敞口控制
   - 流动性管理
3. 收益优化系统:
   - 套利机会优先级
   - 收益率预测
   - 资金使用效率分析

### 风险控制优化
当前实现:
- 交易模拟验证
- MEV保护
- 智能滑点控制
- 多级风控阈值
- 自动交易对选择
  * 基于流动性的风险评估
  * 多DEX数据验证
  * 实时流动性监控

优化建议:
1. 增强风控机制:
   - 深度学习风险评估
   - 实时市场波动监控
   - 智能止损优化
2. 交易保护增强:
   - 私有交易路由
   - 反三明治攻击
   - 失败交易自动回滚
   - MEV-Boost集成
3. 流动性风险管理:
   - 多DEX流动性对比分析
   - 历史流动性趋势分析
   - 流动性突变预警

## 配置说明

### 环境变量
```
INFURA_API_KEY=你的Infura API密钥
FLASHBOTS_SIGNER_KEY=你的Flashbots签名密钥
WALLET_ADDRESS=你的钱包地址
DEX_API_KEY=DEX API密钥
DEX_API_SECRET=DEX API密钥
```

### Redis配置
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 数据缓存
- 交易对数据: 100小时过期
- 套利机会: 100小时过期
- 实时行情: 60秒过期
### 安全优化
   钱包地址最好用加密算法保护一下

### 运行要求
- Python 3.8+
- Redis服务器
- 以太坊节点访问
- Flashbots RPC支持
- The Graph API访问

### 依赖安装
```bash
pip install -r requirements.txt
```

### 主要依赖
- Web3.py: 以太坊交互
- ccxt: 交易所API
- gql: GraphQL客户端
- aiohttp: 异步HTTP
- redis: 数据缓存
- fastapi: API服务

## API文档

### RESTful API接口

#### 套利机会相关
```
GET /opportunities
获取套利机会列表
参数:
- symbol: 交易对符号 (可选)
- min_profit: 最小预期收益 (可选)
- status: 套利状态过滤 (可选)
- limit: 返回数量 (默认10,最大100)

GET /opportunities/{opportunity_id}
获取特定套利机会详情
参数:
- opportunity_id: 套利机会ID

GET /symbols
获取热门交易对列表
参数:
- limit: 返回数量 (默认20,最大100)

GET /stats
获取系统统计信息
返回:
- total_opportunities: 总机会数
- average_profit: 平均收益
- last_update: 最后更新时间
```

### API状态码
- 200: 请求成功
- 400: 请求参数错误
- 404: 资源不存在
- 500: 服务器内部错误

### 数据模型
```json
ArbitrageOpportunity {
    "id": "string",              // 套利机会ID
    "timestamp": "datetime",     // 创建时间
    "symbol": "string",          // 交易对符号
    "source_exchange": "string", // 源交易所
    "target_exchange": "string", // 目标交易所
    "price_difference": "float", // 价格差异(%)
    "estimated_profit": "float", // 预估收益(ETH)
    "gas_cost": "float",        // Gas成本(ETH)
    "transaction_details": {},   // 交易详情
    "status": "enum"            // 状态(pending/simulated/executing/completed/failed)
}
```

### Swagger文档
- 访问 `/docs` 获取交互式API文档
- 支持在线API测试
- 包含详细的参数说明
- 提供请求/响应示例

### API使用示例
```python
import requests

# 获取所有套利机会
response = requests.get('http://localhost:8000/opportunities')
opportunities = response.json()

# 获取特定交易对的套利机会
params = {'symbol': 'WETH/USDC', 'min_profit': 0.01}
response = requests.get('http://localhost:8000/opportunities', params=params)
filtered_opportunities = response.json()

# 获取系统统计信息
response = requests.get('http://localhost:8000/stats')
stats = response.json()
```

## 性能指标
- 最小套利差价: 0.5%
- Gas成本覆盖: 预期收益 > 1.2倍Gas成本
- 单次交易限额: 0.1-0.5 ETH
- Gas价格预测准确率: >85%
- 套利成功率: >90%
- 平均收益率: >0.8%/笔
- 交易对更新频率: 60秒
- 套利检测延迟: <2秒/对


# Install Redis on Windows
```
wsl --install
lindows@DTC-4Q563Y3:~$, 7788
```
