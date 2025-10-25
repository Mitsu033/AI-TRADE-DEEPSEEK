"""
Exit Plan監視モジュール
nof1.ai風のExit Plan（利確目標、損切りライン、無効化条件）を監視し、
条件を満たした場合に自動的にポジションをクローズする
"""
from typing import Dict, List, Optional
from datetime import datetime
from database import DatabaseManager


class ExitPlanMonitor:
    """Exit Plan監視クラス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def check_exit_plans(self, current_positions: Dict, market_data: Dict) -> List[Dict]:
        """
        全てのアクティブなExit Planをチェックし、条件を満たす場合はクローズアクションを返す

        Args:
            current_positions: 現在のポジション情報 {symbol: {...}}
            market_data: 現在の市場データ {symbol: {'price': ...}}

        Returns:
            クローズすべきポジションのリスト [{'symbol': ..., 'reason': ..., 'trigger_type': ...}]
        """
        actions_to_take = []

        # アクティブなExit Planを取得
        active_plans = self.db.get_active_exit_plans()

        if not active_plans:
            return actions_to_take

        print(f"\n[Exit Plan Monitor] {len(active_plans)}件のアクティブなExit Planをチェック中...")

        for plan in active_plans:
            symbol = plan['position_symbol']

            # ポジションが存在しない場合、Exit Planをキャンセル
            if symbol not in current_positions:
                print(f"  [{symbol}] ポジションが存在しないため、Exit Planをキャンセル")
                self.db.update_exit_plan_status(plan['id'], 'cancelled')
                continue

            # 市場データがない場合はスキップ
            if symbol not in market_data:
                continue

            current_price = market_data[symbol].get('price', 0)
            if current_price == 0:
                continue

            # Profit Target チェック
            if plan['profit_target'] and current_price >= plan['profit_target']:
                print(f"  ✅ [{symbol}] Profit Target到達: ${current_price:.2f} >= ${plan['profit_target']:.2f}")
                actions_to_take.append({
                    'symbol': symbol,
                    'reason': f'Profit Target到達: ${plan['profit_target']:.2f}',
                    'trigger_type': 'profit_target',
                    'plan_id': plan['id'],
                    'current_price': current_price
                })
                continue  # 1つのプランに対して1つのアクションのみ

            # Stop Loss チェック
            if plan['stop_loss'] and current_price <= plan['stop_loss']:
                print(f"  🛑 [{symbol}] Stop Loss発動: ${current_price:.2f} <= ${plan['stop_loss']:.2f}")
                actions_to_take.append({
                    'symbol': symbol,
                    'reason': f'Stop Loss発動: ${plan['stop_loss']:.2f}',
                    'trigger_type': 'stop_loss',
                    'plan_id': plan['id'],
                    'current_price': current_price
                })
                continue

            # Invalidation チェック
            if plan['invalidation_price'] and current_price <= plan['invalidation_price']:
                print(f"  ⚠️ [{symbol}] Invalidation条件発動: ${current_price:.2f} <= ${plan['invalidation_price']:.2f}")
                invalidation_text = plan.get('invalidation_condition', f'price below ${plan["invalidation_price"]:.2f}')
                actions_to_take.append({
                    'symbol': symbol,
                    'reason': f'Invalidation: {invalidation_text}',
                    'trigger_type': 'invalidation',
                    'plan_id': plan['id'],
                    'current_price': current_price
                })
                continue

        if actions_to_take:
            print(f"\n[Exit Plan Monitor] {len(actions_to_take)}件のポジションをクローズします")
        else:
            print(f"[Exit Plan Monitor] クローズ条件を満たすポジションはありません")

        return actions_to_take

    def trigger_exit_plan(self, plan_id: int, trigger_type: str):
        """
        Exit Planを発動済みにマーク

        Args:
            plan_id: Exit PlanのID
            trigger_type: 発動タイプ（profit_target/stop_loss/invalidation）
        """
        self.db.update_exit_plan_status(plan_id, 'triggered', trigger_type)
        print(f"[Exit Plan Monitor] Exit Plan #{plan_id} を発動済みにマークしました (trigger: {trigger_type})")

    def cancel_exit_plan_for_symbol(self, symbol: str):
        """
        特定銘柄のアクティブなExit Planをキャンセル

        Args:
            symbol: 銘柄シンボル
        """
        plan = self.db.get_exit_plan_by_symbol(symbol)
        if plan:
            self.db.update_exit_plan_status(plan['id'], 'cancelled')
            print(f"[Exit Plan Monitor] {symbol}のExit Planをキャンセルしました")

    def get_exit_plan_for_symbol(self, symbol: str) -> Optional[Dict]:
        """
        特定銘柄のアクティブなExit Planを取得

        Args:
            symbol: 銘柄シンボル

        Returns:
            Exit Plan情報、存在しない場合はNone
        """
        return self.db.get_exit_plan_by_symbol(symbol)

    def format_exit_plan_summary(self, symbol: str, current_price: float) -> str:
        """
        Exit Planのサマリーをフォーマット

        Args:
            symbol: 銘柄シンボル
            current_price: 現在価格

        Returns:
            フォーマットされたサマリー文字列
        """
        plan = self.get_exit_plan_for_symbol(symbol)
        if not plan:
            return "Exit Plan: なし"

        summary = f"Exit Plan for {symbol}:\n"

        if plan['profit_target']:
            target_pct = ((plan['profit_target'] - current_price) / current_price) * 100
            summary += f"  Profit Target: ${plan['profit_target']:.2f} (+{target_pct:.2f}%)\n"

        if plan['stop_loss']:
            loss_pct = ((plan['stop_loss'] - current_price) / current_price) * 100
            summary += f"  Stop Loss: ${plan['stop_loss']:.2f} ({loss_pct:.2f}%)\n"

        if plan['invalidation_condition']:
            summary += f"  Invalidation: {plan['invalidation_condition']}\n"

        return summary.strip()
