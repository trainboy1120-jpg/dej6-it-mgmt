# xreview report (2026-09-14 02:23)

**Final: PASS**

Spec: DEJ6 IT機器管理 v2.2(案A″ qr-app 吸収)。単一ファイル index.html(Bootstrap 5.3.3 CDN・Supabase REST 直叩き・GitHub Pages 配信)への追加実装。正典: dej6-itpoc-restart/plan_absorb_2026-09-12.md §5。
【満たすべきこと】
1. Firebase(qr-app) を index.html から一切参照しない。sync.yml は schedule なし(workflow_dispatch のみ)。旧同期分は migration で fault_source='legacy'。
2. スキャン受付 ?mode=scan: USB HID スキャナの keydown をバッファし区切り(Enter/Tab, app_config.scan_delim)で1スキャン。状態機械: 待機→3桁(SSP-ddd)で status 正常→FAULT 待ち(15秒, app_config.scan_timeout_ms 上書き可)→FAULT(app_config.scan_fault)で 修理待ち(fault_source='scan', fault_count+1, repair_history event='scan_fault')／返却済み→即 正常(event='scan_return')／その他 status→対象外・変更なし／FAULT 単独→順序違い／FORCERETURN→Phase3 まで無効／未知→無効。非編集者は書き込み不可(PIN ログイン案内)。表示は textContent(XSS 不可)。
3. 棚卸モーダル: 対象=status 修理待ち かつ device_type!=FS。各行 BOXにある/無い→保留/稼働中→正常 の3択、全行選択しないと保存不可(failsafe)。未登録追加はマスタ存在+status 正常のみ受理、保存で 正常→修理待ち(fault_source='manual')+event unregistered_found。保留は repair_history event hold_open/hold_close(status は変えない、最新 event で判定)。実施記録は app_config last_inventory_date/by/note(repair_history.device_id は NOT NULL FK のため inventory 行は作らない)。FS 数量モードでは BOX 内 FS 台数を app_config.fs_wait に保存。
4. FS 数量管理(fs_qty_mode=1): 一覧・タスクから FS 個体を隠し、5区分(稼働/修理待ちBOX/発送中/返却済み要設定/総台数)で 稼働=総-BOX-Σ(qty-received)-Σ(received-ready)。発送は RPC fs_ship(fs_wait 不足で例外)、受領前取消 fs_unship、ロット行は fs_lots PATCH(0≤ready≤received≤qty をクライアントと DB CHECK の両方で検証)。
5. 設定: stagnation_days/stagnation_days_shipped/repair_days(日付リスト, * で棚卸)/repair_roster/fs_qty_mode/fs_total/scan_delim/scan_fault を app_config に upsert。旧 alert_threshold は撤去。
6. 故障回数: statusPatch が 修理待ち で fault_count+1、正常復帰でクリアしない。scripts/import_qrapp.py が snapshot の qr_fault_counts(44台/64回)を dry-run 既定で PATCH。
7. 既存 v2.1 の保全: LEGACY マップ・PIN_SALT/PIN_HASH のみ・ディープリンク ?guide・GUIDE の1行1操作規則・modal fade=8。
8. テスト: tests/test_v22.py(静的 152)・tests/test_v22_e2e.py(Playwright 97, Supabase は route で差し替え。障害系: fs_lots 404→接続エラー、repair_history POST 失敗→途中保存の明示、一括修理待ちの端末別 fault_count を含む)が `py tests/run_all.py` で全 PASS(既存 172+89 含む)。
【受容設計(レビュー対象外・変更しない)】
- anon key の HTML 埋め込み、RLS 無効、PIN(SHA-256 salt)+localStorage 編集者フラグは既存 v2 の設計。今回変更しない(内部運用ツール、Pages 公開の前提)。
- CDN(Bootstrap/Icons) 依存、単一 HTML ファイル構成、`onclick=` の静的ハンドラは既存流儀。動的値を含む onclick を新規に作らないことだけ要求。
- 楽観ロック・多重書込の直列化・オフライン再送・サウンドは best-effort/対象外。書込途中で失敗したら toast で再読み込みを促す(部分保存の可能性を明示)で受容。
- 備品配布(eq_*)モジュール・貸出/12H超過(FORCERETURN)は対象外(Phase 3)。digest.py/digest.yml・sync.py 本体は触らない。
- repair_history の FK は外さない。inventory 実施記録は app_config で表現する(設計判断・変更しない)。
- 人名・PIN 値・Webhook URL をコード/テストに書かない。
- テストは file:// で Playwright、Supabase は route で差し替え、実データに触れない(前提)。
【レビュー観点】ロジックの穴(状態機械・数量計算・failsafe の抜け)、サイレント失敗(判定不能で成功表示)、XSS/インジェクション、既存機能の破壊、SQL の再実行安全性・トランザクション整合、テストが仕様を実際に検証しているか(空振りテスト)。
【round1 対応済み(再確認のみ)】FS 個体行トグルは削除(数量モードでは無条件非表示)／loadAll は app_config・fs_lots・保留履歴の失敗を全体エラーにする(空データで接続済みにしない)／一括 修理待ち は端末ごとに PATCH／単体・一括・棚卸・スキャン受付の先行書込後の失敗は partialMsg で「途中まで保存された可能性があります。再読み込みして確認してください」を明示し loadAll を呼ぶ。
【round2 対応済み(再確認のみ)】HTML に埋め込む typeName は全て esc()(device_type に HTML を入れた e2e で未実行を確認)／スキャン受付は 修理待ち(保留中含む) へ一切書き込まない(対象外・橙表示。保留解除は棚卸のみ)／棚卸の未登録追加は書込前に全件再検証し、不一致なら何も書かずに ID を明示して中止、成功件数は実 PATCH 数。
【round3 対応済み(再確認のみ)】棚卸の未登録追加は書込前に Supabase から該当 ID を再取得して検証(e2e はサーバー応答側を変えて検証)／保留判定は migration のビュー v_hold_latest(DISTINCT ON device_id・最新行)を読み、limit 上限を廃止／migration に DELETE alert_threshold を追加。
【収束条件】残る指摘が minor/nit のみなら PASS としてよい。受容設計に含まれる項目(楽観ロック・直列化・RLS・anon key・単一ファイル・CDN・FK 維持・inventory 行不作成)は指摘に挙げないこと。
【round4 対応済み(再確認のみ)】FS 数量の不変条件 BOX+発送中+要設定 ≤ 総台数 を fsSetWait/finishInventory/saveConfig の書込前(fsWaitError)と DB 側 RPC fs_set_wait の両方で検証／fs_unship は received_qty>0 または received_at あり を拒否／fs_lots は BEFORE UPDATE トリガーで受領・設定済みの減少と qty 変更を禁止(クライアントも同じ検証)、受領済みロットに取消ボタンを出さない。
【受容(追加)】誤入力の訂正は SA が SQL Editor で行う運用(専用 UI は作らない)。fs_total 変更の DB 側検証はクライアント検証のみで受容(app_config は key/value で複数キーの一括 upsert)。
【round5 対応済み(再確認のみ)】一括SIM 混在警告の typeName を esc(間接呼び出し map(typeName) を静的テストで禁止、e2e で buildBulkForm 直呼びの XSS 未実行を確認)／scan_fault は保存前に scanFaultError で検証(英数字・_・- の3〜20文字、FORCERETURN 予約語、端末QR形式 ^(SSP-)?\d{3}$ を拒否)、既存設定が不正なら既定 FAULT にフォールバックしてメタに警告(e2e あり)。
【注記】device_type は v2 マスタ(supabase_setup.sql)の固定列挙で運用し、UI から編集できない。HTML 埋め込みのエスケープは全経路で済み。既存 v2.1 由来のコード(修理手順ガイド・Manifest・Slack 文面)は本レビューの対象外(v2.1 で xreview PASS 済)。
【round6 対応済み(再確認のみ)】taskGroups は FS 除外を保留判定より先に実行(保留中 FS も数量モードでは出ない)。整合のため updateSummary も数量モードでは FS 個体を数えない(FS パネルが正本)。e2e フィクスチャに hold_open の FS-001 を追加し、数量モード ON でタスク・サマリーに出ない／OFF で出ることを検証。
【round7 PASS 後の軽微修正(確認のみ)】棚卸の catch は wrote フラグで部分保存を判定(書込前の失敗では「途中まで保存」と言わない)。これは最終確認 round。
【round8 対応済み(確認のみ)】fault_count は 修理待ち以外→修理待ち の実遷移だけ +1(statusPatch)。一括操作は同一状態の端末を対象外にし、保存直前にも拒否。e2e 追加。

## Round 1: reviewer=openai.gpt-5.6-sol verdict=PASS
仕様およびround1〜8の対応内容を対象ファイル上で再確認しました。blocker/majorに相当する未解決の問題は確認できず、収束条件を満たしています。

### verify command rc=0
```
[test_repair_guide.py] rc=0 passes=172  | ALL PASS | summary: PASS (checks run: see above) 
[test_repair_guide_e2e.py] rc=0 passes=89  | summary: PASS (0 fail) 
[test_v22.py] rc=0 passes=152  | ALL PASS | summary: PASS 
[test_v22_e2e.py] rc=0 passes=97  | summary: PASS (0 fail)
```
