"""
設定ファイル管理モジュール
"""
import json
from typing import Dict


def create_config_file(filename: str = "config.json"):
    """設定ファイルのテンプレートを作成"""
    config = {
        "deepseek_api_key": "your-deepseek-api-key",
        "hyperliquid": {
            "api_key": "your-hyperliquid-api-key",
            "api_secret": "your-hyperliquid-api-secret",
            "testnet": True
        },
        "trading": {
            "initial_balance": 10000.0,
            "trading_interval": 1800,  # 30分（5モジュール戦略最適化）
            "symbols": ["BTC", "ETH", "SOL", "BNB", "DOGE", "XRP"],
            "max_position_size": 0.2,
            "max_leverage": 20
        },
        "database": {
            "path": "trading_data.db"
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"設定ファイルを作成しました: {filename}")
    print("APIキーを設定してください！")


def load_config(filename: str = "config.json") -> Dict:
    """設定ファイルを読み込む"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

