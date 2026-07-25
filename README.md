# DEJ6 IT機器管理システム v2

DEJ6のIT機器(SSP/FS/ZD611/無線機ほか479台)の修理フローを管理するWebツール。
**閲覧は設定不要** — https://trainboy1120-jpg.github.io/dej6-it-mgmt/ を開くだけ。

## v2の設計思想

「人がやるのは物理作業だけ。記録・書類・通知は自動」

| 仕組み | 内容 |
|---|---|
| qr-app自動同期 | SSP管理ツール(Firebase)の故障登録を30分毎に取り込み「修理待ち」へ自動遷移 (GitHub Actions) |
| 今日やることパネル | SIM起票待ち/RMA登録待ち/発送準備OK/要設定 を自動集計しワンクリック処理 |
| SIM本文自動生成 | 対象機器のシリアル/アセット/症状を転記済みの依頼文を生成 |
| RMA登録データ生成 | Zebraポータル貼り付け用の表(症状英訳付き)を生成 |
| Shipping Manifest | 印刷用の送付明細を自動生成。宛先はZebra社/TYO4を機種で自動切替 |
| 朝のダイジェスト | 毎朝8:00に #dej6-it-poc へ修理状況・滞留・実箱との突合を自動投稿 |
| 編集権限 | SA/IT POCメンバーのみ(エイリアス+共有PIN)。全変更は履歴に記録 |

## 機種別修理フロー (JP-OTS Wiki準拠)

- **SSP(TC57) / ZD611**: 修理待ち→SIM起票→RMA登録→発送→返却→正常 (Zebra Direct RMA)
- **FS(RS5100)**: 修理待ち→RMA登録→発送→返却→正常 (SIM不要)
- **無線機(Kenwood)ほか**: 修理待ち→SIM起票→発送→返却→正常 (TYO4青梅FC宛)

発送時の鉄則: Manifest同梱 / 返送先住所確認 / Zebra備考「スワップ禁止」 / 膨張バッテリー発送禁止

## セットアップ(管理者向け・初回のみ)

1. `migration_v2.sql` をSupabase SQL Editorで実行 (v1→v2スキーマ移行+凍結データ棚卸しリセット)
2. Slack Workflow Builderで #dej6-it-poc への「Webhookから開始」ワークフローを作成し、
   URLをリポジトリの Settings → Secrets and variables → Actions → `SLACK_WEBHOOK_URL` に登録
3. アプリの設定(歯車)からZebra送付先住所・DEJ6返送先住所を登録
4. 編集PINをSA/IT POCメンバーに共有

## 構成

```
index.html                    アプリ本体 (GitHub Pages / ゼロセットアップ)
scripts/sync.py               qr-app→Supabase同期 (30分毎 / keep-alive兼用)
scripts/digest.py             朝のSlackダイジェスト (毎朝8:00 JST)
.github/workflows/sync.yml    同期ワークフロー
.github/workflows/digest.yml  ダイジェストワークフロー
migration_v2.sql              v1→v2 マイグレーションSQL
supabase_setup.sql            初期構築SQL (v1・参考)
index_v1_backup.html          v1バックアップ
```

- DB: Supabase (tetigwcotdqgkwfswbyc) — RLS無効の内部運用ツール
- SSP稼働状況: qr-app Firebase (ssp-rental) — 読み取りのみ、qr-app側は変更しない
- 作者: sakrhiro (built with Aki)
