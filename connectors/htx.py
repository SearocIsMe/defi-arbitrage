"""HTX CLOB Connector"""
from typing import Dict, Optional
from web3.types import TxReceipt
from eth_typing import ChecksumAddress
import requests
from connectors.base_connector import CLOBConnector

class HTXConnector(CLOBConnector):
    """HTX CLOB connector implementation"""
    
    def __init__(self, chain: str, rpc_url: str, router_address: str, factory_address: str):
        self.chain = chain
        self.rpc_url = rpc_url
        self.router_address = router_address
        self.factory_address = factory_address
        self.base_url = "https://api.huobi.pro"
        
    def get_name(self) -> str:
        return "HTX"
    
    def get_chain(self) -> str:
        return self.chain
    
    def get_available_markets(self) -> Dict[str, Dict]:
        """Fetch available trading markets from HTX"""
        url = f"{self.base_url}/v1/common/symbols"
        try:
            response = requests.get(url)
            response.raise_for_status()
            markets = response.json()["data"]
            return {
                market["symbol"]: {
                    "base_asset": market["base-currency"],
                    "quote_asset": market["quote-currency"],
                    "min_price": float(market["price-precision"]),
                    "max_price": float(market["price-precision"]),
                    "min_amount": float(market["amount-precision"]),
                    "max_amount": float(market["amount-precision"]),
                }
                for market in markets
            }
        except Exception as e:
            raise Exception(f"Failed to fetch markets: {str(e)}")
    
    def get_balances(self, wallet_address: ChecksumAddress) -> Dict[str, float]:
        """Fetch account balances from HTX"""
        url = f"{self.base_url}/v1/account/accounts/{wallet_address}/balance"
        try:
            response = requests.get(url)
            response.raise_for_status()
            balances = response.json()["data"]["list"]
            return {
                balance["currency"]: float(balance["balance"])
                for balance in balances
            }
        except Exception as e:
            raise Exception(f"Failed to fetch balances: {str(e)}")
    
    def get_order_book(self, market: str) -> Dict:
        """Fetch order book for a specific market"""
        url = f"{self.base_url}/market/depth"
        try:
            response = requests.get(url, params={"symbol": market, "type": "step0"})
            response.raise_for_status()
            order_book = response.json()["tick"]
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
        """Place a limit order on HTX"""
        url = f"{self.base_url}/v1/order/orders/place"
        try:
            response = requests.post(url, json={
                "account-id": wallet_address,
                "symbol": market,
                "type": f"{side.lower()}-limit",
                "price": str(price),
                "amount": str(amount)
            })
            response.raise_for_status()
            order = response.json()
            return order["data"]
        except Exception as e:
            raise Exception(f"Failed to place order: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on HTX"""
        url = f"{self.base_url}/v1/order/orders/{order_id}/submitcancel"
        try:
            response = requests.post(url)
            response.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")