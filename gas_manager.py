from web3 import Web3
import os
import requests
import json
from eth_account import Account
from hexbytes import HexBytes

class MEVProtector:
    def __init__(self, chain_config):
        self.w3 = Web3(Web3.HTTPProvider(chain_config['rpc']))
        self.chain_id = chain_config.get('chain_id', 1)
        self.flashbots_endpoint = 'https://relay.flashbots.net'
        self.signer = Account.from_key(os.getenv('FLASHBOTS_SIGNER_KEY'))
        
    def get_optimal_gas_params(self):
        """获取实时Gas优化参数"""
        try:
            fee_history = self.w3.eth.fee_history(5, 'latest', [25, 50, 75])
            base_fee = self.w3.eth.get_block('latest').baseFeePerGas
            priority_fee = {
                'low': int(fee_history['reward'][0][0] * 0.9),
                'medium': int(fee_history['reward'][0][1] * 1.1),
                'high': int(fee_history['reward'][0][2] * 1.3)
            }
            return {
                'maxPriorityFeePerGas': priority_fee['high'],
                'maxFeePerGas': base_fee + priority_fee['high'],
                'gasLimit': 350000
            }
        except Exception as e:
            print(f"Error fetching gas params: {e}")
            return None

    def protect_transaction(self, tx):
        """交易MEV保护处理"""
        # 添加随机数混淆
        tx['nonce'] = self.w3.eth.get_transaction_count(self.signer.address)
        
        # 使用Flashbots打包
        flashbots_tx = {
            'tx': tx,
            'blockNumber': self.w3.eth.block_number + 1,
            'minTimestamp': 0,
            'maxTimestamp': 0
        }
        
        try:
            response = requests.post(
                self.flashbots_endpoint,
                json={
                    'jsonrpc': '2.0',
                    'method': 'eth_sendPrivateTransaction',
                    'params': [{
                        'tx': HexBytes(tx).hex(),
                        'preferences': {
                            'fast': True
                        }
                    }],
                    'id': 1
                },
                headers={'Content-Type': 'application/json'}
            )
            return response.json().get('result')
        except Exception as e:
            print(f"Flashbots error: {e}")
            return None

    def simulate_bundle(self, tx_hash):
        """交易模拟检查"""
        try:
            return requests.post(
                self.flashbots_endpoint,
                json={
                    'jsonrpc': '2.0',
                    'method': 'eth_callBundle',
                    'params': [{
                        'txs': [tx_hash],
                        'blockNumber': f'0x{self.w3.eth.block_number + 1:x}'
                    }],
                    'id': 1
                }
            ).json()
        except Exception as e:
            print(f"Simulation error: {e}")
            return None
