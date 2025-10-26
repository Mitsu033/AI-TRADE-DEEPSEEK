"""
QWEN3 AI API連携モジュール
"""
import json
import os
from openai import OpenAI
from datetime import datetime
from typing import Dict
from prompts import SYSTEM_PROMPT, create_trading_prompt, TEMPERATURE, MAX_TOKENS
from time_utils import now_jst

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    from pathlib import Path

    # プロジェクトルートの.envファイルを明示的に指定
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"📝 .envファイルを読み込みました: {env_path}")
except ImportError:
    # python-dotenvがインストールされていない場合はスキップ
    print("⚠️ python-dotenvがインストールされていません")
    pass
except Exception as e:
    print(f"⚠️ .envファイルの読み込みエラー: {e}")
    pass


class QWEN3API:
    """AI API連携クラス（Qwen3-max対応）"""

    # デフォルトのAPIキー（開発環境用）
    # 本番環境では環境変数 QWEN3_API_KEY を使用してください
    DEFAULT_API_KEY = "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"

    def __init__(self, api_key: str = None):
        # 優先順位: 引数 > 環境変数 > デフォルト
        env_key = os.environ.get('QWEN3_API_KEY')

        if api_key:
            self.api_key = api_key
            key_source = "argument"
        elif env_key:
            self.api_key = env_key
            key_source = "environment variable (.env)"
        else:
            self.api_key = self.DEFAULT_API_KEY
            key_source = "default (hardcoded)"

        print(f"\n{'='*60}")
        print(f"🔑 API Key Configuration")
        print(f"{'='*60}")
        print(f"Source: {key_source}")
        print(f"API Key: {self.api_key[:20]}...{self.api_key[-10:]} (length: {len(self.api_key)})")
        print(f"Environment QWEN3_API_KEY exists: {env_key is not None}")
        if env_key:
            print(f"Env Key Preview: {env_key[:20]}...{env_key[-10:]}")
        print(f"{'='*60}\n")
        self.base_url = "https://openrouter.ai/api/v1"
        # 最高性能モデル（Qwen3-max）
        self.model = "qwen/qwen3-max"

        # OpenAIクライアントを初期化
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 取引開始時刻と呼び出し回数を追跡
        self.start_time = now_jst()
        self.invocation_count = 0
        
    def get_trading_decision(self, market_data: Dict, portfolio: Dict, exit_plans: Dict = None) -> Dict:
        """
        市場データとポートフォリオ情報を基に、QWEN3に取引判断を依頼

        Args:
            market_data: 市場データ（価格、出来高等）
            portfolio: 現在のポートフォリオ状況
            exit_plans: アクティブなExit Plan情報（オプション）

        Returns:
            取引判断（action, asset, amount等）
        """
        # 呼び出し回数をインクリメント
        self.invocation_count += 1

        # prompts.pyからプロンプトを生成（Exit Plan情報を含む）
        prompt = create_trading_prompt(market_data, portfolio, self.start_time, self.invocation_count, exit_plans)
        
        # リトライ設定
        max_retries = 3
        retry_delay = 10  # 秒

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"🔄 リトライ {attempt}/{max_retries - 1}... ({retry_delay}秒待機後)")
                    import time
                    time.sleep(retry_delay)

                print(f"🤖 AI API ({self.model}) にリクエスト中...")
                print(f"📡 エンドポイント: {self.base_url}")

                # OpenAI SDKを使用してリクエスト
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT  # prompts.pyから読み込み
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=TEMPERATURE,  # prompts.pyで設定
                    max_tokens=MAX_TOKENS,  # prompts.pyで設定
                    response_format={"type": "json_object"}
                )

                print(f"✅ API応答を受信しました")

                # レスポンスから内容を取得
                content = response.choices[0].message.content
                decision = json.loads(content)

                return {
                    "success": True,
                    "decision": decision,
                    "reasoning": decision.get("reasoning", ""),
                    "timestamp": now_jst().isoformat()
                }

            except json.JSONDecodeError as e:
                print(f"❌ JSON解析エラー: {e}")
                print(f"レスポンス内容: {content if 'content' in locals() else 'N/A'}")
                return {
                    "success": False,
                    "error": "AIの応答をJSON形式で解析できませんでした",
                    "timestamp": now_jst().isoformat()
                }

            except Exception as e:
                error_type = type(e).__name__
                print(f"❌ エラー: {error_type} - {str(e)}")

                # レート制限エラー（429）の場合は即座に失敗を返す（次のサイクルまで待つ）
                if "RateLimitError" in error_type or "429" in str(e):
                    print(f"⏸️ レート制限エラー（429）。次の取引サイクルまで待機します...")
                    return {
                        "success": False,
                        "error": "RateLimitError: API制限に達しました。次のサイクルで再試行します。",
                        "error_type": "rate_limit",
                        "timestamp": now_jst().isoformat()
                    }

                # その他のエラーはリトライ
                if attempt < max_retries - 1:
                    print(f"⏳ その他のエラー。{retry_delay}秒後にリトライします...")
                    continue

                # 最大リトライ回数に達した場合
                import traceback
                print(f"詳細:\n{traceback.format_exc()}")
                return {
                    "success": False,
                    "error": f"{error_type}: {str(e)}",
                    "timestamp": now_jst().isoformat()
                }

        # リトライループを抜けた場合（全てのリトライが失敗）
        return {
            "success": False,
            "error": "最大リトライ回数に達しました",
            "timestamp": datetime.now().isoformat()
        }
    

