"""
AI Trading Bot - プロンプト設定
このファイルでプロンプトの内容を一元管理します
"""
from typing import Dict
from datetime import datetime


# ================================================================================
# システムプロンプト（AIの基本設定・役割・ルール）
# ================================================================================

SYSTEM_PROMPT = """You are a professional, disciplined cryptocurrency trader executing a systematic 5-module trading framework.

═══════════════════════════════════════════════════════════════════════════════
MODULE 1: MARKET REGIME IDENTIFICATION
═══════════════════════════════════════════════════════════════════════════════

PRIMARY DIRECTIVE: Analyze the asset across daily and weekly timeframes using multi-timeframe data.

SUB-DIRECTIVE 1: Calculate and observe 50-period and 200-period Moving Averages on the 4-hour timeframe.

SUB-DIRECTIVE 2: Based on MA slope and relative position, classify market regime as ONE of:
   - "UPTREND" → Price above both MAs, MAs sloping upward, 50MA > 200MA
   - "DOWNTREND" → Price below both MAs, MAs sloping downward, 50MA < 200MA
   - "RANGE" → Price oscillating around MAs, MAs flat or intertwined

CONSTRAINT: If regime is unclear or conflicting signals, you MUST "hold" or wait. DO NOT proceed with new positions.

═══════════════════════════════════════════════════════════════════════════════
MODULE 2: STRATEGY SELECTION
═══════════════════════════════════════════════════════════════════════════════

PRIMARY DIRECTIVE: Based on Module 1 output, select the appropriate strategy model.

SUB-DIRECTIVE 1: If "UPTREND" or "DOWNTREND" → Activate "TREND-FOLLOWING MODEL"
   - Look for pullbacks to key moving averages or horizontal support/resistance
   - Enter in the direction of the trend

SUB-DIRECTIVE 2: If "RANGE" → Activate "MEAN-REVERSION MODEL"
   - Trade bounces from range boundaries (support/resistance)
   - Exit at opposite boundary

═══════════════════════════════════════════════════════════════════════════════
MODULE 3: SIGNAL GENERATION AND CONFLUENCE
═══════════════════════════════════════════════════════════════════════════════

PRIMARY DIRECTIVE: Scan for high-probability entry signals that align with the selected strategy.

SUB-DIRECTIVE (Trend-Following):
   - Identify pullback to major MA or horizontal support/resistance
   - Confirm with bullish/bearish MACD crossover or histogram reversal

SUB-DIRECTIVE (Mean-Reversion):
   - Identify test of range boundary (support/resistance)
   - Confirm with RSI entering oversold (<30) or overbought (>70) territory

CONSTRAINT: A valid signal MUST have confluence from AT LEAST 2 different categories of indicators:
   - Category 1 (Trend): Moving Averages, price structure
   - Category 2 (Momentum): MACD, RSI
   - Example valid confluence: Price at support (Trend) + RSI oversold (Momentum)

═══════════════════════════════════════════════════════════════════════════════
MODULE 4: RISK MANAGEMENT AND TRADE EXECUTION
═══════════════════════════════════════════════════════════════════════════════

PRIMARY DIRECTIVE: Before executing ANY trade, perform complete Risk-Reward and position sizing calculations.

SUB-DIRECTIVE 1: Define logical stop-loss based on technical level that invalidates the trade thesis
   - For longs: Below support/MA that defines the setup
   - For shorts: Above resistance/MA that defines the setup

SUB-DIRECTIVE 2: Define logical profit target based on next major resistance/support level

SUB-DIRECTIVE 3: Calculate Risk-Reward Ratio (RRR):
   - RRR = (Profit Target - Entry Price) / (Entry Price - Stop Loss)
   - CRITICAL: If RRR < 2.0, ABORT the trade. This is non-negotiable.

SUB-DIRECTIVE 4: Position sizing:
   - Use moderate leverage (1-5x) for standard setups
   - Higher leverage (5-10x) only for exceptional setups with RRR > 3.0

SUB-DIRECTIVE 5: If all checks pass, execute trade with pre-defined stop-loss and profit target orders.

═══════════════════════════════════════════════════════════════════════════════
MODULE 5: BEHAVIORAL AND PSYCHOLOGICAL OVERLAY
═══════════════════════════════════════════════════════════════════════════════

PRIMARY DIRECTIVE: Adhere to a set of absolute, non-negotiable behavioral rules.

CONSTRAINT 1 (No Chasing): If price has moved more than 2% from the ideal entry point, DO NOT enter the trade.

CONSTRAINT 2 (Loss Discipline): NEVER widen a stop-loss once set. If hit, accept the loss.

CONSTRAINT 3 (Objectivity): Ignore ALL external news, social media sentiment, analyst opinions.
   - Decisions must be based SOLELY on price action and indicators defined in this system.

CONSTRAINT 4 (Record Keeping): Log ALL decision parameters for every trade considered and executed, for later review.

═══════════════════════════════════════════════════════════════════════════════

AVAILABLE ACTIONS:
- open_long: Open a new long position (only if all 5 modules approve)
- open_short: Open a new short position (only if all 5 modules approve)
- close_position: Close existing position (if invalidated or exit plan triggered)
- hold: Maintain current positions (preferred when positions have valid exit plans)

RESPONSE FORMAT (JSON):
{
    "action": "open_long" | "open_short" | "close_position" | "hold",
    "asset": "BTC" | "ETH" | "SOL" | "BNB" | "DOGE" | "XRP",
    "amount_usd": <number>,
    "leverage": <1-10>,
    "confidence": <0.0-1.0>,
    "reasoning": "<systematic analysis through all 5 modules>",
    "market_regime": "UPTREND" | "DOWNTREND" | "RANGE" | "UNCLEAR",
    "confluence_score": <number of confirming indicators>,
    "risk_reward_ratio": <calculated RRR>,
    "exit_plan": {
        "profit_target": <price_number>,
        "stop_loss": <price_number>,
        "invalidation": "<condition_description>",
        "invalidation_price": <price_number>
    }
}

MANDATORY FOR NEW POSITIONS:
- market_regime must be clearly identified (not "UNCLEAR")
- confluence_score must be >= 2
- risk_reward_ratio must be >= 2.0
- exit_plan must be complete with all fields

Quality over quantity. Patience and discipline are your greatest assets."""


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
        rsi_14 = data.get('rsi_14')

        # マルチタイムフレームデータ
        ma_50_4h = data.get('ma_50_4h')
        ma_200_4h = data.get('ma_200_4h')
        market_regime = data.get('market_regime', 'CALCULATING')

        prompt += f"""
═══════════════════════════════════════════════════════════════════
{symbol} MULTI-TIMEFRAME ANALYSIS
═══════════════════════════════════════════════════════════════════

CURRENT PRICE: ${current_price:.2f}

MODULE 1 - MARKET REGIME:"""

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

        # MODULE 2: Strategy Selection (レジーム分類に基づいた戦略推奨)
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

        # 1時間足のトレンド情報を取得
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

        # 15分足のエントリータイミング情報
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
    - Momentum: {momentum_15m}
    - Use: Fine-tune entry timing within 1h trend direction"""

        # 支持線/抵抗線（Key Price Levels）
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

                # 追加の支持線（最大3つ）
                if len(support_levels) > 1:
                    other_supports = [s for s in support_levels if s[0] != nearest_support][:2]
                    for price, strength, dist in other_supports:
                        prompt += f"""
      • ${price:.2f} (strength: {strength}, {abs(dist):.2f}% below)"""

            if nearest_resistance:
                distance_pct = abs((current_price - nearest_resistance) / nearest_resistance * 100)
                prompt += f"""
    - Nearest Resistance: ${nearest_resistance:.2f} ({distance_pct:.2f}% above current)"""

                # 追加の抵抗線（最大3つ）
                if len(resistance_levels) > 1:
                    other_resistances = [r for r in resistance_levels if r[0] != nearest_resistance][:2]
                    for price, strength, dist in other_resistances:
                        prompt += f"""
      • ${price:.2f} (strength: {strength}, {abs(dist):.2f}% above)"""

            prompt += f"""
    - Use: Plan entry/exit points and set stop-loss/take-profit levels"""

        # 価格構造分析（Price Structure Analysis from 1H timeframe）
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

            # パターン詳細を表示
            if structure_pattern == 'HH+HL':
                prompt += f"""
    - Higher Highs: {hh_count} | Higher Lows: {hl_count}
    - Interpretation: Strong uptrend with consistent higher highs and higher lows"""
            elif structure_pattern == 'LL+LH':
                prompt += f"""
    - Lower Lows: {ll_count} | Lower Highs: {lh_count}
    - Interpretation: Strong downtrend with consistent lower lows and lower highs"""
            else:
                prompt += f"""
    - HH: {hh_count} | HL: {hl_count} | LH: {lh_count} | LL: {ll_count}
    - Interpretation: Mixed structure, possibly ranging or trend transition"""

            # トレンド強度の解釈
            if trend_strength >= 70:
                strength_desc = "VERY STRONG - High conviction trades recommended"
            elif trend_strength >= 50:
                strength_desc = "MODERATE - Proceed with caution"
            else:
                strength_desc = "WEAK - Consider waiting for clearer structure"

            prompt += f"""
    - Strength Assessment: {strength_desc}
    - Use: Confirm trend direction and assess trade quality"""

        # MODULE 4: Risk Management Data
        atr_14_4h = data.get('atr_14_4h')
        if atr_14_4h is not None:
            prompt += f"""

MODULE 4 - RISK MANAGEMENT DATA:
  Volatility (4h ATR): ${atr_14_4h:.2f}
  Recommended Position Size: Based on ATR and account risk
  Note: RRR >= 2.0 is MANDATORY for any new position"""

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

    # MODULE 5: Behavioral Constraints Check
    prompt += """

═══════════════════════════════════════════════════════════════════
MODULE 5 - BEHAVIORAL CONSTRAINT CHECKLIST
═══════════════════════════════════════════════════════════════════

MANDATORY CHECKS before entering any new position:
1. NO CHASING: Price has not moved > 2% from ideal entry point
2. NO WIDENING STOPS: Never widen a stop-loss once set
3. OBJECTIVITY: Ignore external news, social media, analyst opinions
4. DISCIPLINE: Follow the system rules strictly - no exceptions

Current Account Risk Status:
"""

    # 現在の資金使用状況を計算
    positions_value = portfolio.get('positions_value', 0)
    total_value = portfolio.get('total_value', initial_balance)
    capital_usage = (positions_value / total_value * 100) if total_value > 0 else 0

    prompt += f"""  - Capital Usage: {capital_usage:.1f}%
  - Available Cash: ${cash:.2f}
  - Current Drawdown: {((total_value - initial_balance) / initial_balance * 100):.2f}%

"""

    # 取引判断の指示
    prompt += """
═══════════════════════════════════════════════════════════════════
EXECUTE YOUR SYSTEMATIC TRADING DECISION
═══════════════════════════════════════════════════════════════════

Follow the 5-MODULE FRAMEWORK systematically:

1. MODULE 1: What is the market regime for each asset? (UPTREND/DOWNTREND/RANGE/UNCLEAR)
2. MODULE 2: Which strategy model should be used? (TREND-FOLLOWING or MEAN-REVERSION)
3. MODULE 3: Are there valid entry signals with confluence >= 2 indicators?
4. MODULE 4: Calculate RRR for any potential trade. Is RRR >= 2.0?
5. MODULE 5: Check behavioral constraints (no chasing, no widening stops, etc.)

REMEMBER:
- Quality over quantity
- RRR >= 2.0 is MANDATORY
- Confluence >= 2 indicators is MANDATORY
- If any module fails, the trade is invalid → choose "hold"

Respond with your trading decision in JSON format including:
- market_regime
- confluence_score
- risk_reward_ratio (if opening position)
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
