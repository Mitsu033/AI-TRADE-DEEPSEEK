# Railway.app デプロイガイド

このガイドでは、AI取引ボットをRailway.appにデプロイする手順を説明します。

## 料金プラン

- **無料枠**: 月500時間まで無料（約20日間の常時稼働）
- **有料プラン**: $5/月で無制限

---

## デプロイ手順

### 1. GitHubリポジトリの準備

```bash
# ローカルでGitリポジトリを初期化
git init
git add .
git commit -m "Initial commit for Railway deployment"

# GitHubにプッシュ（既存リポジトリがある場合）
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Railway.appアカウント作成

1. https://railway.app/ にアクセス
2. GitHubアカウントでサインアップ

### 3. プロジェクトのデプロイ

1. Railway.appダッシュボードで「New Project」をクリック
2. 「Deploy from GitHub repo」を選択
3. リポジトリを選択
4. 自動的にデプロイが開始されます

### 4. 環境変数の設定（オプション）

Railway.appのプロジェクト設定で以下の環境変数を設定できます：

```
QWEN3_API_KEY=your_api_key_here
```

※ 現在は`qwen3_api.py`にAPIキーがハードコードされていますが、環境変数に移行することを推奨します。

### 5. デプロイ確認

1. Railway.appのダッシュボードで「Deployments」タブを確認
2. デプロイが成功したら、生成されたURLにアクセス
3. Webダッシュボードが表示されればOK！

---

## 重要な設定

### ポート設定
Railway.appは自動的に`PORT`環境変数を設定します。
`web_dashboard.py`は既に対応済みです。

### データベース
SQLiteデータベースはエフェメラルストレージに保存されます。
**デプロイごとにデータがリセットされます。**

永続化が必要な場合は：
- Railway PostgreSQL（有料プラン）
- 外部データベースサービス

---

## トラブルシューティング

### ログの確認
Railway.appのダッシュボードで「Logs」タブからリアルタイムログを確認できます。

### デプロイが失敗する場合
1. `requirements.txt`のライブラリバージョンを確認
2. ログでエラーメッセージを確認
3. Procfileの起動コマンドを確認

### ボットが自動起動しない場合
Webダッシュボードにアクセスして「開始」ボタンをクリックしてください。

---

## 使用方法

1. デプロイされたURLにアクセス
2. 「開始」ボタンをクリックして自動取引を開始
3. ポジション、取引履歴、パフォーマンスを確認

### 主な機能
- **ダッシュボード**: リアルタイムの資産状況
- **ポジション**: 現在の保有ポジションとExit Plan
- **取引履歴**: 全取引の履歴
- **パフォーマンス**: 統計とチャート
- **AI判断**: AIの判断理由とExit Plan

---

## コスト管理

### 無料枠を最大限活用
- 月500時間 = 約20日間の常時稼働
- 取引サイクル: 3分ごと
- 1日あたり約480回の取引判断

### 有料プランへの移行
24/7稼働が必要な場合は$5/月プランを推奨。

---

## セキュリティ

### APIキーの保護
1. Railway.appの環境変数にAPIキーを設定
2. `qwen3_api.py`を以下のように修正：

```python
import os

QWEN3_API_KEY = os.environ.get('QWEN3_API_KEY', 'fallback_key')
```

3. GitHubにAPIキーをプッシュしないように注意

---

## サポート

問題が発生した場合：
1. Railway.appのログを確認
2. Railway.app公式ドキュメント: https://docs.railway.app/
3. Discordコミュニティ: https://discord.gg/railway

---

## 次のステップ

- [ ] GitHubリポジトリを作成
- [ ] Railway.appアカウントを作成
- [ ] デプロイを実行
- [ ] 環境変数を設定（推奨）
- [ ] Webダッシュボードにアクセス
- [ ] 自動取引を開始

**Happy Trading!** 🚀
