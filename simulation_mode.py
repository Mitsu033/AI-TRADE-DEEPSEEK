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

        # 4時間足キャンドルデータの保存（マーケットレジーム判定用）
        self.candle_data_4h = {symbol: [] for symbol in symbols}

        # 1時間足キャンドルデータの保存（戦略方向判定用）
        self.candle_data_1h = {symbol: [] for symbol in symbols}

        # 15分足キャンドルデータの保存（エントリータイミング判定用）
        self.candle_data_15m = {symbol: [] for symbol in symbols}

        # 3分足キャンドルデータの保存（短期トレンド判定用）
        self.candle_data_3m = {symbol: [] for symbol in symbols}

        # 更新管理（3分足が最短時間軸のため3分間隔で更新）
        self.update_interval = 180  # 3分 = 180秒
        self.last_3m_update = {}  # 3分足の最終更新時刻
        self.last_15m_update = {}  # 15分足の最終更新時刻
        self.last_1h_update = {}  # 1時間足の最終更新時刻
        self.last_4h_update = {}  # 4時間足の最終更新時刻
        self.is_initialized = False
        self.update_thread = None
        self.running = False

        # 4時間足データを取得
        print("📊 4時間足データを取得中（マーケットレジーム判定用）...")
        self._fetch_4h_initial_data()

        # 1時間足データを取得
        print("📊 1時間足データを取得中（戦略方向判定用）...")
        self._fetch_1h_initial_data()

        # 15分足データを取得
        print("📊 15分足データを取得中（エントリータイミング判定用）...")
        self._fetch_15m_initial_data()

        # 3分足データを取得
        print("📊 3分足データを取得中（短期トレンド判定用）...")
        self._fetch_3m_initial_data()

        # 全データ初期化完了
        self.is_initialized = True
        print("✅ 全データ初期化完了\n")

        # バックグラウンド更新を開始
        self._start_background_update()

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

                            # 最後のキャンドルのタイムスタンプを記録
                            if klines:
                                self.last_4h_update[symbol] = klines[-1][0]  # タイムスタンプ

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

                            # 最後のキャンドルのタイムスタンプを記録
                            if klines:
                                self.last_1h_update[symbol] = klines[-1][0]  # タイムスタンプ

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

    def _fetch_15m_initial_data(self):
        """
        15分足キャンドルデータを取得（エントリータイミング判定用）
        EMA 20、MACD、RSIを計算するために60本の15分足を取得
        """
        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                # 過去60本の15分足キャンドルを取得（15時間分）
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': '15m',  # 15分足
                    'limit': 60  # EMA 20計算に十分
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
                                self.candle_data_15m[symbol].append(candle)

                            data_count = len(klines)
                            print(f"✅ {symbol}: 15分足{data_count}本取得")

                            # 最後のキャンドルのタイムスタンプを記録
                            if klines:
                                self.last_15m_update[symbol] = klines[-1][0]  # タイムスタンプ

                            break

                        elif response.status_code == 418:
                            wait_time = (2 ** attempt) * 2
                            print(f"⚠️ {symbol}: レート制限 (418) - {wait_time}秒後に再試行")
                            time.sleep(wait_time)
                        else:
                            print(f"⚠️ {symbol}: 15分足データ取得失敗 (status: {response.status_code})")
                            break

                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ {symbol}: リクエストエラー - {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)

                # API制限を避けるために待機
                time.sleep(1.5)

            except Exception as e:
                print(f"❌ {symbol}の15分足データ取得エラー: {e}")

        print("✅ 15分足データ取得完了\n")

    def _fetch_3m_initial_data(self):
        """
        3分足キャンドルデータを取得（短期トレンド判定用）
        EMA 20、MACD、RSIを計算するために50本の3分足を取得
        """
        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                # 過去50本の3分足キャンドルを取得（2.5時間分）
                url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': binance_symbol,
                    'interval': '3m',  # 3分足
                    'limit': 50  # EMA 20計算に十分
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
                                self.candle_data_3m[symbol].append(candle)

                            data_count = len(klines)
                            print(f"✅ {symbol}: 3分足{data_count}本取得")

                            # 最後のキャンドルのタイムスタンプを記録
                            if klines:
                                self.last_3m_update[symbol] = klines[-1][0]  # タイムスタンプ

                            break

                        elif response.status_code == 418:
                            wait_time = (2 ** attempt) * 2
                            print(f"⚠️ {symbol}: レート制限 (418) - {wait_time}秒後に再試行")
                            time.sleep(wait_time)
                        else:
                            print(f"⚠️ {symbol}: 3分足データ取得失敗 (status: {response.status_code})")
                            break

                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ {symbol}: リクエストエラー - {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)

                # API制限を避けるために待機
                time.sleep(1.5)

            except Exception as e:
                print(f"❌ {symbol}の3分足データ取得エラー: {e}")

        print("✅ 3分足データ取得完了\n")

    def _start_background_update(self):
        """バックグラウンドで定期的に新しいキャンドルデータを取得"""
        self.running = True

        def update_loop():
            while self.running:
                try:
                    time.sleep(self.update_interval)  # 15分待機
                    self._update_candles()
                except Exception as e:
                    print(f"⚠️ バックグラウンド更新エラー: {e}")

        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()

    def _update_candles(self):
        """新しいキャンドルデータを取得して追加（3分足、15分足、1時間足、4時間足）"""
        current_time_ms = int(time.time() * 1000)

        for symbol in self.symbols:
            try:
                binance_symbol = f"{symbol}USDT"
                url = f"https://api.binance.com/api/v3/klines"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                # ===== 3分足の更新（3分ごと） =====
                last_3m = self.last_3m_update.get(symbol, 0)
                time_since_3m = (current_time_ms - last_3m) / 1000  # 秒に変換

                if time_since_3m >= 180:  # 3分以上経過
                    params_3m = {
                        'symbol': binance_symbol,
                        'interval': '3m',
                        'limit': 1
                    }

                    response = requests.get(url, params=params_3m, headers=headers, timeout=10)

                    if response.status_code == 200:
                        klines = response.json()
                        if klines:
                            kline = klines[0]
                            candle_3m = {
                                'timestamp': kline[0],
                                'open': float(kline[1]),
                                'high': float(kline[2]),
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5])
                            }

                            # 重複チェック
                            if not self.candle_data_3m[symbol] or \
                               candle_3m['timestamp'] != self.candle_data_3m[symbol][-1]['timestamp']:
                                self.candle_data_3m[symbol].append(candle_3m)
                                self.last_3m_update[symbol] = kline[0]

                                # 最大80本を保持
                                if len(self.candle_data_3m[symbol]) > 80:
                                    self.candle_data_3m[symbol].pop(0)

                                print(f"⏱️ {symbol}: 3分足更新 (${candle_3m['close']:.2f}, 保持: {len(self.candle_data_3m[symbol])}本)")

                # ===== 1時間足の更新（1時間ごと） =====
                last_1h = self.last_1h_update.get(symbol, 0)
                time_since_1h = (current_time_ms - last_1h) / 1000  # 秒に変換

                if time_since_1h >= 3600:  # 1時間以上経過
                    params_1h = {
                        'symbol': binance_symbol,
                        'interval': '1h',
                        'limit': 1
                    }

                    response = requests.get(url, params=params_1h, headers=headers, timeout=10)

                    if response.status_code == 200:
                        klines = response.json()
                        if klines:
                            kline = klines[0]
                            candle_1h = {
                                'timestamp': kline[0],
                                'open': float(kline[1]),
                                'high': float(kline[2]),
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5])
                            }

                            # 重複チェック（タイムスタンプが異なる場合のみ追加）
                            if not self.candle_data_1h[symbol] or \
                               candle_1h['timestamp'] != self.candle_data_1h[symbol][-1]['timestamp']:
                                self.candle_data_1h[symbol].append(candle_1h)
                                self.last_1h_update[symbol] = kline[0]

                                # 最大150本を保持
                                if len(self.candle_data_1h[symbol]) > 150:
                                    self.candle_data_1h[symbol].pop(0)

                                print(f"🕐 {symbol}: 1時間足更新 (${candle_1h['close']:.2f}, 保持: {len(self.candle_data_1h[symbol])}本)")

                # ===== 15分足の更新（15分ごと） =====
                last_15m = self.last_15m_update.get(symbol, 0)
                time_since_15m = (current_time_ms - last_15m) / 1000  # 秒に変換

                if time_since_15m >= 900:  # 15分以上経過
                    params_15m = {
                        'symbol': binance_symbol,
                        'interval': '15m',
                        'limit': 1
                    }

                    response = requests.get(url, params=params_15m, headers=headers, timeout=10)

                    if response.status_code == 200:
                        klines = response.json()
                        if klines:
                            kline = klines[0]
                            candle_15m = {
                                'timestamp': kline[0],
                                'open': float(kline[1]),
                                'high': float(kline[2]),
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5])
                            }

                            # 重複チェック
                            if not self.candle_data_15m[symbol] or \
                               candle_15m['timestamp'] != self.candle_data_15m[symbol][-1]['timestamp']:
                                self.candle_data_15m[symbol].append(candle_15m)
                                self.last_15m_update[symbol] = kline[0]

                                # 最大100本を保持
                                if len(self.candle_data_15m[symbol]) > 100:
                                    self.candle_data_15m[symbol].pop(0)

                                print(f"🕒 {symbol}: 15分足更新 (${candle_15m['close']:.2f}, 保持: {len(self.candle_data_15m[symbol])}本)")

                # ===== 4時間足の更新（4時間ごと） =====
                last_4h = self.last_4h_update.get(symbol, 0)
                time_since_4h = (current_time_ms - last_4h) / 1000  # 秒に変換

                if time_since_4h >= 14400:  # 4時間以上経過
                    params_4h = {
                        'symbol': binance_symbol,
                        'interval': '4h',
                        'limit': 1
                    }

                    response = requests.get(url, params=params_4h, headers=headers, timeout=10)

                    if response.status_code == 200:
                        klines = response.json()
                        if klines:
                            kline = klines[0]
                            candle_4h = {
                                'timestamp': kline[0],
                                'open': float(kline[1]),
                                'high': float(kline[2]),
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5])
                            }

                            # 重複チェック
                            if not self.candle_data_4h[symbol] or \
                               candle_4h['timestamp'] != self.candle_data_4h[symbol][-1]['timestamp']:
                                self.candle_data_4h[symbol].append(candle_4h)
                                self.last_4h_update[symbol] = kline[0]

                                # 最大300本を保持
                                if len(self.candle_data_4h[symbol]) > 300:
                                    self.candle_data_4h[symbol].pop(0)

                                print(f"🕓 {symbol}: 4時間足更新 (${candle_4h['close']:.2f}, 保持: {len(self.candle_data_4h[symbol])}本)")

                # レート制限を避けるために待機
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
        # 現在価格を15分足から取得（最短時間軸）
        current_price = None
        if symbol in self.candle_data_15m and self.candle_data_15m[symbol]:
            current_price = self.candle_data_15m[symbol][-1]['close']
        elif symbol in self.candle_data_1h and self.candle_data_1h[symbol]:
            current_price = self.candle_data_1h[symbol][-1]['close']
        elif symbol in self.candle_data_4h and self.candle_data_4h[symbol]:
            current_price = self.candle_data_4h[symbol][-1]['close']

        if current_price is None:
            # データ不足
            return {
                'status': 'insufficient_data',
                'price': 0
            }

        result = {
            'price': current_price,
            'status': 'ok'
        }

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

            # ATR 14（MODULE 4 - リスク管理用）のみ計算
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

        # 3分足コンテキスト（短期トレンド判定用）
        if symbol in self.candle_data_3m and len(self.candle_data_3m[symbol]) >= 20:
            candles_3m = self.candle_data_3m[symbol]
            closes_3m = [c['close'] for c in candles_3m]

            # EMA 20を計算（短期トレンド用）
            result['ema_20_3m'] = self.indicators.calculate_ema(closes_3m, 20)

            # MACD (3分足) - 超短期シグナル検出用
            result['macd_3m'] = self.indicators.calculate_macd(closes_3m)

            # RSI 7 (3分足) - 超短期過熱感チェック
            result['rsi_7_3m'] = self.indicators.calculate_rsi(closes_3m, 7)

            # 3分足のモメンタム判定
            macd_3m = result['macd_3m']

            if macd_3m and macd_3m.get('macd') is not None:
                macd_val = macd_3m['macd']
                signal_val = macd_3m.get('signal', 0)

                if macd_val > signal_val:
                    result['momentum_3m'] = 'BULLISH'
                elif macd_val < signal_val:
                    result['momentum_3m'] = 'BEARISH'
                else:
                    result['momentum_3m'] = 'NEUTRAL'
            else:
                result['momentum_3m'] = 'CALCULATING'
        else:
            # 3分足データが不足
            result['ema_20_3m'] = None
            result['rsi_7_3m'] = None
            result['macd_3m'] = None
            result['momentum_3m'] = 'CALCULATING'

        # 15分足コンテキスト（エントリータイミング判定用）
        if symbol in self.candle_data_15m and len(self.candle_data_15m[symbol]) >= 20:
            candles_15m = self.candle_data_15m[symbol]
            closes_15m = [c['close'] for c in candles_15m]
            highs_15m = [c['high'] for c in candles_15m]
            lows_15m = [c['low'] for c in candles_15m]

            # EMA 20を計算（エントリータイミング用）
            result['ema_20_15m'] = self.indicators.calculate_ema(closes_15m, 20)

            # MACD (15分足) - エントリーシグナル検出用
            result['macd_15m'] = self.indicators.calculate_macd(closes_15m)

            # RSI 14 (15分足) - 過熱感チェック
            result['rsi_14_15m'] = self.indicators.calculate_rsi(closes_15m, 14)

            # RSI 7 (15分足) - 短期過熱感チェック
            result['rsi_7_15m'] = self.indicators.calculate_rsi(closes_15m, 7)

            # MODULE 3用に15分足データを基本指標としても提供
            result['ema_20'] = result['ema_20_15m']
            result['macd'] = result['macd_15m'].get('macd') if result['macd_15m'] else None
            result['rsi_14'] = result['rsi_14_15m']
            result['rsi_7'] = result['rsi_7_15m']

            # 15分足のモメンタム判定
            macd_15m = result['macd_15m']
            rsi_15m = result['rsi_14_15m']

            if macd_15m and macd_15m.get('macd') is not None:
                macd_val = macd_15m['macd']
                signal_val = macd_15m.get('signal', 0)

                if macd_val > signal_val:
                    result['momentum_15m'] = 'BULLISH'
                elif macd_val < signal_val:
                    result['momentum_15m'] = 'BEARISH'
                else:
                    result['momentum_15m'] = 'NEUTRAL'
            else:
                result['momentum_15m'] = 'CALCULATING'
        else:
            # 15分足データが不足
            result['ema_20_15m'] = None
            result['rsi_14_15m'] = None
            result['rsi_7_15m'] = None
            result['macd_15m'] = None
            result['momentum_15m'] = 'CALCULATING'

            # MODULE 3用のフォールバック（15分足データ不足時）
            result['ema_20'] = None
            result['macd'] = None
            result['rsi_14'] = None
            result['rsi_7'] = None

        # 支持線/抵抗線検出（4時間足データから）
        if symbol in self.candle_data_4h and len(self.candle_data_4h[symbol]) >= 100:
            candles_4h = self.candle_data_4h[symbol]
            highs_4h = [c['high'] for c in candles_4h]
            lows_4h = [c['low'] for c in candles_4h]
            closes_4h = [c['close'] for c in candles_4h]

            # 支持線/抵抗線を検出
            sr_data = self.indicators.detect_support_resistance(
                highs_4h, lows_4h, closes_4h, current_price, lookback=100
            )

            result['support_levels'] = sr_data['support_levels']
            result['resistance_levels'] = sr_data['resistance_levels']
            result['nearest_support'] = sr_data['nearest_support']
            result['nearest_resistance'] = sr_data['nearest_resistance']
        else:
            # 4時間足データが不足
            result['support_levels'] = []
            result['resistance_levels'] = []
            result['nearest_support'] = None
            result['nearest_resistance'] = None

        # 価格構造分析（1時間足データから）
        if symbol in self.candle_data_1h and len(self.candle_data_1h[symbol]) >= 50:
            candles_1h = self.candle_data_1h[symbol]
            highs_1h = [c['high'] for c in candles_1h]
            lows_1h = [c['low'] for c in candles_1h]
            closes_1h = [c['close'] for c in candles_1h]

            # 価格構造を分析
            structure_data = self.indicators.analyze_price_structure(
                highs_1h, lows_1h, closes_1h, lookback=50
            )

            result['price_structure'] = structure_data['structure']
            result['structure_pattern'] = structure_data['pattern']
            result['trend_strength'] = structure_data['trend_strength']
            result['hh_count'] = structure_data['hh_count']
            result['ll_count'] = structure_data['ll_count']
            result['hl_count'] = structure_data['hl_count']
            result['lh_count'] = structure_data['lh_count']
        else:
            # 1時間足データが不足
            result['price_structure'] = 'UNCLEAR'
            result['structure_pattern'] = 'INSUFFICIENT_DATA'
            result['trend_strength'] = 0
            result['hh_count'] = 0
            result['ll_count'] = 0
            result['hl_count'] = 0
            result['lh_count'] = 0

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
                # エラー時は基本データのみ返す（15分足から取得を試みる）
                price = 0
                if symbol in self.candle_data_15m and self.candle_data_15m[symbol]:
                    price = self.candle_data_15m[symbol][-1]['close']
                elif symbol in self.candle_data_1h and self.candle_data_1h[symbol]:
                    price = self.candle_data_1h[symbol][-1]['close']
                elif symbol in self.candle_data_4h and self.candle_data_4h[symbol]:
                    price = self.candle_data_4h[symbol][-1]['close']

                market_data[symbol] = {
                    'price': price,
                    'error': str(e)
                }

        return market_data

