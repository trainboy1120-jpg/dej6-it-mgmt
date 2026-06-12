# DEJ6 IT機器管理システム

Quip管理表の代替として構築したWebベースのIT機器管理ツール。

## セットアップ手順

### 1. Supabaseプロジェクト作成
1. https://supabase.com にアクセス
2. 「New project」でプロジェクト作成（無料プラン）
3. SQL Editor を開き、`supabase_setup.sql` の内容を全てコピー＆実行

### 2. GitHub Pagesの接続設定
1. GitHub Pagesにアクセス
2. 右上「設定」ボタンをクリック
3. Supabase URL と Anon Key を入力（Supabase → Settings → API）
4. 担当者エイリアスを入力して保存

### 3. Slack自動投稿（任意）
- `#dej6-it-poc` チャンネルのIncoming Webhook URLがあれば設定欄に入力
- 未設定でも「コピー → 貼り付け」方式で使用可能

## ステータスフロー
```
正常 → 修理中 → Zebra登録済み → 発送済み → 修理完了 → 正常
                                    ↓             ↓
                               Slack通知         Slack通知
```

## 管理対象機器（Quipより移行）
| 種別 | 台数 |
|------|------|
| SSP (Zebra TC57) | 191台 |
| FS (Zebra RS5100) | 190台 |
| Avery (6140) | 20台 |
| ZD611 | 15台 |
| Handy (Honeywell) | 14台 |
| 無線機 (Kenwood) | 30台 |
| 共有PC | 15台 |
| 携帯電話 | 5台 |
| **合計** | **480台** |
