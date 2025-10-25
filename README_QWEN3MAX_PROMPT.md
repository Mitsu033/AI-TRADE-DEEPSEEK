# Qwen3-max プロンプト改善（nof1.ai スタイル）

## 📊 改善の背景

nof1.aiの実際の[Qwen3-maxモデル](https://nof1.ai/models/qwen3-max)の取引データを分析し、同様の成果を出せるようにプロンプトを最適化しました。

### nof1.ai Qwen3-max の実績データ

| 指標 | 値 |
|------|-----|
| **Total Account Value** | $16,099.53 |
| **ROI** | +60.99% |
| **Average Leverage** | 15.4x |
| **Average Confidence** | 81.7% |
| **Biggest Win** | $1,453 |
| **Biggest Loss** | -$586.18 |
| **Hold Times** | Long: 16.5% / Short: 1.8% / **Flat: 81.6%** |

---

## 🔑 主要な改善点

### 1. **慎重な取引戦略**
```
❌ 旧: 積極的な取引を推奨
✅ 新: 81.6%の時間はフラット（様子見）を推奨
```

実際のQwen3-maxは**非常に選択的**で、明確なチャンスがある時だけエントリーします。

### 2. **レバレッジ範囲の拡大**
```
❌ 旧: 1-10x
✅ 新: 1-20x（信頼度に応じて）
```

- **15-20x**: 信頼度 >0.85 かつ強いトレンド
- **10-15x**: 信頼度 >0.75 の中程度のセットアップ
- **5-10x**: 不確実だが有望なセットアップ

### 3. **高い信頼度の要求**
```
❌ 旧: 特に基準なし
✅ 新: 信頼度 >0.80 を目標（平均81.7%）
```

### 4. **具体的な撤退条件**
```javascript
// 新しいフィールド追加
"exit_condition": "4-hour candle closes below 105000"
```

チャートベースの具体的な条件を設定します。

### 5. **判断スタイル**
```
❌ 旧: 冗長な説明
✅ 新: 簡潔で数値重視

例: "Up 60% with $16k account value. Holding BTC 20x leverage, 
     confident at 0.88, exit if price closes below 105000 on 4-hour chart."
```

### 6. **資産の優先順位**
```
✅ BTC と ETH を優先（実績データに基づく）
```

---

## 📝 新しいプロンプトの特徴

### Key Principles
- **Be selective and patient** - ほとんどの時間はholdすべき
- **High confidence only** - 信頼度 >0.80 の取引のみ
- **Strategic leverage** - 1-20x（状況に応じて）
- **Focus on BTC/ETH** - 最も信頼性が高い
- **Specific exit conditions** - 価格レベルとチャートパターン

### Risk Management
```
• High leverage (15-20x): confidence >0.85 + strong trend
• Medium leverage (10-15x): confidence >0.75
• Low leverage (5-10x): uncertain but promising
• Always set stop-loss and take-profit
• Use chart-based conditions
```

### Decision Guidelines
```
• HOLD: no clear opportunity or existing position valid
• BUY: strong uptrend + high confidence + clear exit plan
• SELL: stop-loss met or better opportunity exists
```

---

## 🔧 技術的な変更

### 1. qwen3_api.py
- プロンプトをnof1.ai QWEN3-MAXスタイルに完全リライト
- 英語プロンプトに変更（より正確な指示のため）
- `exit_condition` フィールドを追加

### 2. config.py & config.json
```json
{
  "trading": {
    "max_leverage": 20  // 10 から 20 に変更
  }
}
```

### 3. templates/ai_decisions.html
- `exit_condition` を表示する機能を追加
- ⚠️ アイコンとオレンジ色で視覚的に強調

### 4. templates/layout.html
- Chart.js用の日時アダプターを追加
- 資産推移チャートの時系列表示を修正

---

## 📈 期待される効果

### Before (旧プロンプト)
- ランダムな取引頻度
- 低〜中レバレッジ（1-10x）
- 不明確な撤退条件
- 冗長な説明

### After (新プロンプト)
- **選択的な取引** - 高品質なセットアップのみ
- **戦略的レバレッジ** - 信頼度に応じて最大20x
- **明確な撤退条件** - チャートベースの具体的な価格
- **簡潔な判断** - 数値と条件を明示

---

## 🚀 使用方法

### 1. Webダッシュボードを起動
```bash
# Windows
start_webdashboard.bat

# Mac/Linux
python web_dashboard.py
```

### 2. ブラウザでアクセス
```
http://localhost:5000
```

### 3. AI判断ログを確認
- **タブ**: AI判断ログ
- **新機能**: 撤退条件が表示される
- **確認項目**:
  - 信頼度が 80% 以上
  - レバレッジが適切（5-20x）
  - 具体的な exit_condition

---

## 📊 実装されたnof1.ai機能

### ✅ 実装済み
- [x] 資産推移チャート（折れ線グラフ）
- [x] AI判断ログ（タイムライン）
- [x] ポジション管理
- [x] 取引履歴
- [x] パフォーマンス統計
- [x] ダーク/ライトモード切り替え
- [x] リアルタイム更新
- [x] 具体的な撤退条件表示

### 🔄 今後の拡張可能機能
- [ ] モデル選択（複数AIモデルの比較）
- [ ] 4時間足チャート表示
- [ ] ウォレットリンク
- [ ] ファンディングコストの計算
- [ ] より詳細な取引統計

---

## 🎯 成功指標

nof1.aiのQwen3-maxと同様の結果を目指します：

| 目標 | 値 |
|------|-----|
| **ROI** | +50% 以上 |
| **Flat Time** | 80% 前後 |
| **Average Confidence** | 80% 以上 |
| **Win Rate** | 勝率向上 |
| **Max Leverage** | 状況に応じて最大20x |

---

## 📝 参考資料

- [nof1.ai公式サイト](https://nof1.ai)
- [Qwen3-max詳細ページ](https://nof1.ai/models/qwen3-max)
- [Alpha Arena競技ルール](https://nof1.ai)

---

## 📞 トラブルシューティング

### Q: AIがholdばかりしてトレードしない
A: これは正常です。nof1.aiのQwen3-maxも81.6%の時間はフラットです。高品質なセットアップを待っています。

### Q: レバレッジが20xで怖い
A: 信頼度が85%以上の時のみ高レバレッジを使用します。低信頼度の場合は5-10xです。

### Q: exit_conditionが表示されない
A: AIが設定しなかった可能性があります。プロンプトは推奨していますが、強制ではありません。

---

**更新日**: 2025-10-25  
**バージョン**: 2.0 (nof1.ai Qwen3-max Style)

