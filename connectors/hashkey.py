"""HashKey CLOB Connector"""
from typing import Dict, Optional
from web3.types import TxReceipt
from eth_typing import ChecksumAddress
import requests
from connectors.base_connector import CLOBConnector


class HashKeyConnector(CLOBConnector):
    """HashKey CLOB connector implementation"""
    
    def __init__(self, chain: str, rpc_url: str, router_address: str, factory_address: str):
        self.chain = chain
        self.rpc_url = rpc_url
        self.router_address = router_address
        self.factory_address = factory_address
        self.base_url = "https://api.hashkey.com/api/v1"
        
    def get_name(self) -> str:
        return "HashKey"
    
    def get_chain(self) -> str:
        return self.chain
    
    def get_available_markets(self) -> Dict[str, Dict]:
        """Fetch available trading markets from HashKey"""
        url = f"{self.base_url}/markets"
        try:
            response = requests.get(url)
            response.raise_for_status()
            markets = response.json()
            return {
                market["symbol"]: {
                    "base_asset": market["baseAsset"],
                    "quote_asset": market["quoteAsset"],
                    "min_price": float(market["minPrice"]),
                    "max_price": float(market["maxPrice"]),
                    "min_amount": float(market["minAmount"]),
                    "max_amount": float(market["maxAmount"]),
                }
                for market in markets
            }
        except Exception as e:
            raise Exception(f"Failed to fetch markets: {str(e)}")
    
    def get_balances(self, wallet_address: ChecksumAddress) -> Dict[str, float]:
        """Fetch account balances from HashKey"""
        url = f"{self.base_url}/account/balances"
        try:
            response = requests.get(url, params={"address": wallet_address})
            response.raise_for_status()
            balances = response.json()
            return {
                balance["asset"]: float(balance["free"])
                for balance in balances
            }
        except Exception as e:
            raise Exception(f"Failed to fetch balances: {str(e)}")
    
    def get_order_book(self, market: str) -> Dict:
        """Fetch order book for a specific market"""
        url = f"{self.base_url}/depth"
        try:
            response = requests.get(url, params={"symbol": market})
            response.raise_for_status()
            order_book = response.json()
            return {
                "bids": [[float(price), float(amount)] for price, amount in order_book["bids"]],
                "asks": [[float(price), float(amount)] for price, amount in order_book["asks"]],
            }
        except Exception as e:
            raise Exception(f"Failed to fetch order book: {str(e)}")
    
    def place_limit_order(
        self,
        market: str,
        side: str,
        price: float,
        amount: float,
        wallet_address: ChecksumAddress
    ) -> str:
        """Place a limit order on HashKey"""
        url = f"{self.base_url}/order"
        try:
            response = requests.post(url, json={
                "symbol": market,
                "side": side.upper(),
                "type": "LIMIT",
                "price": str(price),
                "quantity": str(amount),
                "address": wallet_address
            })
            response.raise_for_status()
            order = response.json()
            return order["orderId"]
        except Exception as e:
            raise Exception(f"Failed to place order: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on HashKey"""
        url = f"{self.base_url}/order"
        try:
            response = requests.delete(url, params={"orderId": order_id})
            response.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")