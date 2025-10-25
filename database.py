"""
データベース管理モジュール
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class DatabaseManager:
    """取引データの永続化管理クラス"""
    
    def __init__(self, db_path: str = "trading_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 取引履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                asset TEXT NOT NULL,
                price REAL NOT NULL,
                amount_usd REAL NOT NULL,
                leverage INTEGER DEFAULT 1,
                pnl REAL DEFAULT 0,
                pnl_percentage REAL DEFAULT 0,
                reasoning TEXT,
                success INTEGER DEFAULT 1,
                error_message TEXT
            )
        ''')
        
        # ポートフォリオスナップショットテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_value REAL NOT NULL,
                cash REAL NOT NULL,
                positions_json TEXT,
                roi REAL NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0
            )
        ''')
        
        # 市場データテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume_24h REAL DEFAULT 0,
                funding_rate REAL DEFAULT 0
            )
        ''')
        
        # AI判断テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                reasoning TEXT,
                confidence REAL DEFAULT 0,
                executed INTEGER DEFAULT 0
            )
        ''')

        # Exit Planテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exit_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                position_symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                profit_target REAL,
                stop_loss REAL,
                invalidation_condition TEXT,
                invalidation_price REAL,
                status TEXT DEFAULT 'active',
                triggered_at TEXT,
                trigger_type TEXT
            )
        ''')

        conn.commit()
        conn.close()
    
    def save_trade(self, trade_data: Dict):
        """取引データを保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades 
            (timestamp, action, asset, price, amount_usd, leverage, pnl, pnl_percentage, 
             reasoning, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('timestamp', datetime.now().isoformat()),
            trade_data.get('action', ''),
            trade_data.get('asset', ''),
            trade_data.get('price', 0),
            trade_data.get('amount_usd', 0),
            trade_data.get('leverage', 1),
            trade_data.get('pnl', 0),
            trade_data.get('pnl_percentage', 0),
            trade_data.get('reasoning', ''),
            1 if trade_data.get('success', True) else 0,
            trade_data.get('error_message', '')
        ))
        
        conn.commit()
        conn.close()
    
    def save_portfolio_snapshot(self, portfolio: Dict, metrics: Dict):
        """ポートフォリオのスナップショットを保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO portfolio_snapshots
            (timestamp, total_value, cash, positions_json, roi, total_trades, 
             winning_trades, losing_trades)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            portfolio.get('total_value', 0),
            portfolio.get('cash', 0),
            json.dumps(portfolio.get('positions', {})),
            portfolio.get('roi', 0),
            metrics.get('total_trades', 0),
            metrics.get('winning_trades', 0),
            metrics.get('losing_trades', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_market_data(self, symbol: str, data: Dict):
        """市場データを保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_data
            (timestamp, symbol, price, volume_24h, funding_rate)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('timestamp', datetime.now().isoformat()),
            symbol,
            data.get('price', 0),
            data.get('volume_24h', 0),
            data.get('funding_rate', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_ai_decision(self, decision: Dict, reasoning: str, executed: bool = False):
        """AIの判断を保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_decisions
            (timestamp, decision_json, reasoning, confidence, executed)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            json.dumps(decision),
            reasoning,
            decision.get('confidence', 0),
            1 if executed else 0
        ))
        
        conn.commit()
        conn.close()
    
    def get_ai_decisions(self, limit: int = 50) -> List[Dict]:
        """AI判断履歴を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, decision_json, reasoning, confidence, executed
            FROM ai_decisions
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        decisions = []
        for row in rows:
            decisions.append({
                'id': row[0],
                'timestamp': row[1],
                'decision_json': row[2],
                'reasoning': row[3],
                'confidence': row[4],
                'executed': bool(row[5])
            })
        
        return decisions
    
    def get_trade_history(self, limit: int = 100, asset: Optional[str] = None) -> List[Dict]:
        """取引履歴を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if asset:
            cursor.execute('''
                SELECT * FROM trades 
                WHERE asset = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (asset, limit))
        else:
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        trades = []
        for row in cursor.fetchall():
            trades.append(dict(zip(columns, row)))
        
        conn.close()
        return trades
    
    def get_portfolio_history(self, limit: int = 100) -> List[Dict]:
        """ポートフォリオ履歴を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM portfolio_snapshots 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        snapshots = []
        for row in cursor.fetchall():
            snapshot = dict(zip(columns, row))
            snapshot['positions'] = json.loads(snapshot.get('positions_json', '{}'))
            snapshots.append(snapshot)
        
        conn.close()
        return snapshots
    
    def get_performance_stats(self) -> Dict:
        """パフォーマンス統計を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 総取引数と勝率
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as max_profit,
                MIN(pnl) as max_loss
            FROM trades
            WHERE success = 1
        ''')
        
        stats = cursor.fetchone()
        
        # 最新のポートフォリオ状況
        cursor.execute('''
            SELECT total_value, cash, roi 
            FROM portfolio_snapshots 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        
        portfolio = cursor.fetchone()
        
        conn.close()
        
        win_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
        
        return {
            'total_trades': stats[0] or 0,
            'winning_trades': stats[1] or 0,
            'losing_trades': stats[2] or 0,
            'win_rate': win_rate,
            'total_pnl': stats[3] or 0,
            'avg_pnl': stats[4] or 0,
            'max_profit': stats[5] or 0,
            'max_loss': stats[6] or 0,
            'current_value': portfolio[0] if portfolio else 0,
            'current_cash': portfolio[1] if portfolio else 0,
            'current_roi': portfolio[2] if portfolio else 0
        }
    
    def get_asset_performance(self, asset: str) -> Dict:
        """特定資産のパフォーマンスを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM trades
            WHERE asset = ? AND success = 1
        ''', (asset,))
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            'asset': asset,
            'total_trades': stats[0] or 0,
            'winning_trades': stats[1] or 0,
            'win_rate': (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
            'total_pnl': stats[2] or 0,
            'avg_pnl': stats[3] or 0
        }
    
    def export_to_json(self, output_file: str):
        """データをJSON形式でエクスポート"""
        data = {
            'trades': self.get_trade_history(limit=1000),
            'portfolio_history': self.get_portfolio_history(limit=1000),
            'performance_stats': self.get_performance_stats(),
            'exported_at': datetime.now().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"データをエクスポートしました: {output_file}")
    
    def clear_old_data(self, days: int = 30):
        """古いデータを削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('DELETE FROM market_data WHERE timestamp < ?', (cutoff_date,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()

        print(f"{days}日以前のデータを削除しました（{deleted}件）")

    def save_exit_plan(self, exit_plan_data: Dict):
        """Exit Planを保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO exit_plans
            (timestamp, position_symbol, entry_price, profit_target, stop_loss,
             invalidation_condition, invalidation_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            exit_plan_data.get('position_symbol', ''),
            exit_plan_data.get('entry_price', 0),
            exit_plan_data.get('profit_target'),
            exit_plan_data.get('stop_loss'),
            exit_plan_data.get('invalidation_condition'),
            exit_plan_data.get('invalidation_price'),
            'active'
        ))

        conn.commit()
        conn.close()

    def get_active_exit_plans(self) -> List[Dict]:
        """アクティブなExit Planを全て取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM exit_plans
            WHERE status = 'active'
            ORDER BY timestamp DESC
        ''')

        columns = [desc[0] for desc in cursor.description]
        plans = []
        for row in cursor.fetchall():
            plans.append(dict(zip(columns, row)))

        conn.close()
        return plans

    def get_exit_plan_by_symbol(self, symbol: str) -> Optional[Dict]:
        """特定銘柄のアクティブなExit Planを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM exit_plans
            WHERE position_symbol = ? AND status = 'active'
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (symbol,))

        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()

        conn.close()

        if row:
            return dict(zip(columns, row))
        return None

    def update_exit_plan_status(self, plan_id: int, status: str, trigger_type: str = None):
        """Exit Planのステータスを更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if trigger_type:
            cursor.execute('''
                UPDATE exit_plans
                SET status = ?, triggered_at = ?, trigger_type = ?
                WHERE id = ?
            ''', (status, datetime.now().isoformat(), trigger_type, plan_id))
        else:
            cursor.execute('''
                UPDATE exit_plans
                SET status = ?
                WHERE id = ?
            ''', (status, plan_id))

        conn.commit()
        conn.close()

    def get_exit_plan_history(self, limit: int = 50) -> List[Dict]:
        """Exit Plan履歴を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM exit_plans
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        columns = [desc[0] for desc in cursor.description]
        plans = []
        for row in cursor.fetchall():
            plans.append(dict(zip(columns, row)))

        conn.close()
        return plans

