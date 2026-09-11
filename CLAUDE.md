# CLAUDE.md — dej6-it-mgmt (DEJ6 IT機器管理 v2.0)

DEJ6のIT機器(SSP TC57 / FS RS5100 / ZD611 / 無線機)の修理・在庫管理Webアプリ。
GitHub Pages配信 + GitHub Actions 2本。作者: sakrhiro (Aki併用。このファイルはAkiが生成・保守)。

## アーキテクチャ

- `index.html`: 単一ファイルアプリ(閲覧ゼロ設定/編集はalias+共有PIN)
- DB: Supabase `tetigwcotdqgkwfswbyc`(REST直叩き・約479台)
- 外部データ: qr-app Firebase `ssp-rental`(公開DB) — **読み取り専用**
- `scripts/sync.py`: 30分毎 qr-app→Supabase同期 + **keep-alive兼用**
- `scripts/digest.py`: 毎朝8:00 JST Slackダイジェスト
- リモートには `tr/`(TR進捗管理サブアプリ・Supabase同居)あり。**ローカルが古いことがあるので作業前に必ず `git pull`**

## 絶対ルール

1. **`git push` しない**。commitまで。pushは本人が手動(またはAkiがgithub-mcp経由)
2. **PINとSlack Webhook URLをリポジトリに入れない**(PINはSHA-256ハッシュのみコード内可)
3. **qr-app Firebaseは読むだけ**。書き込みコードを追加しない
4. **旧ステータス名の互換(LEGACY)マッピングを消さない**(旧: 修理中/Zebra登録済み/修理完了)
5. Supabase接続は**JS v2クライアント禁止、fetch直叩き**(`apikey`+`Authorization: Bearer`+`Content-Type`)
6. sync.pyのkeep-alive経路を他機能の成否に依存させない(**起動時に必ず1回Supabaseへ触る**構造を維持。
   過去にsync失敗が続いてkeep-alive不達→プロジェクト停止の事故3回)
7. PII禁止(氏名NG・alias運用)。文字コードUTF-8・改行LF・UIとコメントは日本語

## ドメイン知識(ステータスモデル v2)

- 正常 / 修理待ち / SIM起票済み / RMA登録済み / 発送済み / 返却済み
- SSP(TC57), ZD611: 修理待ち→SIM→RMA→発送→返却→正常
- FS(RS5100): SIM不要(修理待ち→RMA→発送→返却→正常)
- 無線機: RMAなし(修理待ち→SIM→発送(TYO4青梅宛)→返却→正常)
- Shipping Manifest必ず同梱 / 膨張バッテリーは発送禁止 / Zebra備考「スワップ禁止」必須

## 変更時の作法

- 詳細な確定事項・再開状態は `_pm_state.md` を先に読む(このリポジトリの正典)
- 変更したら `_pm_state.md` の再開アンカーも更新する
- 動作確認はheadlessブラウザ+dry-runで実測。Actionsのfail通知を放置しない
