"""
市場データ管理モジュール
"""
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from hyperliquid_api import HyperliquidAPI


class TechnicalIndicators:
    """テクニカル指標計算クラス"""

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """EMA（指数移動平均）を計算"""
        if len(prices) < period:
            return None
        df = pd.DataFrame({'price': prices})
        ema = df['price'].ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])

    @staticmethod
    def calculate_ema_series(prices: List[float], period: int, count: int = 10) -> List[float]:
        """EMAの時系列を計算（最新count個）"""
        if len(prices) < period:
            return []
        df = pd.DataFrame({'price': prices})
        ema = df['price'].ewm(span=period, adjust=False).mean()
        return [float(x) for x in ema.iloc[-count:].tolist()]

    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict:
        """MACDを計算（12, 26, 9）"""
        if len(prices) < 26:
            return {'macd': None, 'signal': None, 'histogram': None}

        df = pd.DataFrame({'price': prices})
        ema12 = df['price'].ewm(span=12, adjust=False).mean()
        ema26 = df['price'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal

        return {
            'macd': float(macd.iloc[-1]),
            'signal': float(signal.iloc[-1]),
            'histogram': float(histogram.iloc[-1])
        }

    @staticmethod
    def calculate_macd_series(prices: List[float], count: int = 10) -> List[float]:
        """MACDの時系列を計算（最新count個）"""
        if len(prices) < 26:
            return []

        df = pd.DataFrame({'price': prices})
        ema12 = df['price'].ewm(span=12, adjust=False).mean()
        ema26 = df['price'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26

        return [float(x) for x in macd.iloc[-count:].tolist()]

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """RSIを計算"""
        if len(prices) < period + 1:
            return None

        df = pd.DataFrame({'price': prices})
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1])

    @staticmethod
    def calculate_rsi_series(prices: List[float], period: int, count: int = 10) -> List[float]:
        """RSIの時系列を計算（最新count個）"""
        if len(prices) < period + 1:
            return []

        df = pd.DataFrame({'price': prices})
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return [float(x) for x in rsi.iloc[-count:].dropna().tolist()]

    @staticmethod
    def calculate_atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> Optional[float]:
        """ATR（Average True Range）を計算"""
        if len(high) < period + 1 or len(low) < period + 1 or len(close) < period:
            return None

        df = pd.DataFrame({'high': high, 'low': low, 'close': close})
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        atr = df['tr'].rolling(window=period).mean()

        return float(atr.iloc[-1])


class MarketDataManager:
    """市場データのリアルタイム管理クラス"""

    def __init__(self, hyperliquid_api: HyperliquidAPI, symbols: List[str]):
        self.api = hyperliquid_api
        self.symbols = symbols
        self.current_prices = {}
        self.price_history = {symbol: [] for symbol in symbols}
        self.max_history_size = 1000
        self.update_callbacks = []

        # テクニカル指標用のデータ管理
        self.indicators = TechnicalIndicators()
        self.interval_data = {symbol: [] for symbol in symbols}  # 3分間隔データ
        self.last_interval_time = {}
        self.interval_seconds = 180  # 3分 = 180秒

        # Open Interest と Funding Rate のキャッシュ
        self.oi_funding_cache = {}
        
    def start_monitoring(self):
        """市場データの監視を開始"""
        # WebSocketでリアルタイムデータを受信
        self.api.start_websocket(self.symbols, self._on_market_update)
        
        # 定期的にRESTAPIでもデータを取得（バックアップ）
        self._start_periodic_update()
    
    def _on_market_update(self, data: Dict):
        """WebSocketからのデータ更新を処理"""
        if 'data' in data and len(data['data']) > 0:
            trade = data['data'][0]
            symbol = trade.get('coin', '')
            price = float(trade.get('px', 0))
            
            if symbol in self.symbols:
                self.current_prices[symbol] = price
                self._add_to_history(symbol, price)
                self._notify_callbacks()
    
    def _start_periodic_update(self):
        """定期的にRESTAPIでデータを更新"""
        def periodic_fetch():
            while True:
                try:
                    market_data = self.api.get_market_data(self.symbols)
                    for symbol, data in market_data.items():
                        self.current_prices[symbol] = data['price']
                        self._add_to_history(symbol, data['price'])

                        # Open Interest と Funding Rate をキャッシュ
                        self.oi_funding_cache[symbol] = {
                            'open_interest': data.get('open_interest', 0),
                            'funding_rate': data.get('funding_rate', 0)
                        }

                        # 3分間隔データの保存
                        self._add_interval_data(symbol, data['price'])

                    self._notify_callbacks()
                except Exception as e:
                    print(f"定期更新エラー: {e}")
                time.sleep(60)  # 60秒ごとに更新

        thread = threading.Thread(target=periodic_fetch, daemon=True)
        thread.start()
    
    def _add_to_history(self, symbol: str, price: float):
        """価格履歴に追加"""
        if symbol in self.price_history:
            self.price_history[symbol].append({
                'price': price,
                'timestamp': datetime.now().isoformat()
            })
            # 履歴サイズを制限
            if len(self.price_history[symbol]) > self.max_history_size:
                self.price_history[symbol].pop(0)

    def _add_interval_data(self, symbol: str, price: float):
        """3分間隔でデータを保存"""
        current_time = time.time()

        # 初回または3分経過している場合
        if symbol not in self.last_interval_time or \
           current_time - self.last_interval_time.get(symbol, 0) >= self.interval_seconds:

            self.interval_data[symbol].append({
                'price': price,
                'timestamp': datetime.now().isoformat(),
                'time': current_time
            })

            self.last_interval_time[symbol] = current_time

            # 最大100データポイントを保持（5時間分）
            if len(self.interval_data[symbol]) > 100:
                self.interval_data[symbol].pop(0)
    
    def _notify_callbacks(self):
        """登録されたコールバックに通知"""
        for callback in self.update_callbacks:
            try:
                callback(self.current_prices)
            except Exception as e:
                print(f"コールバック実行エラー: {e}")
    
    def add_callback(self, callback):
        """データ更新時のコールバックを登録"""
        self.update_callbacks.append(callback)
    
    def get_current_prices(self) -> Dict[str, float]:
        """現在の価格を取得"""
        return self.current_prices.copy()
    
    def get_price_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """指定銘柄の価格履歴を取得"""
        if symbol in self.price_history:
            return self.price_history[symbol][-limit:]
        return []
    
    def get_market_summary(self) -> Dict:
        """市場サマリーを取得"""
        summary = {}
        for symbol in self.symbols:
            history = self.price_history.get(symbol, [])
            if len(history) > 0:
                prices = [h['price'] for h in history]
                current = prices[-1] if prices else 0
                high_24h = max(prices) if prices else 0
                low_24h = min(prices) if prices else 0
                change_24h = ((current - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] > 0 else 0

                summary[symbol] = {
                    'current': current,
                    'high_24h': high_24h,
                    'low_24h': low_24h,
                    'change_24h': change_24h,
                    'data_points': len(history)
                }
        return summary

    def get_market_data_with_indicators(self, symbol: str) -> Dict:
        """指定銘柄の市場データとテクニカル指標を取得"""
        if symbol not in self.symbols:
            return {}

        # 基本的な価格情報
        history = self.price_history.get(symbol, [])
        interval_history = self.interval_data.get(symbol, [])

        if not history:
            return {}

        prices = [h['price'] for h in history]
        current_price = prices[-1] if prices else 0
        high_24h = max(prices) if prices else 0
        low_24h = min(prices) if prices else 0
        change_24h = ((current_price - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] > 0 else 0

        result = {
            'price': current_price,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'change_24h': change_24h,
        }

        # Open Interest と Funding Rate
        if symbol in self.oi_funding_cache:
            result['open_interest'] = self.oi_funding_cache[symbol]['open_interest']
            result['funding_rate'] = self.oi_funding_cache[symbol]['funding_rate']

        # テクニカル指標（3分間隔データから計算）
        if len(interval_history) >= 20:
            interval_prices = [d['price'] for d in interval_history]

            # 価格の時系列（最新10データポイント）
            result['price_series'] = interval_prices[-10:]

            # EMA (20期間) の時系列
            result['ema_20_series'] = self.indicators.calculate_ema_series(interval_prices, 20, 10)
            result['ema_20'] = result['ema_20_series'][-1] if result['ema_20_series'] else None

            # MACD の時系列
            result['macd_series'] = self.indicators.calculate_macd_series(interval_prices, 10)
            result['macd'] = result['macd_series'][-1] if result['macd_series'] else None

            # RSI (7期間) の時系列
            result['rsi_7_series'] = self.indicators.calculate_rsi_series(interval_prices, 7, 10)
            result['rsi_7'] = result['rsi_7_series'][-1] if result['rsi_7_series'] else None

            # RSI (14期間) の時系列
            result['rsi_14_series'] = self.indicators.calculate_rsi_series(interval_prices, 14, 10)
            result['rsi_14'] = result['rsi_14_series'][-1] if result['rsi_14_series'] else None

            # 4時間足コンテキスト（80個の3分データ = 4時間）
            if len(interval_history) >= 80:
                four_hour_prices = [d['price'] for d in interval_history[-80:]]

                result['ema_20_4h'] = self.indicators.calculate_ema(four_hour_prices, 20)
                result['ema_50_4h'] = self.indicators.calculate_ema(four_hour_prices, 50)
                result['macd_4h'] = self.indicators.calculate_macd(four_hour_prices)
                result['rsi_14_4h'] = self.indicators.calculate_rsi(four_hour_prices, 14)

                # ATR計算（高値・安値が必要だが、ここではpriceを代用）
                result['atr_14_4h'] = self.indicators.calculate_atr(
                    four_hour_prices, four_hour_prices, four_hour_prices, 14
                )
        else:
            # データポイント数を追加（デバッグ用）
            result['data_points'] = len(interval_history)

        return result

    def get_all_market_data_with_indicators(self) -> Dict[str, Dict]:
        """全銘柄の市場データとテクニカル指標を取得"""
        return {symbol: self.get_market_data_with_indicators(symbol) for symbol in self.symbols}

