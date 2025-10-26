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

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """SMA（単純移動平均）を計算"""
        if len(prices) < period:
            return None
        df = pd.DataFrame({'price': prices})
        sma = df['price'].rolling(window=period).mean()
        return float(sma.iloc[-1])

    @staticmethod
    def calculate_sma_slope(prices: List[float], period: int, lookback: int = 5) -> Optional[float]:
        """SMAの傾き（slope）を計算

        Args:
            prices: 価格リスト
            period: MA期間
            lookback: 傾き計算用の遡り期間

        Returns:
            傾き（正=上向き、負=下向き、0付近=横ばい）
        """
        if len(prices) < period + lookback:
            return None

        df = pd.DataFrame({'price': prices})
        sma = df['price'].rolling(window=period).mean()

        # 最新のSMAと lookback 前のSMAを比較
        current_sma = float(sma.iloc[-1])
        past_sma = float(sma.iloc[-(lookback + 1)])

        # 傾きを百分率で返す
        slope = ((current_sma - past_sma) / past_sma) * 100
        return slope

    @staticmethod
    def detect_support_resistance(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float,
        lookback: int = 100,
        tolerance_pct: float = 1.0
    ) -> Dict:
        """
        支持線/抵抗線を検出

        Args:
            highs: 高値リスト
            lows: 安値リスト
            closes: 終値リスト
            current_price: 現在価格
            lookback: 遡る期間
            tolerance_pct: クラスタリング許容範囲（%）

        Returns:
            {
                'support_levels': [(price, strength, distance), ...],
                'resistance_levels': [(price, strength, distance), ...],
                'nearest_support': price,
                'nearest_resistance': price
            }
        """
        if len(highs) < lookback or len(lows) < lookback:
            return {
                'support_levels': [],
                'resistance_levels': [],
                'nearest_support': None,
                'nearest_resistance': None
            }

        # 直近lookback本のデータを使用
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_closes = closes[-lookback:]

        # スイングハイとスイングローを検出（局所的な最高値/最安値）
        swing_highs = []
        swing_lows = []

        for i in range(2, len(recent_highs) - 2):
            # スイングハイ: 前後2本より高い
            if (recent_highs[i] > recent_highs[i-1] and
                recent_highs[i] > recent_highs[i-2] and
                recent_highs[i] > recent_highs[i+1] and
                recent_highs[i] > recent_highs[i+2]):
                swing_highs.append(recent_highs[i])

            # スイングロー: 前後2本より低い
            if (recent_lows[i] < recent_lows[i-1] and
                recent_lows[i] < recent_lows[i-2] and
                recent_lows[i] < recent_lows[i+1] and
                recent_lows[i] < recent_lows[i+2]):
                swing_lows.append(recent_lows[i])

        # 価格帯でクラスタリング（±tolerance_pct以内を同一レベル）
        def cluster_levels(levels):
            if not levels:
                return []

            clusters = []
            sorted_levels = sorted(levels)

            for level in sorted_levels:
                # 既存クラスタに追加できるか確認
                added = False
                for cluster in clusters:
                    cluster_avg = sum(cluster) / len(cluster)
                    if abs((level - cluster_avg) / cluster_avg * 100) <= tolerance_pct:
                        cluster.append(level)
                        added = True
                        break

                if not added:
                    clusters.append([level])

            # 各クラスタの平均価格とstrength（接触回数）を計算
            result = []
            for cluster in clusters:
                avg_price = sum(cluster) / len(cluster)
                strength = len(cluster)
                distance_pct = ((current_price - avg_price) / avg_price * 100)
                result.append((avg_price, strength, distance_pct))

            return result

        # クラスタリング実行
        resistance_clusters = cluster_levels(swing_highs)
        support_clusters = cluster_levels(swing_lows)

        # Strengthでソート（強い順）
        resistance_clusters.sort(key=lambda x: x[1], reverse=True)
        support_clusters.sort(key=lambda x: x[1], reverse=True)

        # 上位3つのみ保持
        resistance_levels = resistance_clusters[:3]
        support_levels = support_clusters[:3]

        # 現在価格より上の抵抗線、下の支持線のみフィルタ
        resistance_above = [(p, s, d) for p, s, d in resistance_levels if p > current_price]
        support_below = [(p, s, d) for p, s, d in support_levels if p < current_price]

        # 最も近い支持線/抵抗線を見つける
        nearest_support = min(support_below, key=lambda x: abs(x[2]))[0] if support_below else None
        nearest_resistance = min(resistance_above, key=lambda x: abs(x[2]))[0] if resistance_above else None

        return {
            'support_levels': support_below,
            'resistance_levels': resistance_above,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance
        }

    @staticmethod
    def analyze_price_structure(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        lookback: int = 50
    ) -> Dict:
        """
        価格構造を分析（Higher Highs/Lower Lows/Higher Lows/Lower Highs検出）

        Args:
            highs: 高値リスト
            lows: 安値リスト
            closes: 終値リスト
            lookback: 遡る期間

        Returns:
            {
                'structure': 'UPTREND' | 'DOWNTREND' | 'RANGE',
                'pattern': 'HH+HL' | 'LL+LH' | 'MIXED',
                'trend_strength': 0-100 (強度スコア),
                'swing_highs': [(index, price), ...],
                'swing_lows': [(index, price), ...],
                'hh_count': int,  # Higher Highs count
                'll_count': int,  # Lower Lows count
                'hl_count': int,  # Higher Lows count
                'lh_count': int   # Lower Highs count
            }
        """
        if len(highs) < lookback or len(lows) < lookback or len(closes) < lookback:
            return {
                'structure': 'UNCLEAR',
                'pattern': 'INSUFFICIENT_DATA',
                'trend_strength': 0,
                'swing_highs': [],
                'swing_lows': [],
                'hh_count': 0,
                'll_count': 0,
                'hl_count': 0,
                'lh_count': 0
            }

        # 直近lookback本のデータを使用
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_closes = closes[-lookback:]

        # スイングハイとスイングローを検出（前後3本より高い/低い）
        swing_highs = []
        swing_lows = []

        for i in range(3, len(recent_highs) - 3):
            # スイングハイ: 前後3本より高い
            if (recent_highs[i] > recent_highs[i-1] and
                recent_highs[i] > recent_highs[i-2] and
                recent_highs[i] > recent_highs[i-3] and
                recent_highs[i] > recent_highs[i+1] and
                recent_highs[i] > recent_highs[i+2] and
                recent_highs[i] > recent_highs[i+3]):
                swing_highs.append((i, recent_highs[i]))

            # スイングロー: 前後3本より低い
            if (recent_lows[i] < recent_lows[i-1] and
                recent_lows[i] < recent_lows[i-2] and
                recent_lows[i] < recent_lows[i-3] and
                recent_lows[i] < recent_lows[i+1] and
                recent_lows[i] < recent_lows[i+2] and
                recent_lows[i] < recent_lows[i+3]):
                swing_lows.append((i, recent_lows[i]))

        # Higher Highs (HH) / Lower Highs (LH) をカウント
        hh_count = 0
        lh_count = 0
        for i in range(1, len(swing_highs)):
            if swing_highs[i][1] > swing_highs[i-1][1]:
                hh_count += 1
            elif swing_highs[i][1] < swing_highs[i-1][1]:
                lh_count += 1

        # Higher Lows (HL) / Lower Lows (LL) をカウント
        hl_count = 0
        ll_count = 0
        for i in range(1, len(swing_lows)):
            if swing_lows[i][1] > swing_lows[i-1][1]:
                hl_count += 1
            elif swing_lows[i][1] < swing_lows[i-1][1]:
                ll_count += 1

        # 価格構造パターンを判定
        pattern = 'MIXED'
        structure = 'RANGE'

        # 上昇トレンド判定: HH + HL が優勢
        if hh_count > 0 and hl_count > 0 and (hh_count + hl_count) > (lh_count + ll_count):
            pattern = 'HH+HL'
            structure = 'UPTREND'

        # 下降トレンド判定: LL + LH が優勢
        elif ll_count > 0 and lh_count > 0 and (ll_count + lh_count) > (hh_count + hl_count):
            pattern = 'LL+LH'
            structure = 'DOWNTREND'

        # トレンド強度を計算（0-100）
        total_swings = hh_count + lh_count + hl_count + ll_count

        if total_swings == 0:
            trend_strength = 0
        else:
            if structure == 'UPTREND':
                # 上昇トレンド強度: (HH + HL) の割合 × 一貫性
                consistency = (hh_count + hl_count) / total_swings
                trend_strength = min(100, int(consistency * 100))
            elif structure == 'DOWNTREND':
                # 下降トレンド強度: (LL + LH) の割合 × 一貫性
                consistency = (ll_count + lh_count) / total_swings
                trend_strength = min(100, int(consistency * 100))
            else:
                # レンジの場合は低い強度
                trend_strength = max(0, 50 - abs(hh_count - ll_count) * 5)

        return {
            'structure': structure,
            'pattern': pattern,
            'trend_strength': trend_strength,
            'swing_highs': swing_highs[-5:],  # 直近5つのみ返す
            'swing_lows': swing_lows[-5:],
            'hh_count': hh_count,
            'll_count': ll_count,
            'hl_count': hl_count,
            'lh_count': lh_count
        }

    @staticmethod
    def classify_market_regime(
        price: float,
        ma_50: Optional[float],
        ma_200: Optional[float],
        ma_50_slope: Optional[float],
        ma_200_slope: Optional[float]
    ) -> str:
        """市場レジーム（トレンド/レンジ）を分類

        Module 1の実装：
        - UPTREND: 価格が両MA上、MA上向き、50MA > 200MA
        - DOWNTREND: 価格が両MA下、MA下向き、50MA < 200MA
        - RANGE: 上記以外
        - UNCLEAR: データ不足

        Args:
            price: 現在価格
            ma_50: 50期間MA
            ma_200: 200期間MA
            ma_50_slope: 50MA の傾き
            ma_200_slope: 200MA の傾き

        Returns:
            "UPTREND" | "DOWNTREND" | "RANGE" | "UNCLEAR"
        """
        # データ不足チェック
        if ma_50 is None or ma_200 is None or ma_50_slope is None or ma_200_slope is None:
            return "UNCLEAR"

        # 上昇トレンドの条件
        uptrend_conditions = [
            price > ma_50,              # 価格が50MA上
            price > ma_200,             # 価格が200MA上
            ma_50 > ma_200,             # ゴールデンクロス状態
            ma_50_slope > 0.1,          # 50MA が上向き
            ma_200_slope > 0.05         # 200MA が上向き（緩やか可）
        ]

        # 下降トレンドの条件
        downtrend_conditions = [
            price < ma_50,              # 価格が50MA下
            price < ma_200,             # 価格が200MA下
            ma_50 < ma_200,             # デッドクロス状態
            ma_50_slope < -0.1,         # 50MA が下向き
            ma_200_slope < -0.05        # 200MA が下向き（緩やか可）
        ]

        # 上昇トレンド：5条件中4つ以上
        if sum(uptrend_conditions) >= 4:
            return "UPTREND"

        # 下降トレンド：5条件中4つ以上
        if sum(downtrend_conditions) >= 4:
            return "DOWNTREND"

        # それ以外はレンジ
        return "RANGE"


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

                # MODULE 1: 市場レジーム識別用の50MA/200MA（長期データが必要）
                # 全データを使用（最大1000ポイント = 50時間分）
                all_interval_prices = [d['price'] for d in interval_history]

                # 50MA と 200MA を計算
                ma_50 = self.indicators.calculate_sma(all_interval_prices, 50)
                ma_200 = self.indicators.calculate_sma(all_interval_prices, 200)

                result['ma_50_4h'] = ma_50
                result['ma_200_4h'] = ma_200

                # MA の傾きを計算（5データポイント = 15分）
                ma_50_slope = self.indicators.calculate_sma_slope(all_interval_prices, 50, 5)
                ma_200_slope = self.indicators.calculate_sma_slope(all_interval_prices, 200, 5)

                result['ma_50_slope'] = ma_50_slope
                result['ma_200_slope'] = ma_200_slope

                # 市場レジームを分類
                market_regime = self.indicators.classify_market_regime(
                    current_price,
                    ma_50,
                    ma_200,
                    ma_50_slope,
                    ma_200_slope
                )

                result['market_regime'] = market_regime
        else:
            # データポイント数を追加（デバッグ用）
            result['data_points'] = len(interval_history)

        return result

    def get_all_market_data_with_indicators(self) -> Dict[str, Dict]:
        """全銘柄の市場データとテクニカル指標を取得"""
        return {symbol: self.get_market_data_with_indicators(symbol) for symbol in self.symbols}

