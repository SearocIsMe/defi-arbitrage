from typing import Dict, Optional
from web3 import Web3
from decimal import Decimal
from dataclasses import dataclass
from multi_source_gas_manager import GasManager

@dataclass
class Position:
    """交易头寸信息"""
    size: Decimal  # 头寸大小(以ETH为单位)
    leverage: Decimal  # 杠杆倍数
    entry_price: Decimal  # 开仓价格
    liquidation_price: Decimal  # 清算价格
    margin: Decimal  # 保证金
    unrealized_pnl: Decimal = Decimal('0')  # 未实现盈亏

class FundManager:
    """资金管理器 - 处理杠杆和头寸计算"""
    
    def __init__(self, web3: Web3, gas_manager: GasManager):
        self.w3 = web3
        self.gas_manager = gas_manager
        self.max_leverage = Decimal('3')  # 最大杠杆倍数
        self.min_margin_ratio = Decimal('0.15')  # 最小保证金率
        self.maintenance_margin_ratio = Decimal('0.075')  # 维持保证金率
        
    async def get_wallet_balance(self, address: str) -> Decimal:
        """获取钱包ETH余额"""
        try:
            balance_wei = await self.w3.eth.get_balance(address)
            return Decimal(str(balance_wei)) / Decimal(str(10**18))
        except Exception as e:
            print(f"Error getting wallet balance: {e}")
            return Decimal('0')

    def calculate_max_position_size(self, 
                                  balance: Decimal,
                                  current_price: Decimal,
                                  leverage: Decimal,
                                  gas_limit: int = 350000) -> Dict:
        """
        计算最大可开仓位大小
        
        参数:
            balance: 账户余额(ETH)
            current_price: 当前价格
            leverage: 杠杆倍数
            gas_limit: 预估gas限制
            
        返回:
            {
                'max_size': Decimal,  # 最大仓位大小
                'required_margin': Decimal,  # 所需保证金
                'liquidation_price': Decimal  # 清算价格
            }
        """
        if leverage > self.max_leverage:
            raise ValueError(f"Leverage cannot exceed {self.max_leverage}")
            
        # 预留gas费用
        gas_cost = Decimal(str(self.gas_manager.estimate_transaction_gas_cost(gas_limit)))
        available_balance = balance - gas_cost
        
        if available_balance <= 0:
            return {
                'max_size': Decimal('0'),
                'required_margin': Decimal('0'),
                'liquidation_price': Decimal('0')
            }
            
        # 计算所需保证金(考虑最小保证金率)
        required_margin = available_balance
        max_position_size = required_margin * leverage
        
        # 计算清算价格
        liquidation_price = self._calculate_liquidation_price(
            position_size=max_position_size,
            entry_price=current_price,
            margin=required_margin,
            is_long=True  # 假设做多
        )
        
        return {
            'max_size': max_position_size,
            'required_margin': required_margin,
            'liquidation_price': liquidation_price
        }
        
    def _calculate_liquidation_price(self,
                                   position_size: Decimal,
                                   entry_price: Decimal,
                                   margin: Decimal,
                                   is_long: bool) -> Decimal:
        """
        计算清算价格
        
        参数:
            position_size: 仓位大小
            entry_price: 开仓价格
            margin: 保证金
            is_long: 是否做多
        """
        if position_size == 0 or entry_price == 0:
            return Decimal('0')
            
        position_value = position_size * entry_price
        maintenance_margin = position_value * self.maintenance_margin_ratio
        
        if is_long:
            price_drop = (margin - maintenance_margin) / position_size
            return entry_price - price_drop
        else:
            price_rise = (margin - maintenance_margin) / position_size
            return entry_price + price_rise
            
    def calculate_leverage_params(self,
                                desired_position_size: Decimal,
                                available_balance: Decimal,
                                current_price: Decimal) -> Optional[Dict]:
        """
        计算给定仓位所需的杠杆参数
        
        参数:
            desired_position_size: 期望的仓位大小
            available_balance: 可用余额
            current_price: 当前价格
            
        返回:
            {
                'required_leverage': Decimal,  # 所需杠杆
                'required_margin': Decimal,  # 所需保证金
                'liquidation_price': Decimal  # 清算价格
            }
        """
        position_value = desired_position_size * current_price
        
        # 计算所需杠杆
        required_leverage = position_value / available_balance
        
        if required_leverage > self.max_leverage:
            print(f"Warning: Required leverage {required_leverage} exceeds maximum {self.max_leverage}")
            return None
            
        # 计算所需保证金
        required_margin = position_value / required_leverage
        
        # 确保满足最小保证金率要求
        min_required_margin = position_value * self.min_margin_ratio
        if required_margin < min_required_margin:
            print(f"Warning: Required margin {required_margin} is below minimum {min_required_margin}")
            return None
            
        # 计算清算价格
        liquidation_price = self._calculate_liquidation_price(
            position_size=desired_position_size,
            entry_price=current_price,
            margin=required_margin,
            is_long=True  # 假设做多
        )
        
        return {
            'required_leverage': required_leverage,
            'required_margin': required_margin,
            'liquidation_price': liquidation_price
        }
        
    def calculate_pnl(self, position: Position, current_price: Decimal) -> Dict:
        """
        计算仓位的未实现盈亏和ROE
        
        参数:
            position: Position对象
            current_price: 当前价格
            
        返回:
            {
                'unrealized_pnl': Decimal,  # 未实现盈亏
                'roe': Decimal,  # 投资回报率
                'margin_ratio': Decimal  # 当前保证金率
            }
        """
        if position.size == 0:
            return {
                'unrealized_pnl': Decimal('0'),
                'roe': Decimal('0'),
                'margin_ratio': Decimal('0')
            }
            
        # 计算未实现盈亏
        entry_value = position.size * position.entry_price
        current_value = position.size * current_price
        unrealized_pnl = current_value - entry_value
        
        # 计算ROE
        roe = (unrealized_pnl / position.margin) * Decimal('100')
        
        # 计算当前保证金率
        position_value = position.size * current_price
        margin_ratio = (position.margin + unrealized_pnl) / position_value
        
        return {
            'unrealized_pnl': unrealized_pnl,
            'roe': roe,
            'margin_ratio': margin_ratio
        }
        
    def is_liquidation_triggered(self, position: Position, current_price: Decimal) -> bool:
        """检查是否触发清算"""
        pnl_info = self.calculate_pnl(position, current_price)
        return pnl_info['margin_ratio'] <= self.maintenance_margin_ratio
