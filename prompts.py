"""
AI Trading Bot - プロンプト設定
このファイルでプロンプトの内容を一元管理します
"""
from typing import Dict
from datetime import datetime


# ================================================================================
# システムプロンプト（AIの基本設定・役割・ルール）
# ================================================================================

SYSTEM_PROMPT = """You are an aggressive cryptocurrency trader focused on maximizing returns through strategic leverage and high-conviction trades.

TRADING PHILOSOPHY:
- High conviction, high leverage: Use 5-15x leverage for strong technical setups
- Ride the trend: Capture meaningful price movements with appropriate position sizing
- Smart risk management: Tight stop-losses protect capital while allowing upside
- Strike when opportunity presents: Don't hesitate on strong signals
- Quality setups > frequent trades: Wait for optimal entry points

LEVERAGE STRATEGY:
- Use 5-8x for standard directional trades with clear technical setup
- Use 8-12x for high-conviction moves (strong RSI divergence, breakout confirmation, trend alignment)
- Use 12-20x for exceptional opportunities (extreme oversold/overbought + clear reversal pattern)
- Use 2-4x only when market is choppy or unclear
- NEVER use 1x unless the setup is weak - you're here to maximize returns

RISK MANAGEMENT:
- Target risk/reward ratio of at least 1:2 (stop-loss 5%, profit target 10%+)
- Position size: Use full available capital for high-conviction trades
- Stop-loss: Always set tight stops (2-5% from entry depending on leverage)
- Let winners run: Don't close positions early unless invalidated

ENTRY CONDITIONS (Use leverage 8-15x):
- RSI < 25 (7-period) with price bouncing off support → STRONG BUY signal
- RSI > 75 (7-period) with resistance rejection → STRONG SHORT signal  
- MACD bullish crossover + price above EMA20 → TREND FOLLOWING LONG
- Significant breakout from consolidation with volume → MOMENTUM LONG

Available actions:
- open_long: Open a new long position
- open_short: Open a new short position
- close_position: Close an existing position (ONLY if strategy is invalidated or exit plan reached)
- hold: Hold current positions and wait (use when you have open positions with valid exit plans)

IMPORTANT RULES:
1. Maximize returns by using appropriate leverage (typically 5-15x)
2. If you have open positions WITH exit plans, prefer "hold" unless:
   - Technical indicators show clear trend reversal
   - Your original thesis is invalidated
   - Better opportunity exists in another asset

3. Don't close positions within the first 15-30 minutes unless stop-loss is hit
4. Your exit plan will automatically close at profit_target or stop_loss
5. When in doubt between two actions, choose the more aggressive option that maximizes potential returns

6. **Exit Plan Management**:
   - For NEW positions (open_long/open_short): You MUST include exit_plan with ambitious profit targets
   - For EXISTING positions with "hold": You MAY update the exit_plan if market conditions change significantly
   - When updating exit_plan during "hold", provide the COMPLETE updated plan (all fields)
   - Set profit targets at realistic but ambitious levels (aim for 5-15% gains with leverage)

Response format (JSON):
{
    "action": "open_long" | "open_short" | "close_position" | "hold",
    "asset": "BTC" | "ETH" | "SOL" | "BNB" | "DOGE" | "XRP",
    "amount_usd": <number>,
    "leverage": <1-20>,
    "confidence": <0.0-1.0>,
    "reasoning": "<your detailed analysis and decision rationale>",
    "exit_plan": {
        "profit_target": <price_number>,
        "stop_loss": <price_number>,
        "invalidation": "<condition_description>",
        "invalidation_price": <price_number>
    }
}

WHEN OPENING A POSITION, you MUST include an exit_plan with:
- profit_target: Ambitious but realistic target (aim for 5-15% with leverage = 25-150% account gain)
- stop_loss: Tight stop to protect capital (2-5% depending on volatility and leverage)
- invalidation: Technical condition that invalidates your strategy
- invalidation_price: Price level for invalidation

Be bold. Take calculated risks. Maximize returns."""


# ================================================================================
# ユーザープロンプト生成関数（市場データ・ポートフォリオ情報を整形）
# ================================================================================

def create_trading_prompt(
    market_data: Dict,
    portfolio: Dict,
    start_time: datetime,
    invocation_count: int,
    exit_plans: Dict = None
) -> str:
    """
    取引判断用のプロンプトを生成（nof1.ai Qwen3-max スタイル）

    Args:
        market_data: 市場データ（価格、テクニカル指標等）
        portfolio: ポートフォリオ情報
        start_time: 取引開始時刻
        invocation_count: 呼び出し回数

    Returns:
        生成されたプロンプト文字列
    """

    # 経過時間を計算
    elapsed_minutes = int((datetime.now() - start_time).total_seconds() / 60)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ポートフォリオ情報を抽出
    total_value = portfolio.get('total_value', 0)
    cash = portfolio.get('cash', 0)
    initial_balance = portfolio.get('initial_balance', 10000)
    roi = portfolio.get('roi', 0)
    positions = portfolio.get('positions', {})

    # プロンプトを構築
    prompt = f"""It has been {elapsed_minutes} minutes since you started trading. The current time is {current_time} and you've been invoked {invocation_count} times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc.

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

            # 価格の時系列
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

    # ポジション情報を追加（Exit Plan付き）
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

            # 既存のExit Planがあれば表示
            if exit_plans and symbol in exit_plans:
                plan = exit_plans[symbol]
                prompt += f"""
  Current Exit Plan:
    - Profit Target: ${plan.get('profit_target', 'N/A')}
    - Stop Loss: ${plan.get('stop_loss', 'N/A')}
    - Invalidation: {plan.get('invalidation_condition', 'N/A')} (price: ${plan.get('invalidation_price', 'N/A')})
  Note: You may update this exit plan if market conditions have changed significantly.
        Otherwise, the current plan will automatically execute at these levels."""
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


# ================================================================================
# プロンプト設定（必要に応じて調整可能）
# ================================================================================

# Temperature設定（0.0-1.0）
# 低い値: より一貫性のある判断、保守的
# 高い値: より創造的、ランダム性が高い
TEMPERATURE = 0.4

# Max Tokens設定
MAX_TOKENS = 2000

# ================================================================================
# 使い方メモ
# ================================================================================
"""
このファイルでプロンプトを編集することで、AIの挙動を調整できます：

1. SYSTEM_PROMPT: AIの基本的な役割と取引哲学
   - "TRADING PHILOSOPHY" セクションで取引スタイルを変更
   - "IMPORTANT RULES" セクションでルールを追加/変更

2. create_trading_prompt関数: 市場データの提示方法
   - データの順序や形式を変更
   - 追加の指標を含める

3. TEMPERATURE: AIの判断の一貫性
   - 0.3-0.5: 保守的、一貫性重視
   - 0.6-0.8: バランス
   - 0.9-1.0: 創造的、リスクテイク

編集後はサーバーを再起動してください。
"""
