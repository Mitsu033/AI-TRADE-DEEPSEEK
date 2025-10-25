"""
取引エンジンモジュール
"""
from datetime import datetime
from typing import Dict, List


class TradingEngine:
    """取引エンジン - 実際の取引を管理"""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "roi": 0.0
        }
        
    def execute_trade(self, decision: Dict, current_prices: Dict) -> Dict:
        """
        取引判断を実行
        
        Args:
            decision: DeepSeekからの取引判断
            current_prices: 現在の市場価格
            
        Returns:
            取引結果
        """
        action = decision.get("action", "hold")
        asset = decision.get("asset", "")
        amount_usd = decision.get("amount_usd", 0)
        
        if action == "hold":
            return {"status": "hold", "message": "ポジション維持"}
        
        # 取引前のバリデーション
        validation = self._validate_trade(decision, current_prices)
        if not validation["valid"]:
            return {"status": "rejected", "reason": validation["reason"]}
        
        # 取引実行
        if action == "buy":
            result = self._execute_buy(asset, amount_usd, decision, current_prices)
        elif action == "sell":
            result = self._execute_sell(asset, decision, current_prices)
        else:
            result = {"status": "error", "message": "無効なアクション"}
        
        # 取引履歴に記録
        if result["status"] == "success":
            self.trade_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "asset": asset,
                "price": current_prices.get(asset, 0),
                "amount_usd": amount_usd,
                "reasoning": decision.get("reasoning", ""),
                **result
            })
            self._update_metrics(result)
        
        return result
    
    def _validate_trade(self, decision: Dict, current_prices: Dict) -> Dict:
        """取引のバリデーション"""
        asset = decision.get("asset", "")
        amount_usd = decision.get("amount_usd", 0)
        action = decision.get("action", "")
        
        # 資産の存在確認
        if asset not in current_prices:
            return {"valid": False, "reason": f"資産 {asset} が見つかりません"}
        
        # 購入時の資金確認
        if action == "buy" and amount_usd > self.cash:
            return {"valid": False, "reason": "資金不足"}
        
        # 売却時のポジション確認
        if action == "sell" and asset not in self.positions:
            return {"valid": False, "reason": f"{asset} のポジションがありません"}
        
        # リスク管理: 1回の取引で資産の20%以上を使用しない
        total_value = self.get_total_value(current_prices)
        if amount_usd > total_value * 0.2:
            return {"valid": False, "reason": "取引額が大きすぎます（最大20%）"}
        
        return {"valid": True}
    
    def _execute_buy(self, asset: str, amount_usd: float, decision: Dict, current_prices: Dict) -> Dict:
        """買い注文の実行"""
        price = current_prices[asset]
        leverage = decision.get("leverage", 1)
        quantity = (amount_usd * leverage) / price
        
        # ポジション作成
        if asset not in self.positions:
            self.positions[asset] = {
                "quantity": 0,
                "avg_price": 0,
                "leverage": leverage,
                "stop_loss": decision.get("stop_loss"),
                "take_profit": decision.get("take_profit")
            }
        
        # ポジション更新
        pos = self.positions[asset]
        total_quantity = pos["quantity"] + quantity
        pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + price * quantity) / total_quantity
        pos["quantity"] = total_quantity
        pos["leverage"] = leverage
        
        # 現金を減らす
        self.cash -= amount_usd
        
        return {
            "status": "success",
            "action": "buy",
            "asset": asset,
            "quantity": quantity,
            "price": price,
            "amount_usd": amount_usd,
            "leverage": leverage
        }
    
    def _execute_sell(self, asset: str, decision: Dict, current_prices: Dict) -> Dict:
        """売り注文の実行"""
        if asset not in self.positions:
            return {"status": "error", "message": "ポジションが存在しません"}
        
        pos = self.positions[asset]
        price = current_prices[asset]
        
        # 全ポジションを売却
        quantity = pos["quantity"]
        sale_amount = quantity * price
        
        # 損益計算
        cost = pos["avg_price"] * quantity
        pnl = (sale_amount - cost) * pos["leverage"]
        
        # 現金を増やす
        self.cash += cost / pos["leverage"] + pnl
        
        # ポジション削除
        del self.positions[asset]
        
        return {
            "status": "success",
            "action": "sell",
            "asset": asset,
            "quantity": quantity,
            "price": price,
            "sale_amount": sale_amount,
            "pnl": pnl,
            "pnl_percentage": (pnl / cost) * 100
        }
    
    def get_total_value(self, current_prices: Dict) -> float:
        """総資産価値を計算"""
        positions_value = sum(
            pos["quantity"] * current_prices.get(asset, 0)
            for asset, pos in self.positions.items()
        )
        return self.cash + positions_value
    
    def get_portfolio_status(self, current_prices: Dict) -> Dict:
        """現在のポートフォリオ状況を取得"""
        total_value = self.get_total_value(current_prices)
        
        positions_detail = {}
        for asset, pos in self.positions.items():
            current_price = current_prices.get(asset, 0)
            market_value = pos["quantity"] * current_price
            pnl = (current_price - pos["avg_price"]) * pos["quantity"] * pos["leverage"]
            pnl_pct = ((current_price - pos["avg_price"]) / pos["avg_price"]) * 100 if pos["avg_price"] > 0 else 0
            
            positions_detail[asset] = {
                "quantity": pos["quantity"],
                "avg_price": pos["avg_price"],
                "current_price": current_price,
                "market_value": market_value,
                "leverage": pos["leverage"],
                "pnl": pnl,
                "pnl_percentage": pnl_pct,
                "stop_loss": pos.get("stop_loss"),
                "take_profit": pos.get("take_profit")
            }
        
        roi = ((total_value - self.initial_balance) / self.initial_balance) * 100
        
        return {
            "total_value": total_value,
            "cash": self.cash,
            "positions": positions_detail,
            "roi": roi,
            "initial_balance": self.initial_balance,
            "metrics": self.performance_metrics
        }
    
    def _update_metrics(self, result: Dict):
        """パフォーマンス指標を更新"""
        self.performance_metrics["total_trades"] += 1
        
        if "pnl" in result:
            pnl = result["pnl"]
            self.performance_metrics["total_pnl"] += pnl
            
            if pnl > 0:
                self.performance_metrics["winning_trades"] += 1
            else:
                self.performance_metrics["losing_trades"] += 1

