"""
シミュレーションモード
実際の取引所APIを使わずに、市場データのみを取得してトレーディングをシミュレート
"""
import time
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional
from market_data import TechnicalIndicators


class SimulationExchange:
    """シミュレーション用の仮想取引所"""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.positions = {}  # {symbol: {'quantity': float, 'entry_price': float}}
        self.trade_history = []
        
    def get_market_data(self, symbols: List[str]) -> Dict:
        """
        無料の市場データAPIから価格を取得
        Binance Public API（認証不要）を使用
        """
        market_data = {}
        
        try:
            # Binance Public APIで価格を取得
            for symbol in symbols:
                try:
                    # BinanceのシンボルフォーマットにUSDTを追加
                    binance_symbol = f"{symbol}USDT"
                    
                    # 24時間の価格変動データを取得
                    ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
                    response = requests.get(ticker_url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        market_data[symbol] = {
                            'price': float(data['lastPrice']),
                            'volume_24h': float(data['volume']),
                            'price_change_24h': float(data['priceChangePercent']),
                            'high_24h': float(data['highPrice']),
                            'low_24h': float(data['lowPrice']),
                            'timestamp': datetime.now().isoformat()
                        }
                        print(f"✅ {symbol}: ${float(data['lastPrice']):.2f} ({float(data['priceChangePercent']):+.2f}%)")
                    else:
                        print(f"⚠️ {symbol}: データ取得失敗")
                        
                    # API制限を避けるために少し待機
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️ {symbol}のデータ取得エラー: {e}")
                    continue
            
            return market_data
            
        except Exception as e:
            print(f"❌ 市場データ取得エラー: {e}")
            return {}
    
    def place_order(self, symbol: str, is_buy: bool, amount_usd: float, 
                   price: float, leverage: int = 1) -> Dict:
        """
        シミュレーション注文を実行
        
        Args:
            symbol: 銘柄
            is_buy: True=買い、False=売り
            amount_usd: 取引金額（USD）
            price: 現在価格
            leverage: レバレッジ倍率
            
        Returns:
            注文結果
        """
        try:
            if is_buy:
                # 買い注文
                required_cash = amount_usd / leverage
                
                if required_cash > self.cash:
                    return {
                        "success": False,
                        "reason": f"資金不足: 必要${required_cash:.2f} > 利用可能${self.cash:.2f}"
                    }
                
                # ポジションを追加
                quantity = amount_usd / price
                
                if symbol in self.positions:
                    # 既存ポジションに追加（平均価格を計算）
                    old_qty = self.positions[symbol]['quantity']
                    old_price = self.positions[symbol]['entry_price']
                    old_time = self.positions[symbol]['entry_time']  # 既存のエントリー時刻を保持
                    new_qty = old_qty + quantity
                    new_avg_price = (old_qty * old_price + quantity * price) / new_qty

                    self.positions[symbol] = {
                        'quantity': new_qty,
                        'entry_price': new_avg_price,
                        'leverage': leverage,
                        'entry_time': old_time  # 最初のエントリー時刻を保持
                    }
                else:
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'entry_price': price,
                        'leverage': leverage,
                        'entry_time': datetime.now()  # エントリー時刻を記録
                    }
                
                self.cash -= required_cash
                
                trade = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'BUY',
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'amount_usd': amount_usd,
                    'leverage': leverage,
                    'cash_used': required_cash
                }
                self.trade_history.append(trade)
                
                return {
                    "success": True,
                    "trade": trade,
                    "message": f"買い注文成功: {quantity:.6f} {symbol} @ ${price:.2f}"
                }
                
            else:
                # 売り注文
                if symbol not in self.positions:
                    return {
                        "success": False,
                        "reason": f"ポジションなし: {symbol}"
                    }
                
                position = self.positions[symbol]
                sell_quantity = amount_usd / price
                
                if sell_quantity > position['quantity']:
                    sell_quantity = position['quantity']
                    amount_usd = sell_quantity * price
                
                # 損益を計算
                pnl = (price - position['entry_price']) * sell_quantity * position['leverage']
                pnl_percentage = ((price / position['entry_price']) - 1) * 100 * position['leverage']
                
                # 現金を戻す
                cash_returned = (amount_usd / position['leverage']) + pnl
                self.cash += cash_returned
                
                # ポジションを更新
                position['quantity'] -= sell_quantity
                if position['quantity'] < 0.0001:  # ほぼゼロの場合は削除
                    del self.positions[symbol]
                
                trade = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'SELL',
                    'symbol': symbol,
                    'quantity': sell_quantity,
                    'price': price,
                    'amount_usd': amount_usd,
                    'leverage': position['leverage'],
                    'pnl': pnl,
                    'pnl_percentage': pnl_percentage,
                    'cash_returned': cash_returned
                }
                self.trade_history.append(trade)
                
                return {
                    "success": True,
                    "trade": trade,
                    "pnl": pnl,
                    "pnl_percentage": pnl_percentage,
                    "message": f"売り注文成功: {sell_quantity:.6f} {symbol} @ ${price:.2f} | 損益: ${pnl:.2f} ({pnl_percentage:+.2f}%)"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_positions(self) -> Dict:
        """現在のポジションを取得"""
        return self.positions.copy()
    
    def get_account_value(self, current_prices: Dict) -> Dict:
        """口座価値を計算"""
        positions_value = 0.0
        
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]['price']
                position_value = pos['quantity'] * current_price
                
                # レバレッジポジションの含み損益を計算
                unrealized_pnl = (current_price - pos['entry_price']) * pos['quantity'] * pos['leverage']
                positions_value += (position_value / pos['leverage']) + unrealized_pnl
        
        total_value = self.cash + positions_value
        
        return {
            'cash': self.cash,
            'positions_value': positions_value,
            'total_value': total_value,
            'roi': ((total_value / self.initial_balance) - 1) * 100
        }
    
    def get_position_details(self, symbol: str, current_price: float) -> Dict:
        """特定ポジションの詳細を取得"""
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        current_value = pos['quantity'] * current_price
        entry_value = pos['quantity'] * pos['entry_price']
        unrealized_pnl = (current_price - pos['entry_price']) * pos['quantity'] * pos['leverage']
        unrealized_pnl_pct = ((current_price / pos['entry_price']) - 1) * 100 * pos['leverage']

        # 保有時間を計算
        entry_time = pos.get('entry_time', datetime.now())
        holding_duration = datetime.now() - entry_time
        holding_minutes = int(holding_duration.total_seconds() / 60)

        # 時間表示用の文字列を作成
        if holding_minutes < 60:
            holding_time_str = f"{holding_minutes}M"
        else:
            hours = holding_minutes // 60
            minutes = holding_minutes % 60
            holding_time_str = f"{hours}H {minutes}M"

        return {
            'symbol': symbol,
            'quantity': pos['quantity'],
            'entry_price': pos['entry_price'],
            'current_price': current_price,
            'leverage': pos['leverage'],
            'entry_value': entry_value,
            'current_value': current_value,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_percentage': unrealized_pnl_pct,
            'holding_time': holding_time_str,
            'holding_minutes': holding_minutes
        }


class MarketDataFetcher:
    """市場データ取得クラス（無料API使用）"""
    
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.last_update = None
        self.cache = {}
        self.cache_duration = 10  # 秒
        
    def get_current_prices(self) -> Dict:
        """現在の市場価格を取得（キャッシュ付き）"""
        now = datetime.now()
        
        # キャッシュが有効な場合は使用
        if self.last_update and self.cache:
            elapsed = (now - self.last_update).total_seconds()
            if elapsed < self.cache_duration:
                return self.cache
        
        # Binance Public APIから価格を取得
        exchange = SimulationExchange()
        market_data = exchange.get_market_data(self.symbols)
        
        if market_data:
            self.cache = market_data
            self.last_update = now
        
        return self.cache if self.cache else {}
    
    def get_market_summary(self) -> Dict:
        """市場サマリーを取得"""
        prices = self.get_current_prices()
        summary = {}

        for symbol, data in prices.items():
            summary[symbol] = {
                'current': data['price'],
                'change_24h': data.get('price_change_24h', 0),
                'high_24h': data.get('high_24h', 0),
                'low_24h': data.get('low_24h', 0),
                'volume_24h': data.get('volume_24h', 0)
            }

        return summary


class MarketDataFetcherEnhanced(MarketDataFetcher):
    """
    テクニカル指標を含む拡張版市場データ取得クラス
    Binance Public APIから3分足キャンドルデータを取得し、
    EMA、MACD、RSI等のテクニカル指標を計算
    """

    def __init__(self, symbols: List[str]):
        super().__init__(symbols)

        # テクニカル指標計算クラス
        self.indicators = TechnicalIndicators()

        # キャンドルデータの保存（symbol: [candle_data]）
        self.candle_data = {symbol: [] for symbol in symbols}

        # 4時間足キャンドルデータの保存（マーケットレジーム判定用）
        self.candle_data_4h = {symbol: [] for symbol in symbols}

        # 1時間足キャンドルデータの保存（戦略方向判定用）
        self.candle_data_1h = {symbol: [] for symbol in symbols}

        # 更新管理
        self.update_interval = 180  # 3分 = 180秒
        self.last_candle_update = {}
        self.is_initialized = False
        self.update_thread = None
        self.running = False

        # 初期データを取得
        print("📊 過去の市場データを取得中...")
        self._fetch_initial_data()

        # 4時間足データを取得
        print("📊 4時間足データを取得中（マーケットレジーム判定用）...")
        self._fetch_4h_initial_data()

        # 1時間足データを取得
        print("📊 1時間足データを取得中（戦略方向判定用）...")
        self._fetch_1h_initial_data()

        # バックグラウンド更新を開始
        self._start_background_update()

    def _fetch_initial_data(self):
        """起動時に過去のキャンドルデータを一括取得"""
        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                # 過去500本の3分足キャンドルを取得（25時間分 - 50MA/200MA計算に十分）
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': '3m',  # 3分足
                    'limit': 500  # 最大500本（200MA計算に必要）
                }

                # User-Agentヘッダーを追加してレート制限を回避
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                # レート制限に対応した再試行ロジック
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=10)

                        if response.status_code == 200:
                            klines = response.json()

                            # キャンドルデータを保存
                            for kline in klines:
                                candle = {
                                    'timestamp': kline[0],
                                    'open': float(kline[1]),
                                    'high': float(kline[2]),
                                    'low': float(kline[3]),
                                    'close': float(kline[4]),
                                    'volume': float(kline[5])
                                }
                                self.candle_data[symbol].append(candle)

                            # データ取得状況を詳細に表示
                            data_count = len(klines)
                            ma200_ready = "✅ 可能" if data_count >= 200 else f"⏳ 不可 (あと{200-data_count}本必要)"
                            print(f"✅ {symbol}: {data_count}本取得 | 200MA計算: {ma200_ready}")
                            break  # 成功したらループ終了

                        elif response.status_code == 418:
                            # レート制限エラー - バックオフして再試行
                            wait_time = (2 ** attempt) * 2  # 2秒, 4秒, 8秒
                            print(f"⚠️ {symbol}: レート制限 (418) - {wait_time}秒後に再試行 (試行 {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            print(f"⚠️ {symbol}: 過去データ取得失敗 (status: {response.status_code})")
                            break

                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ {symbol}: リクエストエラー - {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)

                # API制限を避けるために待機（0.2秒 → 1.5秒に延長）
                time.sleep(1.5)

            except Exception as e:
                print(f"❌ {symbol}の過去データ取得エラー: {e}")

        self.is_initialized = True
        print("✅ 初期データ取得完了\n")

    def _fetch_4h_initial_data(self):
        """
        4時間足キャンドルデータを取得（マーケットレジーム判定用）
        MA 50とMA 200を計算するために250本の4時間足を取得
        """
        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                # 過去250本の4時間足キャンドルを取得
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': '4h',  # 4時間足
                    'limit': 250  # 200MA計算に必要
                }

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=10)

                        if response.status_code == 200:
                            klines = response.json()

                            # キャンドルデータを保存
                            for kline in klines:
                                candle = {
                                    'timestamp': kline[0],
                                    'open': float(kline[1]),
                                    'high': float(kline[2]),
                                    'low': float(kline[3]),
                                    'close': float(kline[4]),
                                    'volume': float(kline[5])
                                }
                                self.candle_data_4h[symbol].append(candle)

                            data_count = len(klines)
                            ma200_ready = "✅" if data_count >= 200 else f"⏳ (あと{200-data_count}本)"
                            print(f"✅ {symbol}: 4時間足{data_count}本取得 | 200MA計算: {ma200_ready}")
                            break

                        elif response.status_code == 418:
                            wait_time = (2 ** attempt) * 2
                            print(f"⚠️ {symbol}: レート制限 (418) - {wait_time}秒後に再試行")
                            time.sleep(wait_time)
                        else:
                            print(f"⚠️ {symbol}: 4時間足データ取得失敗 (status: {response.status_code})")
                            break

                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ {symbol}: リクエストエラー - {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)

                # API制限を避けるために待機
                time.sleep(1.5)

            except Exception as e:
                print(f"❌ {symbol}の4時間足データ取得エラー: {e}")

        print("✅ 4時間足データ取得完了\n")

    def _fetch_1h_initial_data(self):
        """
        1時間足キャンドルデータを取得（戦略方向判定用）
        EMA 20/50、MACD、RSIを計算するために100本の1時間足を取得
        """
        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                # 過去100本の1時間足キャンドルを取得
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': '1h',  # 1時間足
                    'limit': 100  # EMA 50計算に十分
                }

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=10)

                        if response.status_code == 200:
                            klines = response.json()

                            # キャンドルデータを保存
                            for kline in klines:
                                candle = {
                                    'timestamp': kline[0],
                                    'open': float(kline[1]),
                                    'high': float(kline[2]),
                                    'low': float(kline[3]),
                                    'close': float(kline[4]),
                                    'volume': float(kline[5])
                                }
                                self.candle_data_1h[symbol].append(candle)

                            data_count = len(klines)
                            print(f"✅ {symbol}: 1時間足{data_count}本取得")
                            break

                        elif response.status_code == 418:
                            wait_time = (2 ** attempt) * 2
                            print(f"⚠️ {symbol}: レート制限 (418) - {wait_time}秒後に再試行")
                            time.sleep(wait_time)
                        else:
                            print(f"⚠️ {symbol}: 1時間足データ取得失敗 (status: {response.status_code})")
                            break

                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ {symbol}: リクエストエラー - {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)

                # API制限を避けるために待機
                time.sleep(1.5)

            except Exception as e:
                print(f"❌ {symbol}の1時間足データ取得エラー: {e}")

        print("✅ 1時間足データ取得完了\n")

    def _start_background_update(self):
        """バックグラウンドで定期的に新しいキャンドルデータを取得"""
        self.running = True

        def update_loop():
            while self.running:
                try:
                    time.sleep(self.update_interval)  # 3分待機
                    self._update_candles()
                except Exception as e:
                    print(f"⚠️ バックグラウンド更新エラー: {e}")

        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()

    def _update_candles(self):
        """新しいキャンドルデータを取得して追加"""
        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                # 最新のキャンドル1本を取得
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': '3m',
                    'limit': 1
                }

                # User-Agentヘッダーを追加
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                response = requests.get(url, params=params, headers=headers, timeout=10)

                if response.status_code == 200:
                    klines = response.json()
                    if klines:
                        kline = klines[0]
                        candle = {
                            'timestamp': kline[0],
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        }

                        # 新しいキャンドルを追加
                        self.candle_data[symbol].append(candle)

                        # 最大600本を保持（200MA計算 + 余裕）
                        # 600本 = 30時間分のデータ
                        if len(self.candle_data[symbol]) > 600:
                            self.candle_data[symbol].pop(0)

                        print(f"🔄 {symbol}: 新しいキャンドルを追加 (価格: ${candle['close']:.2f}, 保持: {len(self.candle_data[symbol])}本)")
                elif response.status_code == 418:
                    print(f"⚠️ {symbol}: レート制限 (418) - 更新をスキップ")

                # レート制限を避けるために待機（0.1秒 → 1.5秒に延長）
                time.sleep(1.5)

            except Exception as e:
                print(f"⚠️ {symbol}のキャンドル更新エラー: {e}")

    def stop(self):
        """バックグラウンド更新を停止"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1)

    def _calculate_indicators_for_symbol(self, symbol: str) -> Dict:
        """指定銘柄のテクニカル指標を計算"""
        candles = self.candle_data.get(symbol, [])

        if len(candles) < 20:
            # データ不足
            return {
                'data_points': len(candles),
                'status': 'insufficient_data'
            }

        # 価格データを抽出
        close_prices = [c['close'] for c in candles]
        high_prices = [c['high'] for c in candles]
        low_prices = [c['low'] for c in candles]

        # 現在の価格
        current_price = close_prices[-1]

        # 24時間データ（仮定：最新のキャンドルから計算）
        high_24h = max(high_prices[-480:]) if len(high_prices) >= 480 else max(high_prices)
        low_24h = min(low_prices[-480:]) if len(low_prices) >= 480 else min(low_prices)
        change_24h = 0
        if len(close_prices) >= 480:
            change_24h = ((current_price - close_prices[-480]) / close_prices[-480] * 100)

        result = {
            'price': current_price,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'change_24h': change_24h,
            'data_points': len(candles)
        }

        # 価格の時系列（最新10データポイント）
        result['price_series'] = close_prices[-10:]

        # EMA (20期間) の時系列
        result['ema_20_series'] = self.indicators.calculate_ema_series(close_prices, 20, 10)
        result['ema_20'] = result['ema_20_series'][-1] if result['ema_20_series'] else None

        # MACD の時系列
        if len(close_prices) >= 26:
            result['macd_series'] = self.indicators.calculate_macd_series(close_prices, 10)
            macd_full = self.indicators.calculate_macd(close_prices)
            result['macd'] = macd_full.get('macd')
        else:
            result['macd_series'] = []
            result['macd'] = None

        # RSI (7期間) の時系列
        result['rsi_7_series'] = self.indicators.calculate_rsi_series(close_prices, 7, 10)
        result['rsi_7'] = result['rsi_7_series'][-1] if result['rsi_7_series'] else None

        # RSI (14期間) の時系列
        result['rsi_14_series'] = self.indicators.calculate_rsi_series(close_prices, 14, 10)
        result['rsi_14'] = result['rsi_14_series'][-1] if result['rsi_14_series'] else None

        # 4時間足コンテキスト（マーケットレジーム判定用）
        if symbol in self.candle_data_4h and len(self.candle_data_4h[symbol]) >= 50:
            candles_4h = self.candle_data_4h[symbol]
            closes_4h = [c['close'] for c in candles_4h]
            highs_4h = [c['high'] for c in candles_4h]
            lows_4h = [c['low'] for c in candles_4h]

            # SMA 50とSMA 200を計算（マーケットレジーム判定用）
            if len(closes_4h) >= 50:
                result['ma_50_4h'] = self.indicators.calculate_sma(closes_4h, 50)
            else:
                result['ma_50_4h'] = None

            if len(closes_4h) >= 200:
                result['ma_200_4h'] = self.indicators.calculate_sma(closes_4h, 200)
            else:
                result['ma_200_4h'] = None

            # EMA 20/50を計算
            result['ema_20_4h'] = self.indicators.calculate_ema(closes_4h, 20)
            result['ema_50_4h'] = self.indicators.calculate_ema(closes_4h, 50)

            # その他の4時間足指標
            result['macd_4h'] = self.indicators.calculate_macd(closes_4h)
            result['rsi_14_4h'] = self.indicators.calculate_rsi(closes_4h, 14)
            result['atr_14_4h'] = self.indicators.calculate_atr(highs_4h, lows_4h, closes_4h, 14)

            # マーケットレジーム判定
            ma_50 = result['ma_50_4h']
            ma_200 = result['ma_200_4h']

            if ma_50 is not None and ma_200 is not None:
                # 価格と50MA/200MAの位置関係、MAの傾きで判定
                price_above_50 = current_price > ma_50
                price_above_200 = current_price > ma_200
                ma_50_above_200 = ma_50 > ma_200

                # MAの傾きを計算（直近5本の4時間足で判定）
                if len(closes_4h) >= 55:
                    ma_50_prev = self.indicators.calculate_sma(closes_4h[:-5], 50)
                    ma_200_prev = self.indicators.calculate_sma(closes_4h[:-5], 200)

                    ma_50_rising = ma_50 > ma_50_prev if ma_50_prev else False
                    ma_200_rising = ma_200 > ma_200_prev if ma_200_prev else False
                else:
                    # データ不足の場合は簡易判定
                    ma_50_rising = True if ma_50_above_200 else False
                    ma_200_rising = True if ma_50_above_200 else False

                # レジーム判定ロジック
                if price_above_50 and price_above_200 and ma_50_above_200:
                    # 価格が両方のMAより上で、50MA > 200MA
                    if ma_50_rising or ma_200_rising:
                        result['market_regime'] = 'UPTREND'
                    else:
                        result['market_regime'] = 'RANGE'  # MAが横ばい
                elif not price_above_50 and not price_above_200 and not ma_50_above_200:
                    # 価格が両方のMAより下で、50MA < 200MA
                    if not ma_50_rising and not ma_200_rising:
                        result['market_regime'] = 'DOWNTREND'
                    else:
                        result['market_regime'] = 'RANGE'  # MAが横ばい
                else:
                    # それ以外はレンジ相場
                    result['market_regime'] = 'RANGE'
            else:
                result['market_regime'] = 'CALCULATING'
        else:
            # 4時間足データが不足している場合
            result['ma_50_4h'] = None
            result['ma_200_4h'] = None
            result['market_regime'] = 'CALCULATING'

        # 1時間足コンテキスト（戦略方向判定用）
        if symbol in self.candle_data_1h and len(self.candle_data_1h[symbol]) >= 20:
            candles_1h = self.candle_data_1h[symbol]
            closes_1h = [c['close'] for c in candles_1h]
            highs_1h = [c['high'] for c in candles_1h]
            lows_1h = [c['low'] for c in candles_1h]

            # EMA 20/50を計算（戦略方向用）
            result['ema_20_1h'] = self.indicators.calculate_ema(closes_1h, 20)
            if len(closes_1h) >= 50:
                result['ema_50_1h'] = self.indicators.calculate_ema(closes_1h, 50)
            else:
                result['ema_50_1h'] = None

            # MACD (1時間足)
            result['macd_1h'] = self.indicators.calculate_macd(closes_1h)

            # RSI 14 (1時間足)
            result['rsi_14_1h'] = self.indicators.calculate_rsi(closes_1h, 14)

            # 1時間足のトレンド方向を判定
            ema_20_1h = result['ema_20_1h']
            ema_50_1h = result['ema_50_1h']

            if ema_20_1h is not None and ema_50_1h is not None:
                if ema_20_1h > ema_50_1h:
                    result['trend_1h'] = 'BULLISH'
                elif ema_20_1h < ema_50_1h:
                    result['trend_1h'] = 'BEARISH'
                else:
                    result['trend_1h'] = 'NEUTRAL'
            else:
                result['trend_1h'] = 'CALCULATING'
        else:
            # 1時間足データが不足
            result['ema_20_1h'] = None
            result['ema_50_1h'] = None
            result['trend_1h'] = 'CALCULATING'

        return result

    def get_current_prices(self) -> Dict:
        """
        現在の価格とテクニカル指標を含む市場データを取得
        （拡張版：AIプロンプトに必要な全データを返す）
        """
        if not self.is_initialized:
            print("⚠️ データ初期化中...")
            return {}

        market_data = {}

        for symbol in self.symbols:
            try:
                # テクニカル指標を計算
                indicators = self._calculate_indicators_for_symbol(symbol)
                market_data[symbol] = indicators

            except Exception as e:
                print(f"❌ {symbol}の指標計算エラー: {e}")
                # エラー時は基本データのみ返す
                if self.candle_data.get(symbol):
                    market_data[symbol] = {
                        'price': self.candle_data[symbol][-1]['close'],
                        'error': str(e)
                    }

        return market_data

