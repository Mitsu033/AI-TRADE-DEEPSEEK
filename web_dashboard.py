"""
nof1.ai風 Webダッシュボード
Qwen3-maxを使用したシミュレーション取引ボットのWebインターフェース
"""
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from datetime import datetime
import json
import threading
import time
import os
from sim_trading_bot import SimulationTradingBot

# 現在のディレクトリを取得
basedir = os.path.abspath(os.path.dirname(__file__))

# Flaskアプリケーション初期化（静的ファイルとテンプレートのパスを明示）
app = Flask(__name__,
            static_folder=os.path.join(basedir, 'static'),
            template_folder=os.path.join(basedir, 'templates'))
CORS(app)

# グローバルボットインスタンス
bot = None
bot_lock = threading.Lock()

def init_bot():
    """ボットを初期化"""
    global bot
    if bot is None:
        with bot_lock:
            if bot is None:
                print("🚀 ボットを初期化中...")
                bot = SimulationTradingBot(initial_balance=10000.0)
                # trading_interval は sim_trading_bot.py の設定（1800秒=30分）を使用
                print("✅ ボット初期化完了")
    return bot

# ================== Webページ ==================

@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template('index.html')

@app.route('/debug')
def debug():
    """デバッグ情報"""
    return jsonify({
        "static_folder": app.static_folder,
        "template_folder": app.template_folder,
        "root_path": app.root_path,
        "static_url_path": app.static_url_path,
        "basedir": basedir
    })

@app.route('/positions')
def positions():
    """ポジション表示"""
    return render_template('positions.html')

@app.route('/trades')
def trades():
    """取引履歴"""
    return render_template('trades.html')

@app.route('/performance')
def performance():
    """パフォーマンス統計"""
    return render_template('performance.html')

@app.route('/ai-decisions')
def ai_decisions():
    """AI判断ログ"""
    return render_template('ai_decisions.html')

# ================== API エンドポイント ==================

@app.route('/api/dashboard')
def api_dashboard():
    """ダッシュボードデータを取得"""
    try:
        current_bot = init_bot()
        current_prices = current_bot.market_fetcher.get_current_prices()

        if not current_prices:
            return jsonify({"error": "市場データを取得できませんでした"}), 503

        portfolio = current_bot._get_portfolio_status(current_prices)
        stats = current_bot.db.get_performance_stats()
        trading_status = current_bot.get_trading_status()

        return jsonify({
            "status": "running" if current_bot.is_running else "stopped",
            "trading_status": trading_status,  # 詳細なステータス情報を追加
            "portfolio": {
                "total_value": portfolio['total_value'],
                "cash": portfolio['cash'],
                "positions_value": portfolio['positions_value'],
                "roi": portfolio['roi'],
                "initial_balance": portfolio['initial_balance'],
                "pnl": portfolio['total_value'] - portfolio['initial_balance']
            },
            "stats": {
                "total_trades": stats['total_trades'],
                "winning_trades": stats['winning_trades'],
                "losing_trades": stats['losing_trades'],
                "win_rate": stats['win_rate'],
                "total_pnl": stats['total_pnl']
            },
            "last_trade": current_bot.last_trade_time.isoformat() if current_bot.last_trade_time else None,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/positions')
def api_positions():
    """現在のポジションを取得"""
    try:
        current_bot = init_bot()
        current_prices = current_bot.market_fetcher.get_current_prices()

        if not current_prices:
            # データ初期化中の可能性を確認
            if not current_bot.market_fetcher.is_initialized:
                return jsonify({
                    "error": "データ初期化中です。しばらくお待ちください",
                    "status": "initializing",
                    "positions": []
                }), 200
            else:
                return jsonify({
                    "error": "市場データを取得できませんでした",
                    "status": "no_data",
                    "positions": []
                }), 503

        portfolio = current_bot._get_portfolio_status(current_prices)

        positions = []
        for symbol, pos in portfolio['positions'].items():
            positions.append({
                "symbol": symbol,
                "quantity": pos['quantity'],
                "avg_price": pos['avg_price'],
                "current_price": pos['current_price'],
                "value": pos['value'],
                "pnl": pos['pnl'],
                "pnl_percentage": pos['pnl_percentage'],
                "leverage": pos['leverage']
            })

        return jsonify({
            "positions": positions,
            "total_positions": len(positions),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        print(f"❌ /api/positions エラー: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": f"サーバーエラー: {str(e)}",
            "positions": []
        }), 500

@app.route('/api/trades')
def api_trades():
    """取引履歴を取得"""
    try:
        current_bot = init_bot()
        limit = request.args.get('limit', 50, type=int)
        
        trades = current_bot.db.get_trade_history(limit=limit)
        
        return jsonify({
            "trades": trades,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """パフォーマンス統計を取得"""
    try:
        current_bot = init_bot()
        stats = current_bot.db.get_performance_stats()
        
        # 資産別パフォーマンス
        asset_performance = {}
        for symbol in current_bot.symbols:
            asset_perf = current_bot.db.get_asset_performance(symbol)
            if asset_perf['total_trades'] > 0:
                asset_performance[symbol] = asset_perf
        
        # ポートフォリオ履歴
        snapshots = current_bot.db.get_portfolio_history(limit=100)
        
        return jsonify({
            "stats": stats,
            "asset_performance": asset_performance,
            "portfolio_history": snapshots,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/market')
def api_market():
    """市場データを取得（テクニカル指標を含む）"""
    try:
        current_bot = init_bot()
        current_prices = current_bot.market_fetcher.get_current_prices()

        if not current_prices:
            return jsonify({"error": "市場データを取得できませんでした"}), 503

        market_data = []
        for symbol, data in current_prices.items():
            market_item = {
                "symbol": symbol,
                "price": data.get('price', 0),
                "change_24h": data.get('change_24h', 0),
                "high_24h": data.get('high_24h', 0),
                "low_24h": data.get('low_24h', 0),
                "data_points": data.get('data_points', 0)
            }

            # テクニカル指標を追加（利用可能な場合）
            if 'ema_20' in data and data['ema_20'] is not None:
                market_item['ema_20'] = data['ema_20']
            if 'ema_50_4h' in data and data['ema_50_4h'] is not None:
                market_item['ema_50_4h'] = data['ema_50_4h']
            if 'macd' in data and data['macd'] is not None:
                market_item['macd'] = data['macd']
            if 'rsi_7' in data and data['rsi_7'] is not None:
                market_item['rsi_7'] = data['rsi_7']
            if 'rsi_14' in data and data['rsi_14'] is not None:
                market_item['rsi_14'] = data['rsi_14']
            if 'atr_14_4h' in data and data['atr_14_4h'] is not None:
                market_item['atr_14_4h'] = data['atr_14_4h']

            market_data.append(market_item)

        return jsonify({
            "market": market_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-decisions')
def api_ai_decisions():
    """AI判断履歴を取得"""
    try:
        current_bot = init_bot()
        limit = request.args.get('limit', 50, type=int)
        
        decisions = current_bot.db.get_ai_decisions(limit=limit)
        
        return jsonify({
            "decisions": decisions,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/start', methods=['POST'])
def api_bot_start():
    """ボットを開始"""
    try:
        current_bot = init_bot()
        if current_bot.is_running:
            return jsonify({"message": "既に実行中です", "status": "running"})
        
        current_bot.start_auto_trading()
        return jsonify({"message": "ボットを開始しました", "status": "running"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/stop', methods=['POST'])
def api_bot_stop():
    """ボットを停止"""
    try:
        current_bot = init_bot()
        if not current_bot.is_running:
            return jsonify({"message": "既に停止しています", "status": "stopped"})
        
        current_bot.stop_auto_trading()
        return jsonify({"message": "ボットを停止しました", "status": "stopped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exit-plans')
def api_exit_plans():
    """Exit Plan履歴を取得"""
    try:
        current_bot = init_bot()
        limit = request.args.get('limit', 50, type=int)

        plans = current_bot.db.get_exit_plan_history(limit=limit)

        return jsonify({
            "exit_plans": plans,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exit-plans/active')
def api_active_exit_plans():
    """アクティブなExit Planを取得"""
    try:
        current_bot = init_bot()
        plans = current_bot.db.get_active_exit_plans()

        # 現在価格を追加
        current_prices = current_bot.market_fetcher.get_current_prices()
        for plan in plans:
            symbol = plan['position_symbol']
            if symbol in current_prices:
                plan['current_price'] = current_prices[symbol].get('price', 0)

        return jsonify({
            "exit_plans": plans,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exit-plan/<symbol>')
def api_exit_plan_by_symbol(symbol):
    """特定銘柄のExit Planを取得"""
    try:
        current_bot = init_bot()
        plan = current_bot.db.get_exit_plan_by_symbol(symbol)

        if not plan:
            return jsonify({"error": f"{symbol}のExit Planが見つかりません"}), 404

        # 現在価格を追加
        current_prices = current_bot.market_fetcher.get_current_prices()
        if symbol in current_prices:
            plan['current_price'] = current_prices[symbol].get('price', 0)

        return jsonify({
            "exit_plan": plan,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stream')
def api_stream():
    """SSEでリアルタイム更新をストリーム"""
    def generate():
        while True:
            try:
                current_bot = init_bot()
                current_prices = current_bot.market_fetcher.get_current_prices()
                
                if current_prices:
                    portfolio = current_bot._get_portfolio_status(current_prices)
                    
                    data = {
                        "type": "update",
                        "portfolio": {
                            "total_value": portfolio['total_value'],
                            "cash": portfolio['cash'],
                            "positions_value": portfolio['positions_value'],
                            "roi": portfolio['roi'],
                            "pnl": portfolio['total_value'] - portfolio['initial_balance']
                        },
                        "status": "running" if current_bot.is_running else "stopped",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                
                time.sleep(5)  # 5秒ごとに更新
            except Exception as e:
                print(f"SSE Error: {e}")
                time.sleep(5)
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║   nof1.ai風 Webダッシュボード                                  ║
    ║   Qwen3-max AI取引ボット - シミュレーションモード              ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    # ボットを初期化
    init_bot()

    # Railway用にPORT環境変数からポートを取得
    port = int(os.environ.get('PORT', 5000))

    print(f"\n🌐 Webサーバーを起動中...")
    print(f"📊 ブラウザで http://localhost:{port} を開いてください\n")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

