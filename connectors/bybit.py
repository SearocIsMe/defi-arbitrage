"""Bybit CLOB Connector"""
from typing import Dict, Optional
from web3.types import TxReceipt
from eth_typing import ChecksumAddress
import requests
import hmac
import hashlib
import time
from connectors.base_connector import CLOBConnector

class BybitConnector(CLOBConnector):
    """Bybit CLOB connector implementation"""
    
    def __init__(self, chain: str, rpc_url: str, router_address: str, factory_address: str):
        self.chain = chain
        self.rpc_url = rpc_url
        self.router_address = router_address
        self.factory_address = factory_address
        self.base_url = "https://api.bybit.com"
        self.api_key = "YOUR_API_KEY"
        self.api_secret = "YOUR_API_SECRET"
        
    def _generate_signature(self, timestamp, params=None):
        if params:
            message = f"{timestamp}{self.api_key}{params}"
        else:
            message = f"{timestamp}{self.api_key}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method, endpoint, params=None):
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, params)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
        response = requests.request(method, f"{self.base_url}{endpoint}", headers=headers, json=params)
        response.raise_for_status()
        return response.json()["result"]
    
    def get_name(self) -> str:
        return "Bybit"
    
    def get_chain(self) -> str:
        return self.chain
    
    def get_available_markets(self) -> Dict[str, Dict]:
        """Fetch available trading markets from Bybit"""
        try:
            markets = self._make_request("GET", "/v5/market/instruments-info?category=spot")
            return {
                market["symbol"]: {
                    "base_asset": market["baseCoin"],
                    "quote_asset": market["quoteCoin"],
                    "min_price": float(market["priceFilter"]["minPrice"]),
                    "max_price": float(market["priceFilter"]["maxPrice"]),
                    "min_amount": float(market["lotSizeFilter"]["minOrderQty"]),
                    "max_amount": float(market["lotSizeFilter"]["maxOrderQty"]),
                }
                for market in markets["list"]
            }
        except Exception as e:
            raise Exception(f"Failed to fetch markets: {str(e)}")
    
    def get_balances(self, wallet_address: ChecksumAddress) -> Dict[str, float]:
        """Fetch account balances from Bybit"""
        try:
            balances = self._make_request("GET", "/v5/account/wallet-balance")
            return {
                balance["coin"]: float(balance["free"])
                for balance in balances["list"][0]["coin"]
            }
        except Exception as e:
            raise Exception(f"Failed to fetch balances: {str(e)}")
    
    def get_order_book(self, market: str) -> Dict:
        """Fetch order book for a specific market"""
        try:
            order_book = self._make_request("GET", f"/v5/market/orderbook?category=spot&symbol={market}")
            return {
                "bids": [[float(price), float(amount)] for price, amount in order_book["b"]],
                "asks": [[float(price), float(amount)] for price, amount in order_book["a"]],
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
        """Place a limit order on Bybit"""
        try:
            order = self._make_request("POST", "/v5/order/create", {
                "category": "spot",
                "symbol": market,
                "side": side.capitalize(),
                "orderType": "Limit",
                "qty": str(amount),
                "price": str(price),
                "timeInForce": "GTC"
            })
            return order["orderId"]
        except Exception as e:
            raise Exception(f"Failed to place order: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on Bybit"""
        try:
            self._make_request("POST", "/v5/order/cancel", {
                "category": "spot",
                "orderId": order_id
            })
            return True
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")