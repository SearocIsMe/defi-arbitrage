"""BitMart CLOB Connector"""
from typing import Dict, Optional
from web3.types import TxReceipt
from eth_typing import ChecksumAddress
import requests
import hmac
import hashlib
import time
from connectors.base_connector import CLOBConnector

class BitMartConnector(CLOBConnector):
    """BitMart CLOB connector implementation"""
    
    def __init__(self, chain: str, rpc_url: str, router_address: str, factory_address: str):
        self.chain = chain
        self.rpc_url = rpc_url
        self.router_address = router_address
        self.factory_address = factory_address
        self.base_url = "https://api-cloud.bitmart.com"
        self.api_key = "YOUR_API_KEY"
        self.api_secret = "YOUR_API_SECRET"
        
    def _generate_signature(self, timestamp, params=None):
        if params:
            message = f"{timestamp}#{self.api_secret}#{params}"
        else:
            message = f"{timestamp}#{self.api_secret}#"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method, endpoint, params=None):
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, params)
        headers = {
            "X-BM-KEY": self.api_key,
            "X-BM-SIGN": signature,
            "X-BM-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
        response = requests.request(method, f"{self.base_url}{endpoint}", headers=headers, json=params)
        response.raise_for_status()
        return response.json()["data"]
    
    def get_name(self) -> str:
        return "BitMart"
    
    def get_chain(self) -> str:
        return self.chain
    
    def get_available_markets(self) -> Dict[str, Dict]:
        """Fetch available trading markets from BitMart"""
        try:
            markets = self._make_request("GET", "/spot/v1/symbols")
            return {
                market["symbol"]: {
                    "base_asset": market["base_currency"],
                    "quote_asset": market["quote_currency"],
                    "min_price": float(market["price_min_precision"]),
                    "max_price": float(market["price_max_precision"]),
                    "min_amount": float(market["amount_min_precision"]),
                    "max_amount": float(market["amount_max_precision"]),
                }
                for market in markets
            }
        except Exception as e:
            raise Exception(f"Failed to fetch markets: {str(e)}")
    
    def get_balances(self, wallet_address: ChecksumAddress) -> Dict[str, float]:
        """Fetch account balances from BitMart"""
        try:
            balances = self._make_request("GET", "/account/v1/wallet")
            return {
                balance["currency"]: float(balance["available"])
                for balance in balances
            }
        except Exception as e:
            raise Exception(f"Failed to fetch balances: {str(e)}")
    
    def get_order_book(self, market: str) -> Dict:
        """Fetch order book for a specific market"""
        try:
            order_book = self._make_request("GET", f"/spot/v1/symbols/book?symbol={market}")
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
        """Place a limit order on BitMart"""
        try:
            order = self._make_request("POST", "/spot/v1/submit_order", {
                "symbol": market,
                "side": side.lower(),
                "type": "limit",
                "price": str(price),
                "size": str(amount),
                "client_order_id": str(int(time.time() * 1000))
            })
            return order["order_id"]
        except Exception as e:
            raise Exception(f"Failed to place order: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on BitMart"""
        try:
            self._make_request("POST", "/spot/v1/cancel_order", {"order_id": order_id})
            return True
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")