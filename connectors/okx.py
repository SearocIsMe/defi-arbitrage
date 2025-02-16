"""OKX CLOB Connector"""
from typing import Dict, Optional
from web3.types import TxReceipt
from eth_typing import ChecksumAddress
import requests
import hmac
import hashlib
import time
from connectors.base_connector import CLOBConnector

class OKXConnector(CLOBConnector):
    """OKX CLOB connector implementation"""
    
    def __init__(self, chain: str, rpc_url: str, router_address: str, factory_address: str):
        self.chain = chain
        self.rpc_url = rpc_url
        self.router_address = router_address
        self.factory_address = factory_address
        self.base_url = "https://www.okx.com/api/v5"
        self.api_key = "YOUR_API_KEY"
        self.api_secret = "YOUR_API_SECRET"
        self.passphrase = "YOUR_PASSPHRASE"
        
    def _generate_signature(self, timestamp, method, request_path, body=""):
        message = timestamp + method + request_path + body
        mac = hmac.new(bytes(self.api_secret, 'utf-8'), bytes(message, 'utf-8'), hashlib.sha256)
        return mac.hexdigest()
    
    def _make_request(self, method, endpoint, params=None):
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, method.upper(), endpoint, str(params) if params else "")
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }
        response = requests.request(method, f"{self.base_url}{endpoint}", headers=headers, json=params)
        response.raise_for_status()
        return response.json()["data"]
    
    def get_name(self) -> str:
        return "OKX"
    
    def get_chain(self) -> str:
        return self.chain
    
    def get_available_markets(self) -> Dict[str, Dict]:
        """Fetch available trading markets from OKX"""
        try:
            markets = self._make_request("GET", "/public/instruments", {"instType": "SPOT"})
            return {
                market["instId"]: {
                    "base_asset": market["baseCcy"],
                    "quote_asset": market["quoteCcy"],
                    "min_price": float(market["tickSz"]),
                    "max_price": float(market["tickSz"]),
                    "min_amount": float(market["lotSz"]),
                    "max_amount": float(market["lotSz"]),
                }
                for market in markets
            }
        except Exception as e:
            raise Exception(f"Failed to fetch markets: {str(e)}")
    
    def get_balances(self, wallet_address: ChecksumAddress) -> Dict[str, float]:
        """Fetch account balances from OKX"""
        try:
            balances = self._make_request("GET", "/account/balance", {"ccy": "ALL"})
            return {
                balance["ccy"]: float(balance["availBal"])
                for balance in balances[0]["details"]
            }
        except Exception as e:
            raise Exception(f"Failed to fetch balances: {str(e)}")
    
    def get_order_book(self, market: str) -> Dict:
        """Fetch order book for a specific market"""
        try:
            order_book = self._make_request("GET", "/market/books", {"instId": market, "sz": "400"})
            return {
                "bids": [[float(price), float(amount)] for price, amount in order_book[0]["bids"]],
                "asks": [[float(price), float(amount)] for price, amount in order_book[0]["asks"]],
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
        """Place a limit order on OKX"""
        try:
            order = self._make_request("POST", "/trade/order", {
                "instId": market,
                "tdMode": "cash",
                "side": side.lower(),
                "ordType": "limit",
                "px": str(price),
                "sz": str(amount),
                "ccy": market.split("-")[0]
            })
            return order[0]["ordId"]
        except Exception as e:
            raise Exception(f"Failed to place order: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on OKX"""
        try:
            self._make_request("POST", "/trade/cancel-order", {"ordId": order_id})
            return True
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")