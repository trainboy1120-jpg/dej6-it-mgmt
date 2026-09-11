# xreview report (2026-09-12 03:07)

**Final: FAIL**

**Stopped: manual fix mode (--fixer none): findings remain; fix them by hand and re-run for re-review** (human review needed)

Spec: 対象は DEJ6 IT機器管理アプリ index.html(単一ファイル・Bootstrap5・Supabase REST 直叩き・GitHub Pages 配信)への『機種別 修理手順ガイド v2.1』の実装。docs/impl_repair_guide.patch が今回の全差分(index.html.bak → index.html、追加のみ・既存機能の削除なし)、index.html は差分適用後の全文(文脈確認用)、tests/test_repair_guide.py が静的テスト(168 PASS: 1行1操作・step_extra とフローの整合・first_aid≥3・URL https・識別子の一意定義(新規22件が各1回、旧名0)・inline onclick に動的値なし・全 href が esc(guideSafeUrl())・モーダル数7・見出しA〜E順・LEGACY/PIN 保全)、tests/test_repair_guide_e2e.py が Playwright 動的テスト(62 PASS: Supabase/Firebase は route で差し替え。ナビ→9タブ→カード数=フロー長、ディープリンク ?guide= 空/不正/正常、デバイス→手順→「いまここ」1個、ガイド表示中は statusModal を隠し Esc で閉じると同機器で復帰、XSS 住所がテキスト表示、javascript: URL→#、URLコピー形式、印刷ウィンドウの title/見出し/ステップ数/.btn 非表示/A4≤3枚、モバイル390px)。設計プランは docs/repair_guide_plan.md(cross-model review r14 PASS 済)。レビュー観点: (1)差分が既存機能(ステータス更新・一括操作・Manifest・履歴・設定・SOP・sync との契約)を壊していないか (2)描画の XSS 境界(動的値は esc()、URL は guideSafeUrl、機種値はホワイトリスト) (3)多重モーダルの扱い(hide→hidden.bs.modal で開く→閉じたら statusModal を再表示)に競合・取りこぼしがないか (4)ディープリンクと起動順序(loadAll 前に開いても壊れない) (5)テストが仕様を実際に検証しているか(形だけの PASS がないか) (6)現場で誤解を生む表現。blocking = blocker または major。仕様どおりで指摘対象外: ガイド本文はコード内定数(DB化・編集UIは対象外)/写真・動画は対象外/未検証Wiki下位URLは載せない(QuickLinkトップのみ)/SB_KEY(anon key)と PIN_HASH がコード内にあるのは既存設計で GitHub Pages 公開前提(PIN 平文は無い)/静的文字列のみの onclick(guideOpen(typeFilter==='ALL'?'SSP':typeFilter)・guideCopyUrl()・guidePrint()・guideOpenFromStatus())は既存アプリの作法に合わせて許容/print は別ウィンドウ document.write 方式(既存 printManifest と同じ)/Avery は FLOWS 上「SIM起票済み」を通過するのがツールの制約で『ツール上の表示』と明示して受容/Other は FLOWS に無いため GUIDE_DEFAULT_FLOW を使う設計(openStatus の既定配列も同定数に置換済)/1行1操作の判定は check_one_action.py の規則を正とし通過した行の分割要求は対象外/first_aid と cautions は説明文で規則の対象外/テストは file:// で index.html を開くため Pages 固有の挙動(相対パス等)は対象外/e2e の clipboard 実書き込みは file:// では権限が取れないため guideDeepLink() の戻り値検証で代替(受容)/本文の事実は確認済みで真偽は対象外。

## Round 1: reviewer=openai.gpt-5.6-sol verdict=FAIL
ディープリンク起動時、非同期設定読込より先にガイドが描画され、登録済み送付先住所が反映されない重大な起動順序不具合があります。また、多重モーダル復帰テストは入力値保持を実際には検証しておらず、仕様上の重要な回帰を検出できません。
- [major] index.html:1519 ディープリンクでは appCfg の読込完了前にガイドを開くため、登録済み送付先住所が表示されない
  - evidence: 起動処理は 1517 行目で `loadAll()` を待たず、1519 行目で直ちに `if (q.has('guide')) guideOpen(...)` を実行します。一方、住所は 1434 行目で `appCfg` から取得され、未読込なら `(住所はマスタ設定で登録してください)` になります。loadAll 完了時の `refreshUI()` はガイドを再描画しないため、ディープリンク利用者には設定済み住所がそのまま反映されません。
  - fix: 初回の `loadAll()` 完了後にディープリンクを開くか、loadAll で appCfg 更新後、guideModal が表示中なら `guideRender(guideState.type, guideState.current)` を呼んで再描画してください。設定取得失敗時にもガイド自体を開けるよう、デバイス読込と適切に分離してください。
- [major] tests/test_repair_guide_e2e.py:107 statusModal の入力値保持テストが実質的に実行されていない
  - evidence: 107 行目は `await pg.fill('#mMemoInput', 'memo-keep') if ...disabled else None` ですが、テストは編集者状態を設定していないため入力欄は disabled で、fill は常にスキップされます。さらに 116 行目の復帰確認は `#mDeviceId` だけを検査し、コメントで主張する「同じ入力値のまま戻る」を確認していません。
  - fix: ページ遷移前に localStorage へ有効な編集者状態を設定して入力欄を有効化し、`mMemoInput` へ値を入力してください。ガイドを Esc で閉じて statusModal が復帰した後、`#mMemoInput` の value が `memo-keep` のままであることを必須アサーションに追加してください。
