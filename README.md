# DEJ6 IT機器管理システム v2.2

DEJ6のIT機器(SSP/FS/ZD611/無線機ほか479台)の修理フローを管理するWebツール。
**閲覧は設定不要** — https://trainboy1120-jpg.github.io/dej6-it-mgmt/ を開くだけ。

## v2の設計思想

「人がやるのは物理作業だけ。記録・書類・通知は自動」

| 仕組み | 内容 |
|---|---|
| スキャン受付 (v2.2) | `index.html?mode=scan` を故障BOX前の PC でキオスク表示。USB スキャナで 端末QR→FAULT QR を読むと「修理待ち」、返却済みの端末を読むと「正常」。旧 qr-app(Firebase) の同期は v2.2 で停止 |
| 棚卸 (v2.2) | 修理デーの冒頭に「修理依頼品 BOX の実物 ⇄ ツールの修理待ち」を突合。BOX に無い個体は「保留」(内訳外・滞留アラート外)、BOX 内の未登録品はその場で修理待ちに登録 |
| FS 数量管理 (v2.2) | FS(RS5100) は個体でなく台数で管理(稼働 / 修理待ち(BOX) / 発送中 / 返却済み・要設定 / 総台数 の5区分、合計=総台数)。発送はロット単位(fs_lots) |
| 修理デー・担当 (v2.2) | 設定の「今月の修理デー(日付リスト)」と担当ローテを「今日やること」に表示。`*` 付きの日は棚卸あり |
| 故障回数 (v2.2) | 修理待ちへの遷移ごとに `devices.fault_count` +1(旧 qr-app の実績 44台/64回を `scripts/import_qrapp.py` で初期投入)。2回=黄、3回以上=赤バッジ |
| 今日やることパネル | SIM起票待ち/RMA登録待ち/発送準備OK/要設定 を自動集計しワンクリック処理 |
| SIM本文自動生成 | 対象機器のシリアル/アセット/症状を転記済みの依頼文を生成 |
| RMA登録データ生成 | Zebraポータル貼り付け用の表(症状英訳付き)を生成 |
| Shipping Manifest | 印刷用の送付明細を自動生成。宛先はZebra社/TYO4を機種で自動切替 |
| 朝のダイジェスト | 毎朝8:00に #dej6-it-poc へ修理状況・滞留・実箱との突合を自動投稿 |
| 編集権限 | SA/IT POCメンバーのみ(エイリアス+共有PIN)。全変更は履歴に記録 |
| 修理手順ガイド (v2.1) | ナビ[修理手順]または機器モーダルの「この機種の修理手順」から、機種別の手順(A 修理前に試す / B フロー / C 復帰チェック / D リンク集 / E 発送の鉄則)を表示。現在ステータスに「いまここ」印。`?guide=SSP` 等のディープリンク・URLコピー・印刷(A4)対応 |

## 機種別修理フロー (JP-OTS Wiki準拠)

- **SSP(TC57) / ZD611**: 修理待ち→SIM起票→RMA登録→発送→返却→正常 (Zebra Direct RMA)
- **FS(RS5100)**: 修理待ち→RMA登録→発送→返却→正常 (SIM不要)
- **無線機(Kenwood)ほか**: 修理待ち→SIM起票→発送→返却→正常 (TYO4青梅FC宛)

発送時の鉄則: Manifest同梱 / 返送先住所確認 / Zebra備考「スワップ禁止」 / 膨張バッテリー発送禁止

## セットアップ(管理者向け・初回のみ)

1. `migration_v2.sql` をSupabase SQL Editorで実行 (v1→v2スキーマ移行+凍結データ棚卸しリセット)
1-2. **v2.2**: `migration_v2_2.sql` を Supabase SQL Editor で実行(fault_count / repair_history.event / fs_lots + RPC / app_config 既定値 / 旧同期分の legacy 化。再実行安全)→ `py scripts/import_qrapp.py`(dry-run)→ `py scripts/import_qrapp.py --apply` で故障回数を投入
2. Slack Workflow Builderで #dej6-it-poc への「Webhookから開始」ワークフローを作成し、
   URLをリポジトリの Settings → Secrets and variables → Actions → `SLACK_WEBHOOK_URL` に登録
3. アプリの設定(歯車)からZebra送付先住所・DEJ6返送先住所を登録
4. 編集PINをSA/IT POCメンバーに共有

## 構成

```
index.html                    アプリ本体 (GitHub Pages / ゼロセットアップ)
scripts/sync.py               qr-app→Supabase同期 (v2.2 で定期実行停止。手動 workflow_dispatch のみ・履歴用に残置)
scripts/import_qrapp.py       v2.2 故障回数の初期投入(qrapp-capture snapshot → devices.fault_count。dry-run 既定)
scripts/digest.py             朝のSlackダイジェスト (毎朝8:00 JST)
.github/workflows/sync.yml    同期ワークフロー(v2.2: schedule なし)
.github/workflows/digest.yml  ダイジェストワークフロー
migration_v2.sql              v1→v2 マイグレーションSQL
migration_v2_2.sql            v2.2 マイグレーションSQL(fault_count / event / v_hold_latest / fs_lots+トリガー / RPC fs_ship・fs_unship・fs_set_wait / 既定値 / legacy 化)
supabase_setup.sql            初期構築SQL (v1・参考)
index_v1_backup.html          v1バックアップ
docs/repair_guide_plan.md     v2.1 修理手順ガイドの設計プラン(cross-model review PASS)
docs/mockup/                  v2.1 モック・実装スクショ・チェッカー(識別子衝突/1行1操作)
tests/run_all.py              テスト一括実行 (v2.1: test_repair_guide.py + test_repair_guide_e2e.py / v2.2: test_v22.py + test_v22_e2e.py)
```

### v2.1 修理手順ガイドの更新方法
- 手順本文は `index.html` 内の定数 `GUIDE_DATA`(機種別) / `GUIDE_STEP_BASE`(ステータス共通)。編集後は `py tests/run_all.py` で全PASSを確認(1ステップ1操作・フローとの整合・リンクが https であることを機械チェック)
- e2e は Supabase/Firebase をスタブして file:// で動くため、実データには触れない。要: `py -m pip install playwright` + `py -m playwright install chromium`
- 手順の出典は JP-OTS QuickLink Wiki。訂正・追加は #dej6-it-poc へ

### v2.2 運用メモ(スキャン受付・棚卸・FS)
- **Firebase(qr-app) は参照しない。** `index.html` から Firebase への通信を撤去し、`sync.yml` の cron を削除した(手動実行のみ残る)。旧同期で登録された個体は `fault_source='legacy'` に変わり、以後 sync.py が実行されても触られない
- **スキャン受付の PC**: `?mode=scan` を開き、右下の「PIN でログイン」で一度だけ編集者になる(localStorage に保持)。USB スキャナは HID(キーボード)型。区切り文字(Enter/Tab)と故障コード(既定 `FAULT`)は設定(歯車)で変更。`FORCERETURN` は Phase 3 まで無効。テスト用に `app_config.scan_timeout_ms` で FAULT 待ち時間(既定 15000)を変えられる
- **棚卸の記録**: 実施日/担当/メモは `app_config.last_inventory_*`、個体ごとの判定は `repair_history.event`(`hold_open` / `hold_close` / `unregistered_found` / `inventory_ok`)、保留判定はビュー `v_hold_latest`(端末ごと最新)。全行を選ばないと保存できない(判定漏れの防止)
- **FS 台数**: BOX 内の修理待ち台数は `app_config.fs_wait`(棚卸か FS パネルで入力)、発送中・要設定は `fs_lots` から自動計算。発送は RPC `fs_ship`(fs_wait 不足なら失敗)、BOX 台数の更新は RPC `fs_set_wait`(BOX+発送中+要設定 ≤ 総台数 を DB でも検証)、受領前の取消は `fs_unship`。ロットの受領・設定済み台数はトリガーで減らせない(訂正は SA が SQL Editor で)
- **テスト**: `py tests/run_all.py`(v2.2 分は静的 152 + e2e 97。cross-model review: GPT-5.6 Sol 9 round → PASS findings 0、`docs/xreview_v22_final.md`)。e2e は Supabase を route で差し替えるため実データに触れない

- DB: Supabase (tetigwcotdqgkwfswbyc) — RLS無効の内部運用ツール(anon key + アプリ側 PIN)
- 作者: sakrhiro (built with Aki)
