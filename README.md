# QWEN3-MAX 自動トレーディングシステム

**Powered by QWEN3 AI + Hyperliquid Exchange**

暗号通貨の自動取引を行うAIトレーディングボットシステムです。QWEN3-MAX AIが市場データを分析し、Hyperliquid取引所で自動的に取引を実行します。

## 📁 プロジェクト構造

```
自動取引DEEPSEEK/
├── config.py              # 設定管理
├── database.py            # データベース管理（SQLite）
├── hyperliquid_api.py     # Hyperliquid取引所API連携
├── market_data.py         # リアルタイム市場データ管理
├── qwen3_api.py           # QWEN3 AI API連携
├── trading_engine.py      # 取引ロジックとポートフォリオ管理
├── trading_bot.py         # メインボットクラス
├── main.py                # エントリーポイント
├── config.json            # 設定ファイル（要作成）
├── trading_data.db        # データベース（自動生成）
└── README.md              # このファイル
```

## 🚀 セットアップ

### 1. 必要なパッケージをインストール

```bash
pip install requests websocket-client
```

### 2. 設定ファイルの作成

初回実行時に`config.json`を作成するか、以下の内容で手動作成してください：

```json
{
  "qwen3_api_key": "your-qwen3-api-key",
  "hyperliquid": {
    "api_key": "your-hyperliquid-api-key",
    "api_secret": "your-hyperliquid-api-secret",
    "testnet": true
  },
  "trading": {
    "initial_balance": 10000.0,
    "trading_interval": 1800,  // 30分ごと（マルチタイムフレーム戦略最適化）
    "symbols": ["BTC", "ETH", "SOL", "BNB", "DOGE", "XRP"],
    "max_position_size": 0.2,
    "max_leverage": 20
  },
  "database": {
    "path": "trading_data.db"
  }
}
```

### 3. APIキーの取得

- **QWEN3 API**: [https://openrouter.ai/](https://openrouter.ai/) でOpenRouter APIキーを取得（QWEN3-MAXモデルにアクセス可能）
- **Hyperliquid API**: [https://hyperliquid.xyz/](https://hyperliquid.xyz/) で取得

⚠️ **重要**: 最初は必ず`testnet: true`でテストしてください！

## 📝 使用方法

### 🚀 Webダッシュボード起動（推奨）

**Windowsの場合:**
```
start_dashboard.bat をダブルクリック
```

**または、コマンドラインから:**
```bash
python web_dashboard.py
```

起動後、ブラウザで `http://localhost:5000` を開いてください。

### 主な機能

- **📊 リアルタイムダッシュボード** - 資産状況、ROI、損益をリアルタイム表示
- **💼 ポジション管理** - 現在のポジションと含み損益を確認
- **📈 取引履歴** - 過去の全取引を確認
- **🧠 AI判断ログ** - AIの取引判断理由を詳細に確認
- **📉 パフォーマンス分析** - 資産別の統計とチャート
- **🎮 ボット制御** - ワンクリックで自動取引の開始/停止

## 🔧 各モジュールの説明

### config.py
設定ファイルの読み込みと作成を管理します。

### database.py
取引履歴、ポートフォリオスナップショット、市場データ、AI判断をSQLiteデータベースに保存・取得します。

### hyperliquid_api.py
Hyperliquid取引所とのAPI通信を担当。市場データ取得、注文発注、ポジション管理を行います。

### market_data.py
WebSocketとREST APIを使用して市場データをリアルタイムで監視・管理します。

### qwen3_api.py
QWEN3 AIに市場データとポートフォリオ情報を送信し、取引判断を取得します。OpenRouter経由でQWEN3-MAXモデルにアクセスします。

### trading_engine.py
取引の実行、ポートフォリオ管理、損益計算、リスク管理を担当します。

### trading_bot.py
すべてのモジュールを統合し、自動取引ループを管理します。

### main.py
プログラムのエントリーポイント。ユーザーインターフェースとメニューを提供します。

## 🛡️ リスク管理

このシステムには以下のリスク管理機能が組み込まれています：

- ✅ 1回の取引で資産の20%まで
- ✅ レバレッジは最大20倍（信頼度に応じて調整）
- ✅ 自動損切り設定（-15%）
- ✅ 分散投資の推奨
- ✅ 取引前のバリデーション
- ✅ 取引頻度: 2分ごと（nof1.ai準拠）

## 📊 データベース

すべての取引データはSQLiteデータベースに保存されます：

- **trades**: 取引履歴
- **portfolio_snapshots**: ポートフォリオの時系列データ
- **market_data**: 市場データ履歴
- **ai_decisions**: AIの判断履歴

## ⚠️ 注意事項

1. **テストネットで十分にテストしてください**
2. **投資は自己責任で行ってください**
3. **APIキーは厳重に管理してください**
4. **定期的にバックアップを取ってください**
5. **市場の急変時には手動介入を検討してください**

## 📈 パフォーマンス追跡

システムは以下の指標を自動的に追跡します：

- 総取引数
- 勝率
- 総損益（PnL）
- 平均損益
- ROI（投資収益率）
- 資産別パフォーマンス

## 🔄 アップデート履歴

### v1.0.0 (2024)
- 初回リリース
- モジュール化された構造
- SQLiteデータベース統合
- リアルタイム市場データ監視
- AI駆動の取引判断

## 📞 サポート

問題が発生した場合は、各モジュールのエラーメッセージを確認してください。
ログは詳細な情報を提供します。

## 📄 ライセンス

このプロジェクトは個人使用のためのものです。

---

**免責事項**: このソフトウェアは教育目的で提供されています。暗号通貨取引は高リスクであり、損失が発生する可能性があります。使用は自己責任で行ってください。

