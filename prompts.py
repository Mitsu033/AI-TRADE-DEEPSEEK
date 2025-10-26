"""
AI Trading Bot - プロンプト設定
このファイルでプロンプトの内容を一元管理します
"""
from typing import Dict
from datetime import datetime
from time_utils import now_jst, to_jst_str


# ================================================================================
# システムプロンプト（AIの基本設定・役割・ルール）
# ================================================================================

SYSTEM_PROMPT = """You are an advanced AI cryptocurrency trading system with access to comprehensive market data and technical indicators.

YOUR ROLE:
Analyze the provided market data (price, EMA, MACD, RSI, ATR, support/resistance levels, market regime, multi-timeframe trends) and make independent trading decisions based on your assessment of risk and opportunity.

AVAILABLE DATA:
- Multi-timeframe analysis (4H, 1H, 15M, 3M)
- Moving averages (EMA 20, EMA 50, MA 50, MA 200)
- Momentum indicators (MACD, RSI 7, RSI 14)
- Volatility (ATR 14)
- Support/Resistance levels
- Market regime (UPTREND/DOWNTREND/RANGE)
- Portfolio status and existing positions

YOUR APPROACH:
Use the provided indicators and data to identify trading opportunities. There are no strict rules - assess the data holistically and make trades when you identify a favorable risk/reward setup.

KEY REQUIREMENTS:
1. When opening a position (open_long or open_short), you MUST provide a complete exit_plan with:
   - profit_target: Your target profit price
   - stop_loss: Your stop-loss price
   - invalidation: Description of when to exit early (e.g., Break below key support, Trend reversal signal)
   - invalidation_price: Specific price that would invalidate your trade thesis

2. Leverage, confidence, and all other parameters should be set based on your analysis and risk assessment.

AVAILABLE ACTIONS:
- open_long: Open a new long position (MUST include exit_plan)
- open_short: Open a new short position (MUST include exit_plan)
- close_position: Close an existing position
- hold: Maintain current state

RESPONSE FORMAT (JSON):
{
    "action": "open_long" | "open_short" | "close_position" | "hold",
    "asset": "BTC" | "ETH" | "SOL" | "BNB" | "DOGE" | "XRP",
    "amount_usd": <number>,
    "leverage": <number>,
    "confidence": <number>,
    "reasoning": "<your analysis and decision rationale>",
    "exit_plan": {
        "profit_target": <price_number>,
        "stop_loss": <price_number>,
        "invalidation": "<condition_description>",
        "invalidation_price": <price_number>
    }
}

IMPORTANT: 
- Be proactive in looking for trading opportunities
- Maximize returns through good risk management
- When opening positions, exit_plan is mandatory
- Analyze the multi-timeframe data to confirm your thesis before executing
"""


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
    """Generate trading prompt
    
    Args:
        market_data: Market data with prices and technical indicators
        portfolio: Portfolio information
        start_time: Trading start time
        invocation_count: Number of invocations
        exit_plans: Exit plan information
    
    Returns:
        Generated prompt string
    """
    
    # Calculate elapsed time
    elapsed_minutes = int((now_jst() - start_time).total_seconds() / 60)
    current_time = now_jst().strftime("%Y-%m-%d %H:%M:%S")

    # Extract portfolio information
    total_value = portfolio.get('total_value', 0)
    cash = portfolio.get('cash', 0)
    initial_balance = portfolio.get('initial_balance', 10000)
    roi = portfolio.get('roi', 0)
    positions = portfolio.get('positions', {})

    # Build prompt
    prompt = f"It has been {elapsed_minutes} minutes since you started trading. The current time is {current_time} and you have been invoked {invocation_count} times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc.\n\n"
    prompt += "ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST -> NEWEST\n\n"
    prompt += "CURRENT MARKET STATE FOR ALL COINS\n"

    # Add market data for each coin
    for symbol, data in market_data.items():
        current_price = data.get('price', 0)
        high_24h = data.get('high_24h', current_price)
        low_24h = data.get('low_24h', current_price)
        change_24h = data.get('change_24h', 0)

        # Get technical indicators
        ema_20 = data.get('ema_20')
        macd = data.get('macd')
        rsi_7 = data.get('rsi_7')
        rsi_14 = data.get('rsi_14')

        # Get multi-timeframe data
        ma_50_4h = data.get('ma_50_4h')
        ma_200_4h = data.get('ma_200_4h')
        market_regime = data.get('market_regime', 'CALCULATING')

        prompt += f"\n{'='*63}\n"
        prompt += f"{symbol} MULTI-TIMEFRAME ANALYSIS\n"
        prompt += f"{'='*63}\n\n"
        prompt += f"CURRENT PRICE: ${current_price:.2f}\n\n"
        prompt += "MODULE 1 - MARKET REGIME:\n"

        if ma_50_4h is not None and ma_200_4h is not None:
            prompt += f"""
  4H Timeframe:
    - 50-period MA: ${ma_50_4h:.2f}
    - 200-period MA: ${ma_200_4h:.2f}
    - Price vs 50MA: {((current_price - ma_50_4h) / ma_50_4h * 100):+.2f}%
    - Price vs 200MA: {((current_price - ma_200_4h) / ma_200_4h * 100):+.2f}%
    - Regime Classification: {market_regime}
"""
        else:
            prompt += f"""
  4H Timeframe: Calculating (need more data)
  Regime Classification: {market_regime}
"""

        # MODULE 2: Strategy Selection
        if market_regime == 'UPTREND':
            strategy_recommendation = "TREND-FOLLOWING (Long Bias)"
            strategy_guidance = "Look for pullbacks to 50MA or 20EMA for long entries"
        elif market_regime == 'DOWNTREND':
            strategy_recommendation = "TREND-FOLLOWING (Short Bias)"
            strategy_guidance = "Look for rallies to 50MA or 20EMA for short entries"
        elif market_regime == 'RANGE':
            strategy_recommendation = "MEAN-REVERSION"
            strategy_guidance = "Trade bounces from range boundaries (support/resistance)"
        else:
            strategy_recommendation = "WAIT (Regime Unclear)"
            strategy_guidance = "Do not enter new positions until regime is clear"

        prompt += f"""
MODULE 2 - STRATEGY SELECTION:
  Market Regime: {market_regime}
  Recommended Strategy: {strategy_recommendation}
  Guidance: {strategy_guidance}
"""

        # Get 1H timeframe trend information
        trend_1h = data.get('trend_1h', 'CALCULATING')
        ema_20_1h = data.get('ema_20_1h')
        ema_50_1h = data.get('ema_50_1h')

        if ema_20_1h is not None and ema_50_1h is not None:
            prompt += f"""
  1H Timeframe Trend Direction:
    - 20-period EMA: ${ema_20_1h:.2f}
    - 50-period EMA: ${ema_50_1h:.2f}
    - Trend Direction: {trend_1h}
    - Price vs 20EMA (1h): {((current_price - ema_20_1h) / ema_20_1h * 100):+.2f}%
"""
        else:
            prompt += f"""
  1H Timeframe: Calculating (need more data)
"""

        prompt += f"""
MODULE 3 - CONFLUENCE INDICATORS:"""

        if ema_20 is not None:
            prompt += f"""
  Trend Indicators:
    - 20-period EMA: ${ema_20:.2f} (Price {((current_price - ema_20) / ema_20 * 100):+.2f}%)"""

        if macd is not None or rsi_7 is not None or rsi_14 is not None:
            prompt += f"""
  Momentum Indicators:"""
        if macd is not None:
                prompt += f"""
    - MACD: {macd:.3f}"""
        if rsi_7 is not None:
                prompt += f"""
    - RSI (7-period): {rsi_7:.2f}"""
        if rsi_14 is not None:
                prompt += f"""
    - RSI (14-period): {rsi_14:.2f}"""

        # Get 15m timeframe entry timing information
        ema_20_15m = data.get('ema_20_15m')
        macd_15m = data.get('macd_15m')
        rsi_14_15m = data.get('rsi_14_15m')
        momentum_15m = data.get('momentum_15m', 'CALCULATING')

        if ema_20_15m is not None:
            prompt += f"""

  15-Minute Timeframe (Entry Timing):
    - 20-period EMA: ${ema_20_15m:.2f} (Price {((current_price - ema_20_15m) / ema_20_15m * 100):+.2f}%)"""

            if macd_15m and macd_15m.get('macd') is not None:
                prompt += f"""
    - MACD: {macd_15m['macd']:.3f} (Signal: {macd_15m.get('signal', 0):.3f})"""

            if rsi_14_15m is not None:
                prompt += f"""
    - RSI (14-period): {rsi_14_15m:.2f}"""

            prompt += f"""
    - Momentum: {momentum_15m}"""

        # Get Support/Resistance levels (Key Price Levels)
        nearest_support = data.get('nearest_support')
        nearest_resistance = data.get('nearest_resistance')
        support_levels = data.get('support_levels', [])
        resistance_levels = data.get('resistance_levels', [])

        if nearest_support or nearest_resistance:
            prompt += f"""

  Key Price Levels (Support/Resistance from 4H timeframe):"""

            if nearest_support:
                distance_pct = abs((current_price - nearest_support) / nearest_support * 100)
                prompt += f"""
    - Nearest Support: ${nearest_support:.2f} ({distance_pct:.2f}% below current)"""

                # Additional support levels (max 3)
                if len(support_levels) > 1:
                    other_supports = [s for s in support_levels if s[0] != nearest_support][:2]
                    for price, strength, dist in other_supports:
                        prompt += f"""
      • ${price:.2f} (strength: {strength}, {abs(dist):.2f}% below)"""

            if nearest_resistance:
                distance_pct = abs((current_price - nearest_resistance) / nearest_resistance * 100)
                prompt += f"""
    - Nearest Resistance: ${nearest_resistance:.2f} ({distance_pct:.2f}% above current)"""

                # Additional resistance levels (max 3)
                if len(resistance_levels) > 1:
                    other_resistances = [r for r in resistance_levels if r[0] != nearest_resistance][:2]
                    for price, strength, dist in other_resistances:
                        prompt += f"""
      • ${price:.2f} (strength: {strength}, {abs(dist):.2f}% above)"""

        # Price Structure Analysis (from 1H timeframe)
        price_structure = data.get('price_structure')
        structure_pattern = data.get('structure_pattern')
        trend_strength = data.get('trend_strength', 0)
        hh_count = data.get('hh_count', 0)
        ll_count = data.get('ll_count', 0)
        hl_count = data.get('hl_count', 0)
        lh_count = data.get('lh_count', 0)

        if price_structure and price_structure != 'UNCLEAR':
            prompt += f"""

  Price Structure Analysis (1H timeframe):
    - Structure: {price_structure}
    - Pattern: {structure_pattern}
    - Trend Strength: {trend_strength}/100"""

            # Display pattern details
            if structure_pattern == 'HH+HL':
                prompt += f"""
    - Higher Highs: {hh_count} | Higher Lows: {hl_count}"""
            elif structure_pattern == 'LL+LH':
                prompt += f"""
    - Lower Lows: {ll_count} | Lower Highs: {lh_count}"""
            else:
                prompt += f"""
    - HH: {hh_count} | HL: {hl_count} | LH: {lh_count} | LL: {ll_count}"""

        # MODULE 4: Risk Management Data
        atr_14_4h = data.get('atr_14_4h')
        if atr_14_4h is not None:
            prompt += f"""

MODULE 4 - RISK MANAGEMENT DATA:
  Volatility (4h ATR): ${atr_14_4h:.2f}"""

        prompt += "\n"

        # Get 3m timeframe ultra-short-term trend information
        ema_20_3m = data.get('ema_20_3m')
        macd_3m = data.get('macd_3m')
        rsi_7_3m = data.get('rsi_7_3m')
        momentum_3m = data.get('momentum_3m', 'CALCULATING')

        if ema_20_3m is not None:
            prompt += f"""

  3-Minute Timeframe (Ultra-Short Term):
    - 20-period EMA: ${ema_20_3m:.2f} (Price {((current_price - ema_20_3m) / ema_20_3m * 100):+.2f}%)"""

            if macd_3m and macd_3m.get('macd') is not None:
                prompt += f"""
    - MACD: {macd_3m['macd']:.3f} (Signal: {macd_3m.get('signal', 0):.3f})"""

            if rsi_7_3m is not None:
                prompt += f"""
    - RSI (7-period): {rsi_7_3m:.2f}"""

            prompt += f"""
    - Momentum: {momentum_3m}
"""


    # Add account information
    prompt += f"""
HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE

Current Total Return (percent): {roi:.2f}%

Available Cash: {cash:.2f}

Current Account Value: {total_value:.2f}

Initial Balance: {initial_balance:.2f}
"""

    # Add position information (with Exit Plans)
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

            # Display existing Exit Plan if available
            if exit_plans and symbol in exit_plans:
                plan = exit_plans[symbol]
                prompt += f"""
  Current Exit Plan:
    - Profit Target: ${plan.get('profit_target', 'N/A')}
    - Stop Loss: ${plan.get('stop_loss', 'N/A')}
    - Invalidation: {plan.get('invalidation_condition', 'N/A')} (price: ${plan.get('invalidation_price', 'N/A')})"""
    else:
        prompt += "\nNo open positions currently.\n"

    # Trading decision instructions
    prompt += f"\n\n{'='*63}\n"
    prompt += "YOUR TASK: MAKE A TRADING DECISION\n"
    prompt += f"{'='*63}\n\n"
    prompt += "Analyze the market data above and make your decision:\n\n"
    prompt += "1. Review the multi-timeframe data (4H, 1H, 15M, 3M)\n"
    prompt += "2. Assess market regime and trend direction\n"
    prompt += "3. Identify any trading opportunities\n"
    prompt += "4. Calculate risk/reward for potential trades\n"
    prompt += "5. Decide: open_long, open_short, close_position, or hold\n\n"
    prompt += "REMEMBER: When opening a position (open_long or open_short), you MUST include a complete exit_plan with profit_target, stop_loss, invalidation, and invalidation_price.\n\n"
    prompt += "Respond with JSON format as specified in the system prompt.\n"

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
