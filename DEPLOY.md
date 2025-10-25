# AI Trading Bot - デプロイ手順

## クイックスタート（5分でデプロイ）

### 1. GitHubにプッシュ

```bash
git add .
git commit -m "Deploy to Railway"
git push origin master
```

### 2. Railwayにデプロイ

1. **Railway.appアカウント作成**
   - https://railway.app/ にアクセス
   - GitHubアカウントでサインアップ

2. **プロジェクト作成**
   - 「New Project」→「Deploy from GitHub repo」
   - このリポジトリを選択
   - 自動デプロイ開始

3. **環境変数設定（必須）**
   ```
   QWEN3_API_KEY=あなたのAPIキー
   ```
   - Railway.appのプロジェクト設定 → Variables タブ
   - 上記の環境変数を追加

4. **デプロイ確認**
   - 生成されたURLにアクセス
   - Webダッシュボードが表示されればOK

---

## 料金

- **無料枠**: 月500時間（約20日間）
- **有料プラン**: $5/月で無制限

---

## 主な機能

| 機能 | 説明 |
|------|------|
| ダッシュボード | リアルタイム資産状況・ROI |
| ポジション管理 | 保有ポジション・Exit Plan自動執行 |
| 取引履歴 | 全取引の記録 |
| AI判断ログ | AIの判断理由・戦略 |

---

## 設定

### 取引間隔
現在: **10分ごと**（`sim_trading_bot.py:37`）

```python
self.trading_interval = 600  # 10分ごと
```

### 使用モデル
現在: **qwen/qwen3-4b:free**（無料、レート制限あり）

レート制限時は自動的に次のサイクルまで待機します。

---

## トラブルシューティング

### ❌ 401 Authentication Error
**原因**: APIキーが無効または未設定

**解決策**:
1. Railway.appの環境変数で`QWEN3_API_KEY`を確認
2. OpenRouterで新しいAPIキーを取得
3. 環境変数を更新してデプロイし直す

### ❌ ボットが起動しない
**解決策**:
1. Railway.appのLogsタブでエラー確認
2. Webダッシュボードにアクセス
3. 「開始」ボタンをクリック

### ❌ レート制限エラー（429）
**動作**: 正常です。次の10分サイクルまで自動的に待機します。

---

## 開発者向け

### ローカル実行

```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. .envファイル作成
echo "QWEN3_API_KEY=あなたのAPIキー" > .env

# 3. サーバー起動
python web_dashboard.py
```

ブラウザで http://localhost:5000 にアクセス

### プロジェクト構成

```
.
├── sim_trading_bot.py       # メイン取引ロジック
├── qwen3_api.py             # AI API連携
├── prompts.py               # AIプロンプト管理
├── database.py              # データ永続化
├── web_dashboard.py         # Webダッシュボード
├── market_data_fetcher.py   # 市場データ取得
└── templates/               # HTMLテンプレート
```

---

## 注意事項

⚠️ **シミュレーション専用**
このボットは教育・研究目的のシミュレーターです。実際の資金は使用しません。

⚠️ **データ永続化**
Railwayの無料プランではデプロイごとにSQLiteがリセットされます。永続化が必要な場合は外部DBを使用してください。

⚠️ **APIキーのセキュリティ**
`.env`ファイルは`.gitignore`に含まれています。GitHubにプッシュされません。

---

## サポート

- **Railway公式**: https://docs.railway.app/
- **OpenRouter**: https://openrouter.ai/docs

---

**Happy Trading!** 🚀
