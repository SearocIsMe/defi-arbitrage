from typing import Dict, Optional, List
import os
import time
import requests
from web3 import Web3
from abc import ABC, abstractmethod
import json
from datetime import datetime, timedelta
import statistics

class GasDataSource(ABC):
    """Gas价格数据源基类"""
    @abstractmethod
    def get_gas_price(self) -> Optional[Dict]:
        """
        获取gas价格
        返回: {
            'fast': int,  # Gwei
            'standard': int,
            'slow': int,
            'timestamp': int
        }
        """
        pass

class Web3GasSource(GasDataSource):
    """通过Web3连接获取gas价格"""
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    def get_gas_price(self) -> Optional[Dict]:
        try:
            fee_history = self.w3.eth.fee_history(5, 'latest', [25, 50, 75])
            base_fee = self.w3.eth.get_block('latest').baseFeePerGas
            
            # 计算不同优先级的gas价格
            priority_fees = {
                'slow': int(fee_history['reward'][0][0]),
                'standard': int(fee_history['reward'][0][1]),
                'fast': int(fee_history['reward'][0][2])
            }
            
            return {
                'fast': base_fee + priority_fees['fast'],
                'standard': base_fee + priority_fees['standard'],
                'slow': base_fee + priority_fees['slow'],
                'timestamp': int(time.time())
            }
        except Exception as e:
            print(f"Web3 gas price error: {e}")
            return None

class EtherscanGasSource(GasDataSource):
    """通过Etherscan API获取gas价格"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.etherscan.io/api"
        self.history_url = "https://api.etherscan.io/api?module=stats&action=dailyavggasprice"

    def get_gas_price(self) -> Optional[Dict]:
        try:
            response = requests.get(
                self.base_url,
                params={
                    'module': 'gastracker',
                    'action': 'gasoracle',
                    'apikey': self.api_key
                }
            )
            data = response.json()
            if data['status'] == '1':
                result = data['result']
                return {
                    'fast': int(float(result['FastGasPrice'])),
                    'standard': int(float(result['ProposeGasPrice'])),
                    'slow': int(float(result['SafeGasPrice'])),
                    'timestamp': int(time.time())
                }
            return None
        except Exception as e:
            print(f"Etherscan gas price error: {e}")
            return None

    def get_historical_prices(self, days: int = 7) -> Optional[List[Dict]]:
        """获取历史gas价格数据"""
        try:
            response = requests.get(
                f"{self.history_url}&apikey={self.api_key}"
            )
            data = response.json()
            if data['status'] == '1':
                return data['result'][-days:]
            return None
        except Exception as e:
            print(f"Etherscan historical gas price error: {e}")
            return None

class OneInchGasSource(GasDataSource):
    """通过1inch API获取gas价格"""
    def __init__(self):
        self.base_url = "https://api.1inch.io/v5.0/1/gas-price"

    def get_gas_price(self) -> Optional[Dict]:
        try:
            response = requests.get(self.base_url)
            data = response.json()
            return {
                'fast': int(data['high']),
                'standard': int(data['medium']),
                'slow': int(data['low']),
                'timestamp': int(time.time())
            }
        except Exception as e:
            print(f"1inch gas price error: {e}")
            return None

class GasPredictionService:
    """Gas价格预测服务"""
    def __init__(self, data_file: str = 'gas_price_history.json'):
        self.data_file = data_file
        self.history_data = self._load_history()
        self.max_history_days = 7
        self.ema_alpha = 0.2  # EMA平滑因子
        self.volatility_threshold = 0.3  # 波动率阈值
        self.spike_threshold = 0.5  # 价格突变阈值
        self.ema_values = {'fast': None, 'standard': None, 'slow': None}

    def _load_history(self) -> List[Dict]:
        """加载历史数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception:
            return []

    def _save_history(self):
        """保存历史数据"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.history_data, f)
        except Exception as e:
            print(f"Error saving gas price history: {e}")

    def add_price_data(self, price_data: Dict):
        """添加新的价格数据到历史记录"""
        self.history_data.append({
            **price_data,
            'timestamp': int(time.time())
        })
        
        # 只保留最近7天的数据
        cutoff_time = int(time.time()) - (self.max_history_days * 24 * 3600)
        self.history_data = [d for d in self.history_data if d['timestamp'] > cutoff_time]
        self._save_history()

    def calculate_volatility(self, prices: List[int]) -> float:
        """计算价格波动率"""
        if len(prices) < 2:
            return 0.0
        price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        return statistics.mean(price_changes)

    def detect_price_spike(self, current_price: int, historical_prices: List[int]) -> bool:
        """检测价格突变"""
        if not historical_prices:
            return False
        avg_price = statistics.mean(historical_prices)
        return abs(current_price - avg_price) / avg_price > self.spike_threshold

    def update_ema(self, speed: str, new_price: int):
        """更新指数移动平均"""
        if self.ema_values[speed] is None:
            self.ema_values[speed] = new_price
        else:
            self.ema_values[speed] = int(
                new_price * self.ema_alpha + 
                self.ema_values[speed] * (1 - self.ema_alpha)
            )

    def predict_gas_price(self) -> Optional[Dict]:
        """预测未来gas价格,使用EMA和波动率分析"""
        if not self.history_data:
            return None

        try:
            current_hour = datetime.now().hour
            relevant_prices = {
                'fast': [],
                'standard': [],
                'slow': []
            }

            # 收集相关数据
            for data in self.history_data:
                data_hour = datetime.fromtimestamp(data['timestamp']).hour
                if data_hour == current_hour:
                    for speed in ['fast', 'standard', 'slow']:
                        if speed in data:
                            relevant_prices[speed].append(data[speed])

            prediction = {}
            for speed in ['fast', 'standard', 'slow']:
                if relevant_prices[speed]:
                    # 计算基础预测值
                    weights = list(range(1, len(relevant_prices[speed]) + 1))
                    base_prediction = int(
                        sum(p * w for p, w in zip(relevant_prices[speed], weights)) /
                        sum(weights)
                    )

                    # 检查波动率
                    volatility = self.calculate_volatility(relevant_prices[speed])
                    is_spike = self.detect_price_spike(
                        base_prediction, 
                        relevant_prices[speed][:-1]
                    )

                    # 更新EMA
                    self.update_ema(speed, base_prediction)

                    if is_spike:
                        # 如果检测到突变,使用EMA值
                        prediction[speed] = self.ema_values[speed]
                    elif volatility > self.volatility_threshold:
                        # 如果波动率高,增加EMA权重
                        prediction[speed] = int(
                            0.7 * self.ema_values[speed] + 
                            0.3 * base_prediction
                        )
                    else:
                        # 正常情况下的预测
                        prediction[speed] = int(
                            0.3 * self.ema_values[speed] + 
                            0.7 * base_prediction
                        )
                else:
                    prediction[speed] = None

            return prediction
        except Exception as e:
            print(f"Error predicting gas price: {e}")
            return None

class GasManager:
    """Gas价格管理器 - 聚合多个数据源"""
    def __init__(self):
        # 初始化所有数据源
        self.sources: List[GasDataSource] = []
        
        # Web3数据源
        if os.getenv('INFURA_API_KEY'):
            rpc_url = f"https://mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}"
            self.sources.append(Web3GasSource(rpc_url))
        
        # Etherscan数据源
        if os.getenv('ETHERSCAN_API_KEY'):
            self.etherscan = EtherscanGasSource(os.getenv('ETHERSCAN_API_KEY'))
            self.sources.append(self.etherscan)
        
        # 1inch数据源
        self.sources.append(OneInchGasSource())
        
        # 初始化预测服务
        self.prediction_service = GasPredictionService()
        
        # 缓存最近的gas价格
        self.cache = {
            'data': None,
            'timestamp': 0
        }
        self.cache_duration = 15  # 缓存时间(秒)

    def get_optimal_gas_price(self) -> Dict:
        """
        获取最优gas价格(聚合多个数据源)
        返回中位数价格以避免异常值
        """
        current_time = int(time.time())
        
        # 检查缓存是否有效
        if current_time - self.cache['timestamp'] < self.cache_duration:
            return self.cache['data']

        prices = {
            'fast': [],
            'standard': [],
            'slow': []
        }

        # 从所有数据源获取价格
        for source in self.sources:
            price_data = source.get_gas_price()
            if price_data:
                for speed in ['fast', 'standard', 'slow']:
                    prices[speed].append(price_data[speed])
                # 添加到预测服务的历史数据
                self.prediction_service.add_price_data(price_data)

        # 获取预测价格
        predicted_prices = self.prediction_service.predict_gas_price()
        if predicted_prices:
            for speed in ['fast', 'standard', 'slow']:
                if predicted_prices[speed] is not None:
                    prices[speed].append(predicted_prices[speed])

        # 计算每个速度级别的中位数
        result = {}
        for speed in prices:
            if prices[speed]:
                sorted_prices = sorted(prices[speed])
                mid = len(sorted_prices) // 2
                if len(sorted_prices) % 2 == 0:
                    result[speed] = (sorted_prices[mid-1] + sorted_prices[mid]) // 2
                else:
                    result[speed] = sorted_prices[mid]
            else:
                result[speed] = None

        # 更新缓存
        self.cache = {
            'data': result,
            'timestamp': current_time
        }

        return result

    def estimate_transaction_gas_cost(self, gas_limit: int, speed: str = 'fast') -> float:
        """
        估算交易gas成本(以ETH为单位)
        """
        gas_prices = self.get_optimal_gas_price()
        if not gas_prices or gas_prices[speed] is None:
            return 0
        
        gas_price_gwei = gas_prices[speed]
        return (gas_price_gwei * gas_limit) / 1e9  # 转换为ETH

    def is_gas_price_reasonable(self, threshold_gwei: int = 100) -> bool:
        """
        检查当前gas价格是否合理
        """
        gas_prices = self.get_optimal_gas_price()
        return gas_prices and gas_prices['standard'] <= threshold_gwei

    def get_gas_price_trend(self) -> Optional[str]:
        """
        分析gas价格趋势
        返回: 'increasing', 'decreasing', 或 'stable'
        """
        try:
            if hasattr(self, 'etherscan'):
                historical_data = self.etherscan.get_historical_prices(3)  # 获取3天数据
                if historical_data:
                    prices = [float(day['avgGasPrice']) for day in historical_data]
                    if len(prices) >= 2:
                        avg_change = (prices[-1] - prices[0]) / len(prices)
                        if avg_change > 5:  # 5 Gwei的变化阈值
                            return 'increasing'
                        elif avg_change < -5:
                            return 'decreasing'
                        return 'stable'
            return None
        except Exception as e:
            print(f"Error analyzing gas price trend: {e}")
            return None
