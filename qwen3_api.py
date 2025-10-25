"""
QWEN3 AI API連携モジュール
"""
import json
from openai import OpenAI
from datetime import datetime
from typing import Dict


class QWEN3API:
    """AI API連携クラス（Qwen3-max対応）"""

    # ここにAPI キーを直接入力してください（OpenRouter経由でQWEN3を使用）
    QWEN3_API_KEY = "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"
    
    def __init__(self, api_key: str = None):
        # api_keyが指定されていない場合は、クラス変数を使用
        self.api_key = api_key if api_key else self.QWEN3_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "qwen/qwen-2.5-72b-instruct"

        # OpenAIクライアントを初期化
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 取引開始時刻と呼び出し回数を追跡
        self.start_time = datetime.now()
        self.invocation_count = 0
        
    def get_trading_decision(self, market_data: Dict, portfolio: Dict) -> Dict:
        """
        市場データとポートフォリオ情報を基に、QWEN3に取引判断を依頼

        Args:
            market_data: 市場データ（価格、出来高等）
            portfolio: 現在のポートフォリオ状況

        Returns:
            取引判断（action, asset, amount等）
        """
        # 呼び出し回数をインクリメント
        self.invocation_count += 1

        prompt = self._create_trading_prompt(market_data, portfolio)
        
        try:
            print(f"🤖 AI API ({self.model}) にリクエスト中...")
            print(f"📡 エンドポイント: {self.base_url}")
            
            # OpenAI SDKを使用してリクエスト
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional cryptocurrency trader managing a portfolio.

Analyze the market data and make your best trading decision.

Available actions:
- open_long: Open a new long position
- open_short: Open a new short position
- close_position: Close an existing position
- hold: Do nothing

Response format (JSON):
{
    "action": "open_long" | "open_short" | "close_position" | "hold",
    "asset": "BTC" | "ETH" | "SOL" | "BNB" | "DOGE" | "XRP",
    "amount_usd": <number>,
    "leverage": <1-20>,
    "reasoning": "<your analysis and decision rationale>",
    "exit_plan": {
        "profit_target": <price_number>,
        "stop_loss": <price_number>,
        "invalidation": "<condition_description>",
        "invalidation_price": <price_number>
    }
}

IMPORTANT: When opening a position (open_long/open_short), you MUST include an exit_plan with:
- profit_target: Target price for taking profit
- stop_loss: Price to cut losses
- invalidation: Textual condition that invalidates your strategy (e.g., "4-hour close below 105000")
- invalidation_price: Numerical price for invalidation condition

Make the decision that maximizes profit while managing risk."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
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
                "timestamp": datetime.now().isoformat()
            }
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析エラー: {e}")
            print(f"レスポンス内容: {content if 'content' in locals() else 'N/A'}")
            return {
                "success": False,
                "error": "AIの応答をJSON形式で解析できませんでした",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ エラー: {type(e).__name__} - {str(e)}")
            # より詳細なエラー情報を表示
            import traceback
            print(f"詳細:\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_trading_prompt(self, market_data: Dict, portfolio: Dict) -> str:
        """取引判断用のプロンプトを生成（nof1.ai Qwen3-max スタイル）"""

        # 経過時間を計算
        elapsed_minutes = int((datetime.now() - self.start_time).total_seconds() / 60)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ポートフォリオ情報を抽出
        total_value = portfolio.get('total_value', 0)
        cash = portfolio.get('cash', 0)
        initial_balance = portfolio.get('initial_balance', 10000)
        roi = portfolio.get('roi', 0)
        positions = portfolio.get('positions', {})

        # プロンプトを構築
        prompt = f"""It has been {elapsed_minutes} minutes since you started trading. The current time is {current_time} and you've been invoked {self.invocation_count} times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc.

ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST

CURRENT MARKET STATE FOR ALL COINS
"""

        # 各コインの市場データを追加
        for symbol, data in market_data.items():
            current_price = data.get('price', 0)
            high_24h = data.get('high_24h', current_price)
            low_24h = data.get('low_24h', current_price)
            change_24h = data.get('change_24h', 0)

            # テクニカル指標の取得
            ema_20 = data.get('ema_20')
            macd = data.get('macd')
            rsi_7 = data.get('rsi_7')

            prompt += f"""
ALL {symbol} DATA

current_price = {current_price:.2f}"""

            if ema_20 is not None:
                prompt += f", current_ema20 = {ema_20:.3f}"
            if macd is not None:
                prompt += f", current_macd = {macd:.3f}"
            if rsi_7 is not None:
                prompt += f", current_rsi (7 period) = {rsi_7:.3f}"

            prompt += "\n"

            # Open Interest と Funding Rate
            if 'open_interest' in data and 'funding_rate' in data:
                prompt += f"""
In addition, here is the latest {symbol} open interest and funding rate for perps:

Open Interest: Latest: {data['open_interest']:.2f}

Funding Rate: {data['funding_rate']:.6e}
"""

            # 時系列データ（Intraday series）
            if 'ema_20_series' in data and data['ema_20_series']:
                prompt += f"\nIntraday series (3-minute intervals, oldest → latest):\n"

                # 価格の時系列（ダミーデータ、実際は3分間隔データが必要）
                if 'price_series' in data:
                    prices_str = ', '.join([f"{p:.2f}" for p in data['price_series'][-10:]])
                    prompt += f"\nMid prices: [{prices_str}]\n"

                # EMA (20期間) の時系列
                ema_series = data['ema_20_series'][-10:]
                ema_str = ', '.join([f"{x:.3f}" for x in ema_series])
                prompt += f"\nEMA indicators (20-period): [{ema_str}]\n"

                # MACD の時系列
                if 'macd_series' in data and data['macd_series']:
                    macd_series = data['macd_series'][-10:]
                    macd_str = ', '.join([f"{x:.3f}" for x in macd_series])
                    prompt += f"\nMACD indicators: [{macd_str}]\n"

                # RSI (7期間) の時系列
                if 'rsi_7_series' in data and data['rsi_7_series']:
                    rsi7_series = data['rsi_7_series'][-10:]
                    rsi7_str = ', '.join([f"{x:.3f}" for x in rsi7_series])
                    prompt += f"\nRSI indicators (7-Period): [{rsi7_str}]\n"

                # RSI (14期間) の時系列
                if 'rsi_14_series' in data and data['rsi_14_series']:
                    rsi14_series = data['rsi_14_series'][-10:]
                    rsi14_str = ', '.join([f"{x:.3f}" for x in rsi14_series])
                    prompt += f"\nRSI indicators (14-Period): [{rsi14_str}]\n"

                # 4時間足コンテキスト
                if 'ema_20_4h' in data and data['ema_20_4h'] is not None:
                    prompt += f"\nLonger-term context (4-hour timeframe):\n"
                    prompt += f"\n20-Period EMA: {data['ema_20_4h']:.3f}"

                    if 'ema_50_4h' in data and data['ema_50_4h'] is not None:
                        prompt += f" vs. 50-Period EMA: {data['ema_50_4h']:.3f}\n"
                    else:
                        prompt += "\n"

                    # ATR
                    if 'atr_14_4h' in data and data['atr_14_4h'] is not None:
                        prompt += f"\n14-Period ATR: {data['atr_14_4h']:.3f}\n"

                    # 4時間足のMACD
                    if 'macd_4h' in data and data['macd_4h'].get('macd') is not None:
                        macd_val = data['macd_4h']['macd']
                        prompt += f"\nMACD (4h): {macd_val:.3f}\n"

                    # 4時間足のRSI
                    if 'rsi_14_4h' in data and data['rsi_14_4h'] is not None:
                        prompt += f"\nRSI (14-Period, 4h): {data['rsi_14_4h']:.3f}\n"

            else:
                # テクニカル指標がまだ計算されていない場合
                prompt += f"\nTechnical indicators are being calculated (need more data points: {data.get('data_points', 0)}/20)\n"

            prompt += "\n24-hour range: High: {:.2f}, Low: {:.2f}, Change: {:.2f}%\n".format(high_24h, low_24h, change_24h)


        # アカウント情報を追加
        prompt += f"""
HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE

Current Total Return (percent): {roi:.2f}%

Available Cash: {cash:.2f}

Current Account Value: {total_value:.2f}

Initial Balance: {initial_balance:.2f}
"""

        # ポジション情報を追加
        if positions:
            prompt += "\nCurrent live positions & performance:\n"
            for symbol, pos in positions.items():
                quantity = pos.get('quantity', 0)
                avg_price = pos.get('avg_price', 0)
                current_price = pos.get('current_price', 0)
                leverage = pos.get('leverage', 1)
                pnl = pos.get('pnl', 0)
                pnl_pct = pos.get('pnl_percentage', 0)
                holding_time = pos.get('holding_time', 'N/A')

                prompt += f"""
{symbol}: entry_price=${avg_price:.2f}, current_price=${current_price:.2f}, unrealized_pnl=${pnl:+.2f} ({pnl_pct:+.2f}%), leverage={leverage}x, holding_time={holding_time}"""
        else:
            prompt += "\nNo open positions currently.\n"

        # 取引判断の指示
        prompt += """

MAKE YOUR TRADING DECISION:
Consider the market data, technical indicators, your current positions, and risk/reward.
If you have an open position, you can choose to close it, hold it, or open a new position in a different asset.

Respond with your trading decision in JSON format.
"""

        return prompt

