"""
シミュレーションモード用トレーディングボット
取引所APIなしで完全にローカルで動作
"""
import time
import json
import threading
from datetime import datetime
from typing import Dict

from qwen3_api import QWEN3API
from simulation_mode import SimulationExchange, MarketDataFetcherEnhanced
from database import DatabaseManager
from exit_plan_monitor import ExitPlanMonitor


class SimulationTradingBot:
    """シミュレーション用トレーディングボット"""
    
    def __init__(self, qwen3_api_key: str = None, initial_balance: float = 10000.0,
                 db_path: str = "simulation_trading_data.db"):
        # QWEN3 APIクライアント
        self.qwen3 = QWEN3API(qwen3_api_key)
        self.exchange = SimulationExchange(initial_balance)
        self.db = DatabaseManager(db_path)
        self.exit_monitor = ExitPlanMonitor(self.db)
        
        # 取引対象の銘柄
        self.symbols = ["BTC", "ETH", "SOL", "BNB", "DOGE", "XRP"]

        # 市場データ取得（拡張版：テクニカル指標を含む）
        self.market_fetcher = MarketDataFetcherEnhanced(self.symbols)
        
        # 自動取引設定
        self.is_running = False
        self.trading_thread = None
        self.trading_interval = 1800  # 30分ごと（マルチタイムフレーム戦略に最適）
        self.last_trade_time = None
        self.initial_balance = initial_balance

        # エラー管理
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10  # 連続エラー上限
        
    def start_auto_trading(self):
        """自動取引を開始（データ取得も含めて全て開始）"""
        if self.is_running:
            print("⚠️ 既に自動取引が実行中です")
            return

        print("🚀 シミュレーション自動取引を開始します...")

        # 市場データ取得が停止している場合は再開
        if self.market_fetcher and not self.market_fetcher.running:
            print("  📊 市場データ取得を再開中...")
            self.market_fetcher._start_background_update()
            print("  ✅ 市場データ取得を再開しました")

        self.is_running = True
        self.consecutive_errors = 0  # エラーカウンターをリセット

        # 取引ループを開始（daemon=Falseで常時実行）
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=False)
        self.trading_thread.start()

        print(f"✅ 自動取引開始: {self.trading_interval}秒ごとに取引判断を実行")
    
    def stop_auto_trading(self):
        """自動取引を停止（データ取得も含めて全て停止）"""
        if not self.is_running:
            print("⚠️ 既に停止しています")
            return

        print("⏹️ 自動取引を停止中...")

        # 取引ループを停止
        self.is_running = False

        # 市場データのバックグラウンド更新を停止
        if self.market_fetcher:
            print("  📊 市場データ取得を停止中...")
            self.market_fetcher.stop()

        # 取引スレッドの終了を待つ（最大5秒）
        if self.trading_thread and self.trading_thread.is_alive():
            print("  🔄 取引スレッドの終了を待機中...")
            self.trading_thread.join(timeout=5)
            if self.trading_thread.is_alive():
                print("  ⚠️ 取引スレッドが終了しませんでした（タイムアウト）")
            else:
                print("  ✅ 取引スレッドを停止しました")

        print("✅ 全ての処理を停止しました")

    def is_thread_alive(self) -> bool:
        """
        取引スレッドが生存しているか確認

        Returns:
            スレッドが生存していればTrue、そうでなければFalse
        """
        return self.trading_thread is not None and self.trading_thread.is_alive()

    def get_trading_status(self) -> Dict:
        """
        取引ボットの詳細なステータスを取得

        Returns:
            ステータス情報を含む辞書
        """
        status = {
            "is_running": self.is_running,
            "thread_alive": self.is_thread_alive(),
            "consecutive_errors": self.consecutive_errors,
            "max_consecutive_errors": self.max_consecutive_errors,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "trading_interval": self.trading_interval
        }

        # 市場データ取得の状態を追加
        if self.market_fetcher:
            status["market_data_fetcher"] = {
                "running": self.market_fetcher.running,
                "initialized": self.market_fetcher.is_initialized,
                "update_interval": self.market_fetcher.update_interval
            }

        return status

    def _trading_loop(self):
        """取引ループ（バックグラウンドで実行）- 常時実行対応"""
        while self.is_running:
            try:
                print(f"\n{'='*60}")
                print(f"🔄 取引サイクル実行中... [{datetime.now().strftime('%H:%M:%S')}]")
                print(f"{'='*60}")

                # 現在の市場価格を取得
                current_prices = self.market_fetcher.get_current_prices()

                if not current_prices:
                    print("⚠️ 市場データを待機中...")
                    self.consecutive_errors += 1

                    # エラーが多すぎる場合の対処
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        print(f"❌ 連続エラーが{self.max_consecutive_errors}回に達しました。60秒待機...")
                        time.sleep(60)
                        self.consecutive_errors = 0  # リセット
                    else:
                        time.sleep(10)
                    continue

                # 取引サイクルを実行
                result = self.run_trading_cycle(current_prices)

                # 成功したらエラーカウンターをリセット
                if result.get('status') in ['success', 'waiting', 'exit_plan_executed']:
                    self.consecutive_errors = 0
                elif result.get('status') == 'error':
                    self.consecutive_errors += 1
                    print(f"⚠️ 連続エラー回数: {self.consecutive_errors}/{self.max_consecutive_errors}")

                # 結果をログ（データ準備中以外）
                if result.get('status') != 'waiting':
                    self._log_trade_result(result)

                # 次の取引まで待機（エラーが多い場合は待機時間を延長）
                wait_time = self.trading_interval
                if self.consecutive_errors >= 5:
                    wait_time = self.trading_interval * 2
                    print(f"⚠️ エラーが多いため待機時間を延長: {wait_time}秒")

                print(f"\n⏳ 次の取引まで{wait_time}秒待機...")
                time.sleep(wait_time)

            except KeyboardInterrupt:
                print("\n⏹️ ユーザーによって停止されました")
                self.is_running = False
                break

            except Exception as e:
                self.consecutive_errors += 1
                print(f"❌ 取引ループエラー ({self.consecutive_errors}/{self.max_consecutive_errors}): {e}")
                print(f"📝 エラー詳細: {type(e).__name__}")

                # エラーが多すぎる場合
                if self.consecutive_errors >= self.max_consecutive_errors:
                    print(f"❌ 連続エラーが{self.max_consecutive_errors}回に達しました。")
                    print("🔄 60秒待機後、自動的に再試行します...")
                    time.sleep(60)
                    self.consecutive_errors = 0  # リセット
                else:
                    # バックオフ戦略: エラー回数に応じて待機時間を増やす
                    backoff_time = min(30 * self.consecutive_errors, 300)  # 最大5分
                    print(f"🔄 {backoff_time}秒後に自動的に再試行します...")
                    time.sleep(backoff_time)

        print("🛑 取引ループを終了しました")
    
    def _check_data_readiness(self, market_data: Dict) -> Dict:
        """
        データ準備状況をチェック

        Returns:
            {'ready': bool, 'message': str, 'ready_symbols': list, 'not_ready_symbols': list}
        """
        ready_symbols = []
        not_ready_symbols = []

        for symbol, data in market_data.items():
            # テクニカル指標が計算されているかチェック
            data_points = data.get('data_points', 0)
            has_ema = 'ema_20' in data and data['ema_20'] is not None
            has_rsi = 'rsi_7' in data and data['rsi_7'] is not None

            if has_ema and has_rsi:
                ready_symbols.append(symbol)
            else:
                not_ready_symbols.append({
                    'symbol': symbol,
                    'data_points': data_points,
                    'needed': 20
                })

        all_ready = len(not_ready_symbols) == 0

        return {
            'ready': all_ready,
            'ready_symbols': ready_symbols,
            'not_ready_symbols': not_ready_symbols,
            'message': f"準備完了: {len(ready_symbols)}/{len(market_data)} 銘柄"
        }

    def run_trading_cycle(self, market_data: Dict) -> Dict:
        """
        1サイクルの取引を実行
        """
        try:
            # データ準備状況をチェック
            data_status = self._check_data_readiness(market_data)

            if not data_status['ready']:
                print(f"\n⏳ データ準備中: {data_status['message']}")
                for item in data_status['not_ready_symbols']:
                    print(f"   {item['symbol']}: {item['data_points']}/{item['needed']} データポイント")
                print("   ➡️ テクニカル指標の計算が完了するまで待機します...")
                return {
                    'status': 'waiting',
                    'message': 'データ準備中',
                    'data_status': data_status
                }

            print(f"\n✅ データ準備完了: 全{len(data_status['ready_symbols'])}銘柄")

            # 現在のポートフォリオ状況を取得
            portfolio = self._get_portfolio_status(market_data)

            # Exit Planのチェック（最優先実行）
            print("\n[Exit Plan Check] アクティブなExit Planをチェック中...")
            exit_actions = self.exit_monitor.check_exit_plans(
                portfolio.get('positions', {}),
                market_data
            )

            # Exit Planに基づくクローズ実行（最優先・厳守）
            if exit_actions:
                print(f"\n🔴 [Exit Plan 厳守] {len(exit_actions)}件のExit Planを発動します")

                for exit_action in exit_actions:
                    symbol = exit_action['symbol']
                    reason = exit_action['reason']
                    trigger_type = exit_action['trigger_type']
                    plan_id = exit_action['plan_id']
                    current_price = exit_action.get('current_price', 0)

                    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    print(f"[Exit Plan 発動] {symbol}")
                    print(f"  理由: {reason}")
                    print(f"  現在価格: ${current_price:.2f}")
                    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                    # ポジションを強制クローズ（Exit Plan厳守）
                    result = self._execute_trade({
                        'action': 'close_position',
                        'asset': symbol
                    }, market_data)

                    # Exit Planを発動済みにマーク
                    self.exit_monitor.trigger_exit_plan(plan_id, trigger_type)

                    # 結果を記録
                    if result.get('status') == 'success':
                        print(f"  ✅ {symbol}のポジションをクローズしました")
                        print(f"  📊 決済理由: {reason}")
                    else:
                        print(f"  ❌ {symbol}のクローズに失敗: {result.get('message')}")

                # Exit Plan実行後、ポートフォリオを再取得
                portfolio = self._get_portfolio_status(market_data)

                # Exit Plan発動時はこのサイクルを終了（AI判断をスキップ）
                print(f"\n✅ Exit Planを厳守しました。このサイクルを終了します。")
                return {
                    'status': 'exit_plan_executed',
                    'message': f'{len(exit_actions)}件のExit Planを発動',
                    'exit_actions': exit_actions,
                    'timestamp': datetime.now().isoformat()
                }

            # アクティブなExit Planを取得（AIに既存のプランを伝える）
            active_exit_plans = {}
            all_plans = self.exit_monitor.db.get_active_exit_plans()
            for plan in all_plans:
                symbol = plan['position_symbol']
                active_exit_plans[symbol] = {
                    'profit_target': plan['profit_target'],
                    'stop_loss': plan['stop_loss'],
                    'invalidation_condition': plan['invalidation_condition'],
                    'invalidation_price': plan['invalidation_price']
                }

            # QWEN3に取引判断を依頼（Exit Planが発動しなかった場合のみ）
            print("\n🤖 AI判断を取得中...")
            ai_response = self.qwen3.get_trading_decision(market_data, portfolio, active_exit_plans)
            
            if not ai_response["success"]:
                return {
                    "status": "error",
                    "message": "AI判断の取得に失敗",
                    "error": ai_response.get("error"),
                    "timestamp": datetime.now().isoformat()
                }
            
            # 取引を実行
            decision = ai_response["decision"]
            trade_result = self._execute_trade(decision, market_data)

            # Exit Planの処理
            action = decision.get("action", "").lower()
            asset = decision.get("asset")
            exit_plan = decision.get("exit_plan", {})

            # 新規ポジション作成時：Exit Planを保存
            if action in ["open_long", "open_short", "buy"] and trade_result.get("status") == "success":
                if exit_plan and asset:
                    current_price = market_data.get(asset, {}).get('price', 0)

                    # Exit Planをデータベースに保存
                    exit_plan_data = {
                        'position_symbol': asset,
                        'entry_price': current_price,
                        'profit_target': exit_plan.get('profit_target'),
                        'stop_loss': exit_plan.get('stop_loss'),
                        'invalidation_condition': exit_plan.get('invalidation'),
                        'invalidation_price': exit_plan.get('invalidation_price')
                    }

                    self.db.save_exit_plan(exit_plan_data)
                    print(f"\n[Exit Plan - 新規] {asset}のExit Planを保存しました:")
                    print(f"  Profit Target: ${exit_plan.get('profit_target', 'N/A')}")
                    print(f"  Stop Loss: ${exit_plan.get('stop_loss', 'N/A')}")
                    print(f"  Invalidation: {exit_plan.get('invalidation', 'N/A')}")

            # HOLD時：Exit Planが含まれていれば更新
            elif action == "hold" and exit_plan and asset:
                # 既存のExit Planをキャンセル
                existing_plan = self.exit_monitor.get_exit_plan_for_symbol(asset)
                if existing_plan:
                    self.exit_monitor.cancel_exit_plan_for_symbol(asset)
                    print(f"\n[Exit Plan - 更新] {asset}の既存プランをキャンセルしました")

                # 新しいExit Planを保存
                current_price = market_data.get(asset, {}).get('price', 0)
                exit_plan_data = {
                    'position_symbol': asset,
                    'entry_price': current_price,
                    'profit_target': exit_plan.get('profit_target'),
                    'stop_loss': exit_plan.get('stop_loss'),
                    'invalidation_condition': exit_plan.get('invalidation'),
                    'invalidation_price': exit_plan.get('invalidation_price')
                }

                self.db.save_exit_plan(exit_plan_data)
                print(f"\n[Exit Plan - 更新] {asset}の新しいExit Planを保存しました:")
                print(f"  Profit Target: ${exit_plan.get('profit_target', 'N/A')} (更新)")
                print(f"  Stop Loss: ${exit_plan.get('stop_loss', 'N/A')} (更新)")
                print(f"  Invalidation: {exit_plan.get('invalidation', 'N/A')} (更新)")

            # ポジションをクローズした場合、Exit Planもキャンセル
            elif action == "close_position" and trade_result.get("status") == "success" and asset:
                self.exit_monitor.cancel_exit_plan_for_symbol(asset)

            # データベースに保存
            if trade_result.get("status") == "success":
                trade_data = {
                    "timestamp": datetime.now().isoformat(),
                    "action": decision.get("action"),
                    "asset": decision.get("asset"),
                    "price": market_data.get(decision.get("asset"), {}).get('price', 0),
                    "amount_usd": decision.get("amount_usd", 0),
                    "leverage": decision.get("leverage", 1),
                    "pnl": trade_result.get("pnl", 0),
                    "pnl_percentage": trade_result.get("pnl_percentage", 0),
                    "reasoning": decision.get("reasoning", ""),
                    "success": True
                }
                self.db.save_trade(trade_data)
                
                # ポートフォリオスナップショットを保存
                updated_portfolio = self._get_portfolio_status(market_data)
                performance = {
                    'total_trades': len(self.exchange.trade_history),
                    'total_pnl': updated_portfolio['total_value'] - self.initial_balance,
                    'roi': updated_portfolio['roi']
                }
                self.db.save_portfolio_snapshot(updated_portfolio, performance)
            
            # AI判断を保存
            self.db.save_ai_decision(decision, ai_response.get("reasoning", ""), 
                                    trade_result.get("status") == "success")
            
            self.last_trade_time = datetime.now()
            
            return {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "ai_decision": decision,
                "ai_reasoning": ai_response["reasoning"],
                "trade_result": trade_result,
                "portfolio": self._get_portfolio_status(market_data)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _validate_risk_reward_ratio(self, entry_price: float, profit_target: float, stop_loss: float) -> tuple:
        """MODULE 4: Risk-Reward Ratio (RRR) を検証

        Args:
            entry_price: エントリー価格
            profit_target: 利益目標価格
            stop_loss: 損切り価格

        Returns:
            (is_valid: bool, rrr: float, message: str)
        """
        if not all([entry_price, profit_target, stop_loss]):
            return False, 0.0, "Exit Plan が不完全です（profit_target, stop_loss, entry_price が必須）"

        # リスクとリワードを計算
        risk = abs(entry_price - stop_loss)
        reward = abs(profit_target - entry_price)

        if risk == 0:
            return False, 0.0, "Stop Loss がエントリー価格と同じです"

        rrr = reward / risk
        
        # Debug出力
        print(f"  [RRR Debug] Entry=${entry_price:.2f}, Target=${profit_target:.2f}, Stop=${stop_loss:.2f}")
        print(f"  [RRR Debug] Reward=${reward:.2f}, Risk=${risk:.2f}, RRR={rrr:.2f}")

        # 市場レジームに応じたRRR判定（レンジは1.5以上、トレンドは2.0以上推奨）
        # ここでは最低1.5を要求（プロンプトで指示されている通り）
        min_rrr = 1.5  # RANGE市場は1.5でOK、トレンド市場は2.0推奨
        
        if rrr < min_rrr:
            return False, rrr, f"RRR {rrr:.2f} < {min_rrr} (必須条件未達成。レンジ市場: 1.5、トレンド市場: 2.0)"

        return True, rrr, f"RRR {rrr:.2f} ✓"

    def _validate_confluence(self, decision: Dict) -> tuple:
        """MODULE 3: コンフルエンス（複数指標の一致）を検証

        Args:
            decision: AI判断結果

        Returns:
            (is_valid: bool, score: int, message: str)
        """
        confluence_score = decision.get("confluence_score", 0)

        # confluence_score >= 1 が必須条件（2は推奨）
        if confluence_score < 1:
            return False, confluence_score, f"Confluence Score {confluence_score} < 1 (最低1つの指標一致が必要)"

        return True, confluence_score, f"Confluence Score {confluence_score} ✓"

    def _validate_market_regime(self, decision: Dict) -> tuple:
        """MODULE 1: 市場レジームが明確かどうかを検証

        Args:
            decision: AI判断結果

        Returns:
            (is_valid: bool, regime: str, message: str)
        """
        market_regime = decision.get("market_regime", "UNCLEAR")

        # UNCLEAR の場合は取引不可
        if market_regime == "UNCLEAR":
            return False, market_regime, "市場レジームが不明確です（データ不足またはレンジ相場の可能性）"

        return True, market_regime, f"Market Regime: {market_regime} ✓"

    def _execute_trade(self, decision: Dict, market_data: Dict) -> Dict:
        """取引を実行（シミュレーション）"""
        action = decision.get("action", "hold").lower()
        asset = decision.get("asset")
        amount_usd = decision.get("amount_usd", 0)
        leverage = decision.get("leverage", 1)

        if action == "hold":
            return {
                "status": "success",
                "action": "hold",
                "message": "ポジションを保持"
            }

        # close_positionの処理
        if action == "close_position":
            if asset and asset in self.exchange.positions:
                current_price = market_data[asset]['price']
                pos = self.exchange.positions[asset]
                # ポジション全体を決済
                position_value = pos['quantity'] * current_price
                result = self.exchange.place_order(asset, False, position_value, current_price, pos['leverage'])
                if result['success']:
                    return {
                        "status": "success",
                        "action": "close_position",
                        "message": f"ポジション決済: {asset}",
                        "pnl": result.get('trade', {}).get('pnl', 0),
                        "pnl_percentage": result.get('trade', {}).get('pnl_percentage', 0)
                    }
                else:
                    return {
                        "status": "failed",
                        "reason": result.get('reason', 'Unknown error')
                    }
            else:
                return {
                    "status": "failed",
                    "reason": f"決済するポジションがありません: {asset}"
                }

        # 新規エントリーの処理
        if asset not in market_data:
            return {
                "status": "failed",
                "reason": f"市場データなし: {asset}"
            }

        current_price = market_data[asset]['price']

        # 新規エントリー前の5モジュール検証
        if action in ["open_long", "buy", "open_short", "sell"]:
            print("\n" + "="*60)
            print("📋 5-MODULE FRAMEWORK VALIDATION")
            print("="*60)

            # MODULE 1: 市場レジーム検証
            regime_valid, regime, regime_msg = self._validate_market_regime(decision)
            print(f"MODULE 1 (Market Regime): {regime_msg}")
            if not regime_valid:
                return {
                    "status": "failed",
                    "reason": f"MODULE 1 失敗: {regime_msg}"
                }

            # MODULE 3: コンフルエンス検証
            confluence_valid, conf_score, conf_msg = self._validate_confluence(decision)
            print(f"MODULE 3 (Confluence): {conf_msg}")
            if not confluence_valid:
                return {
                    "status": "failed",
                    "reason": f"MODULE 3 失敗: {conf_msg}"
                }

            # MODULE 4: RRR検証（Exit Planが必要）
            exit_plan = decision.get("exit_plan", {})
            profit_target = exit_plan.get("profit_target")
            stop_loss = exit_plan.get("stop_loss")

            # Entry priceは現在価格を使用（実際のエントリー時刻に最も近い値）
            entry_price = current_price

            rrr_valid, rrr, rrr_msg = self._validate_risk_reward_ratio(
                entry_price,
                profit_target,
                stop_loss
            )
            print(f"MODULE 4 (Risk-Reward): {rrr_msg}")
            print(f"  詳細: Entry=${entry_price:.2f}, Target=${profit_target:.2f}, Stop=${stop_loss:.2f}")
            if not rrr_valid:
                return {
                    "status": "failed",
                    "reason": f"MODULE 4 失敗: {rrr_msg}"
                }

            print("="*60)
            print("✅ ALL MODULES PASSED - Executing trade")
            print("="*60 + "\n")

        # open_long または buy
        if action in ["open_long", "buy"]:
            result = self.exchange.place_order(asset, True, amount_usd, current_price, leverage)
            if result['success']:
                return {
                    "status": "success",
                    "action": "open_long",
                    "message": result['message']
                }
            else:
                return {
                    "status": "failed",
                    "reason": result.get('reason', 'Unknown error')
                }

        # open_short または sell（新規ショートポジション）
        elif action in ["open_short", "sell"]:
            # 注意: 現在のSimulationExchangeはショートポジションを完全にはサポートしていない
            # とりあえずロングと同じ処理で代用（実装を簡略化）
            result = self.exchange.place_order(asset, True, amount_usd, current_price, leverage)
            if result['success']:
                return {
                    "status": "success",
                    "action": "open_short",
                    "message": f"ショート（仮実装）: {result['message']}"
                }
            else:
                return {
                    "status": "failed",
                    "reason": result.get('reason', 'Unknown error')
                }

        return {
            "status": "failed",
            "reason": f"不明なアクション: {action}"
        }
    
    def _get_portfolio_status(self, market_data: Dict) -> Dict:
        """ポートフォリオ状況を取得"""
        account = self.exchange.get_account_value(market_data)
        
        positions = {}
        for symbol in self.exchange.positions.keys():
            if symbol in market_data:
                pos_detail = self.exchange.get_position_details(symbol, market_data[symbol]['price'])
                if pos_detail:
                    positions[symbol] = {
                        'quantity': pos_detail['quantity'],
                        'avg_price': pos_detail['entry_price'],
                        'current_price': pos_detail['current_price'],
                        'value': pos_detail['current_value'],
                        'pnl': pos_detail['unrealized_pnl'],
                        'pnl_percentage': pos_detail['unrealized_pnl_percentage'],
                        'leverage': pos_detail['leverage'],
                        'holding_time': pos_detail.get('holding_time', 'N/A'),
                        'holding_minutes': pos_detail.get('holding_minutes', 0)
                    }
        
        return {
            'total_value': account['total_value'],
            'cash': account['cash'],
            'positions_value': account['positions_value'],
            'positions': positions,
            'roi': account['roi'],
            'initial_balance': self.initial_balance
        }
    
    def _log_trade_result(self, result: Dict):
        """取引結果をログに出力"""
        print(f"\n{'='*60}")
        print(f"📊 取引実行結果 - {result.get('timestamp', '')}")
        print(f"{'='*60}")
        
        if result['status'] == 'error':
            print(f"❌ エラー: {result.get('message', '')}")
        elif result['status'] == 'completed':
            decision = result.get('ai_decision', {})
            trade_result = result.get('trade_result', {})
            
            action = decision.get('action', '').upper()
            action_emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
            
            print(f"{action_emoji} AI判断: {action}")
            print(f"📊 銘柄: {decision.get('asset', '')}")
            print(f"💰 金額: ${decision.get('amount_usd', 0):.2f}")
            print(f"📈 レバレッジ: {decision.get('leverage', 1)}x")
            print(f"💭 理由: {decision.get('reasoning', '')}")
            print(f"🎯 信頼度: {decision.get('confidence', 0):.2%}")
            
            if trade_result.get('status') == 'success':
                print(f"\n✅ 取引成功: {trade_result.get('message', '')}")
                if 'pnl' in trade_result:
                    pnl = trade_result['pnl']
                    pnl_pct = trade_result.get('pnl_percentage', 0)
                    pnl_emoji = "📈" if pnl > 0 else "📉"
                    print(f"{pnl_emoji} 損益: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            else:
                print(f"\n⚠️ 取引失敗: {trade_result.get('reason', 'Unknown')}")
            
            portfolio = result.get('portfolio', {})
            print(f"\n💼 ポートフォリオ:")
            print(f"  総資産: ${portfolio.get('total_value', 0):.2f}")
            print(f"  現金: ${portfolio.get('cash', 0):.2f}")
            print(f"  ポジション価値: ${portfolio.get('positions_value', 0):.2f}")
            
            roi = portfolio.get('roi', 0)
            roi_emoji = "📈" if roi > 0 else "📉"
            print(f"  {roi_emoji} ROI: {roi:+.2f}%")
        
        print(f"{'='*60}\n")
    
    def print_dashboard(self):
        """コンソールにダッシュボードを表示"""
        current_prices = self.market_fetcher.get_current_prices()
        portfolio = self._get_portfolio_status(current_prices)
        stats = self.db.get_performance_stats()
        
        print("\n" + "="*80)
        print("🤖 QWEN3 シミュレーショントレーディングボット ダッシュボード")
        print("="*80)
        
        # ボット状態
        status = "🟢 稼働中" if self.is_running else "🔴 停止中"
        print(f"\n【ボット状態】 {status} (シミュレーションモード)")
        if self.last_trade_time:
            print(f"最終取引: {self.last_trade_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ポートフォリオ
        print(f"\n【ポートフォリオ】")
        print(f"  総資産価値: ${portfolio['total_value']:.2f}")
        print(f"  現金: ${portfolio['cash']:.2f}")
        print(f"  ポジション価値: ${portfolio['positions_value']:.2f}")
        
        roi = portfolio['roi']
        roi_emoji = "📈" if roi > 0 else "📉"
        print(f"  {roi_emoji} ROI: {roi:+.2f}%")
        print(f"  初期資金: ${portfolio['initial_balance']:.2f}")
        print(f"  損益: ${portfolio['total_value'] - portfolio['initial_balance']:+.2f}")
        
        # ポジション
        if portfolio['positions']:
            print(f"\n【現在のポジション】")
            for asset, pos in portfolio['positions'].items():
                pnl_emoji = "📈" if pos['pnl'] > 0 else "📉"
                print(f"  {asset}:")
                print(f"    数量: {pos['quantity']:.6f}")
                print(f"    平均取得価格: ${pos['avg_price']:.2f}")
                print(f"    現在価格: ${pos['current_price']:.2f}")
                print(f"    レバレッジ: {pos['leverage']}x")
                print(f"    {pnl_emoji} 含み損益: ${pos['pnl']:+.2f} ({pos['pnl_percentage']:+.2f}%)")
        else:
            print(f"\n【現在のポジション】")
            print(f"  ポジションなし")
        
        # パフォーマンス統計
        print(f"\n【パフォーマンス統計】")
        print(f"  総取引数: {stats['total_trades']}")
        print(f"  勝ちトレード: {stats['winning_trades']} | 負けトレード: {stats['losing_trades']}")
        print(f"  勝率: {stats['win_rate']:.2f}%")
        print(f"  総損益: ${stats['total_pnl']:+.2f}")
        print(f"  平均損益: ${stats['avg_pnl']:+.2f}")
        if stats['max_profit'] > 0:
            print(f"  最大利益: ${stats['max_profit']:.2f}")
        if stats['max_loss'] < 0:
            print(f"  最大損失: ${stats['max_loss']:.2f}")
        
        # 市場サマリー
        market_summary = self.market_fetcher.get_market_summary()
        if market_summary:
            print(f"\n【市場サマリー】")
            for symbol, data in market_summary.items():
                change = data['change_24h']
                change_emoji = "🟢" if change > 0 else "🔴"
                print(f"  {symbol}: ${data['current']:.2f} {change_emoji} {change:+.2f}% (24h)")
        
        print("\n" + "="*80 + "\n")
    
    def generate_report(self, output_file: str = "simulation_report.json"):
        """詳細なレポートを生成"""
        current_prices = self.market_fetcher.get_current_prices()
        
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "mode": "SIMULATION",
            "bot_info": {
                "status": "running" if self.is_running else "stopped",
                "trading_interval": self.trading_interval,
                "symbols": self.symbols,
                "last_trade": self.last_trade_time.isoformat() if self.last_trade_time else None
            },
            "performance": self.db.get_performance_stats(),
            "portfolio": self._get_portfolio_status(current_prices),
            "trade_history": self.exchange.trade_history,
            "recent_trades_db": self.db.get_trade_history(limit=50),
            "market_summary": self.market_fetcher.get_market_summary()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ レポートを生成しました: {output_file}")
        return report

