"""
Hyperliquid取引所API連携モジュール
"""
import json
import hmac
import hashlib
import websocket
import threading
import requests
from datetime import datetime
from typing import Dict, List, Optional


class HyperliquidAPI:
    """Hyperliquid取引所APIとの連携クラス"""
    
    # ここにHyperliquid APIキーを直接入力してください
    HYPERLIQUID_API_KEY = "your-hyperliquid-api-key-here"
    HYPERLIQUID_API_SECRET = "your-hyperliquid-api-secret-here"
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        # api_keyが指定されていない場合は、クラス変数を使用
        self.api_key = api_key if api_key else self.HYPERLIQUID_API_KEY
        self.api_secret = api_secret if api_secret else self.HYPERLIQUID_API_SECRET
        self.testnet = testnet
        
        # エンドポイント設定
        if testnet:
            self.base_url = "https://api.hyperliquid-testnet.xyz"
            self.ws_url = "wss://api.hyperliquid-testnet.xyz/ws"
        else:
            self.base_url = "https://api.hyperliquid.xyz"
            self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        self.ws = None
        self.market_data = {}
        self.ws_thread = None
        
    def _sign_request(self, data: Dict) -> str:
        """リクエストに署名を追加"""
        message = json.dumps(data, separators=(',', ':'))
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def get_market_data(self, symbols: List[str]) -> Dict:
        """
        市場データを取得
        
        Args:
            symbols: 取得する銘柄リスト（例: ["BTC", "ETH", "SOL"]）
            
        Returns:
            各銘柄の価格データ
        """
        try:
            response = requests.post(
                f"{self.base_url}/info",
                json={"type": "metaAndAssetCtxs"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            market_data = {}
            for asset in data[1]:
                symbol = asset['name']
                if symbol in symbols:
                    market_data[symbol] = {
                        'price': float(asset['markPx']),
                        'volume_24h': float(asset.get('dayNtlVlm', 0)),
                        'funding_rate': float(asset.get('funding', 0)),
                        'open_interest': float(asset.get('openInterest', 0)),
                        'timestamp': datetime.now().isoformat()
                    }
            
            return market_data
            
        except Exception as e:
            print(f"市場データ取得エラー: {e}")
            return {}
    
    def place_order(self, symbol: str, is_buy: bool, size: float, price: Optional[float] = None, 
                    leverage: int = 1, reduce_only: bool = False) -> Dict:
        """
        注文を発注
        
        Args:
            symbol: 銘柄（例: "BTC"）
            is_buy: True=買い、False=売り
            size: 数量（USD建て）
            price: 指値価格（Noneの場合は成行）
            leverage: レバレッジ倍率
            reduce_only: ポジション縮小のみ
            
        Returns:
            注文結果
        """
        try:
            order_data = {
                "type": "order",
                "orders": [{
                    "asset": symbol,
                    "isBuy": is_buy,
                    "limitPx": str(price) if price else "0",
                    "sz": str(size),
                    "reduceOnly": reduce_only,
                    "orderType": {"limit": {"tif": "Gtc"}} if price else {"market": {}}
                }],
                "grouping": "na"
            }
            
            # 署名を追加
            signature = self._sign_request(order_data)
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
                "X-Signature": signature
            }
            
            response = requests.post(
                f"{self.base_url}/exchange",
                json=order_data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "order_id": result.get("statuses", [{}])[0].get("filled"),
                "data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_positions(self) -> Dict:
        """現在のポジションを取得"""
        try:
            response = requests.post(
                f"{self.base_url}/info",
                json={
                    "type": "clearinghouseState",
                    "user": self.api_key
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            positions = {}
            if 'assetPositions' in data:
                for pos in data['assetPositions']:
                    if float(pos['position']['szi']) != 0:
                        symbol = pos['position']['coin']
                        positions[symbol] = {
                            'size': float(pos['position']['szi']),
                            'entry_price': float(pos['position']['entryPx']),
                            'unrealized_pnl': float(pos['position']['unrealizedPnl']),
                            'leverage': float(pos['position'].get('leverage', 1)),
                            'liquidation_price': float(pos['position'].get('liquidationPx', 0))
                        }
            
            return positions
            
        except Exception as e:
            print(f"ポジション取得エラー: {e}")
            return {}
    
    def get_account_value(self) -> Dict:
        """口座残高と証拠金情報を取得"""
        try:
            response = requests.post(
                f"{self.base_url}/info",
                json={
                    "type": "clearinghouseState",
                    "user": self.api_key
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'account_value': float(data.get('marginSummary', {}).get('accountValue', 0)),
                'total_margin_used': float(data.get('marginSummary', {}).get('totalMarginUsed', 0)),
                'withdrawable': float(data.get('withdrawable', 0))
            }
            
        except Exception as e:
            print(f"口座情報取得エラー: {e}")
            return {'account_value': 0, 'total_margin_used': 0, 'withdrawable': 0}
    
    def start_websocket(self, symbols: List[str], callback):
        """
        WebSocketで市場データのリアルタイム受信を開始
        
        Args:
            symbols: 購読する銘柄リスト
            callback: データ受信時のコールバック関数
        """
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if 'channel' in data and data['channel'] == 'trades':
                    callback(data)
            except Exception as e:
                print(f"WebSocketメッセージ処理エラー: {e}")
        
        def on_error(ws, error):
            print(f"WebSocketエラー: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket接続終了")
        
        def on_open(ws):
            # 購読メッセージを送信
            for symbol in symbols:
                subscribe_msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "trades",
                        "coin": symbol
                    }
                }
                ws.send(json.dumps(subscribe_msg))
            print(f"WebSocket接続開始: {symbols}")
        
        def run_ws():
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            self.ws.run_forever()
        
        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()
    
    def stop_websocket(self):
        """WebSocket接続を停止"""
        if self.ws:
            self.ws.close()

