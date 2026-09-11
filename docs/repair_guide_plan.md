# 修理手順ガイド(Repair Guide) 追加プラン — DEJ6 IT機器管理 v2.1

作成: 2026-09-12 / 対象: `index.html`(単一ファイルアプリ) / 状態: **プラン確定(cross-model review r14 PASS)・実装は本人GO待ち** / レビュー履歴: r1 8 → r2 4 → r3 6 → r4 4 → r5 2 → r6 2(編集未反映の再指摘) → r7 3 → r8 1 → r9 1(編集未反映) → r10 1 → r11 1 → r12 2 → r13 2 → **r14 PASS**(reviewer=GPT-5.6 Sol, fixer=none, レポート `docs/xreview_plan_2026-09-12_r{1..14}.md`)

## 1. 目的
「この機器が壊れた。次に何をすればいい?」を、**初めて触るSA・AAでも1人で完結**できるように、
機種ごとの修理手順(修理に出す前の一次対処 → 修理フローの各ステップ → 復帰設定)と必要リンクを
アプリの中に1か所で見せる。今の「使い方」モーダルはツールの操作説明で、**機器そのものの直し方**が無い。

## 2. 利用シーン(誰が・いつ)
| 誰 | いつ | 入口 |
|---|---|---|
| 修理箱を見たAA/SA(閲覧のみ) | 「これ壊れてる、どうする?」 | ナビの **[修理手順]** ボタン(ログイン不要) → 機種タブ |
| ステータスを進めるSA/IT POC | モーダルで次のステータスを押す前 | ステータス更新モーダルの **[この機種の手順]** リンク → 現ステータスの位置を**「いまここ」**でハイライト |
| 修理箱の前の人 | 印刷物/QRから | **ディープリンク** `?guide=SSP` を開くとガイドが直接開く。**[印刷]** で機種ごとのA4手順書(A〜Eを全部含むので2〜3枚・実測済み。修理箱の横にクリアファイルで置く想定。1枚に収める要約版は v1 対象外) |

## 3. 画面仕様(モック: `docs/mockup/mockup_desktop.png`, `mockup_mobile.png`)
新モーダル `guideModal`(modal-xl・scrollable)。構成は上から:
1. **機種タブ**(nav-pills・横スクロール): SSP(TC57) / FS(RS5100) / ZD611 / 無線機 / Avery / Handy / PC / 携帯
2. **概要カード**: 型番・SIM要否・RMA要否・送付先(マスタ設定の住所を表示)・修理フローのバッジ列(既存 `.status-badge` を再利用)・担当分担(修理待ち登録=気付いた人 / SIM以降=SA・IT POC)
3. **A. 修理に出す前に試す(5分)**: チェックリスト。直ったら「正常」へ戻す指示付き(無駄な発送を減らす)
4. **B. 修理フロー**: 1ステップ=1カード。**[ステータス] / やること(1行1操作) / ✅完了のサイン / ⚠先回りの注意 / 🔗リンク(ボタン)**。デバイスモーダルから開いた時は現在ステータスのカードに「いまここ」バッジ+枠色。説明だけの文(「〜は不要」「送付先は〜」)は actions に入れず cautions に置く
5. **C. 復帰チェック**: 「正常」に戻す前の動作確認リスト(機種別)
6. **D. リンク集**: SIMテンプレ / Zebraポータル / JP-OTS QuickLink Wiki / Slack #dej6-it-poc / SOP(機種で出し分け。URL未確認の資料は無効ボタン+「共有先URL確認中」)
7. **E. 発送の鉄則**(全機種共通・黄色帯): Manifest同梱 / 返送先確認 / 備考「スワップ禁止」 / 膨張バッテリー発送禁止
8. フッター: 出典(JP-OTS QuickLink Wiki 2026-07-25確認)・「手順の訂正は #dej6-it-poc へ」。ヘッダ右に [URLコピー] [印刷](モバイルはアイコンのみ)

## 4. 機種別の中身(v1で入れる内容。出典: JP-OTS Wiki 2026-07-25確認 / #dej6-it-poc 実績 / 点検SOP draft v3)
| 機種 | 一次対処(抜粋) | フロー | 送付先 |
|---|---|---|---|
| SSP TC57 | 再起動 / 充電端子清掃 / 別クレードル / Utility・Velocity起動確認 / スキャン窓清掃 | 修理待ち→SIM→RMA→発送→返却→正常 | Zebra社(Direct RMA) |
| FS RS5100 | 端子清掃 / バッテリー再装着 / 別クレードル / TC57と再ペアリング / 振ってビーム継続確認 | 修理待ち→RMA→発送→返却→正常(**SIM不要**) | Zebra社(Direct RMA) |
| ZD611 | ヘッド清掃 / キャリブレーション / **印字速度101・濃度5**(Ito-san設定、修理頻度が下がった実績) / ラベル・ギャップ確認 | 修理待ち→SIM→RMA→発送→返却→正常 | Zebra社(Direct RMA) |
| 無線機 | バッテリー入替で切り分け / 充電器・アンテナ緩み / チャンネル確認 | 修理待ち→SIM→発送→返却→正常(RMAなし) | TYO4青梅FC IT宛 |
| Avery | Wikiのトラブルシュート(チケット不要) | 修理待ち→SIM起票済み(ツール上の表示。実際はWiki手順で修理依頼済みの意味)→発送→返却→正常 | Wikiの指示(ガイドは `dest` で個別表示) |
| Handy / 携帯 / PC / その他 | 再起動・充電で切り分け | 修理待ち→SIM→発送→返却→正常 | 「SIM で指示された宛先(既定は TYO4)」を `dest` で表示。TYO4 住所は既定値として併記、発送ステップに「SIM の宛先を優先」の注意 |
復帰(正常へ戻す)は全機種共通: ナンバリング(テプラ・SSPはバッテリー内側にも) → 設定/動作確認 → SSPはqr-appの故障登録を解除 → 「正常」。

## 5. 実装方針(index.html への差分)
- **データ**: `const GUIDE_DATA = { SSP:{...}, FS:{...}, ... }`(JS定数)。1機種= `{model, who, dest?, sim_label?, sim_link_label?, first_aid[], step_extra{status:{replace?, title?, actions[], done?, cautions[], fallback?{title, actions[]}}}, return_check[], links[{label,url|null,note?}]}`。共通ステップ本文は `GUIDE_STEP_BASE[status]`、機種固有は `step_extra` で上書き。**`actions` を持つ step_extra は必ず `replace:true`(共通 actions/cautions を丸ごと置換。追記モードは無い。実作業順を機種ごとに書き切る)**。`cautions` だけの step_extra は共通 cautions に追記。`title`/`done` は個別上書き。`dest` を持つ機種は Zebra/TYO4 の二分の文言を上書き(Avery=Wiki の指示・`hide_addr:true` で住所非表示 / Handy・PC・Mobile・Other=「SIM で指示された宛先(既定は TYO4)」・住所は TYO4 を既定値として表示)。 `fallback` は条件付きの代替手順(例: SSP「qr-app が使えない時」)で、`actions` と同じ1行1操作規則に従い、カード内の小見出し+番号リストで表示する。`sim_label`/`sim_link_label` は Avery のように SIM 要否の表示とリンク名を機種で差し替える時だけ使う。
  既存 `FLOWS` / `SIM_TEMPLATES` / `ZEBRA_TYPES` / `appCfg`(住所) を参照して**二重管理しない**(フロー順とSIMリンクはガイド側に書かない)。
- **UI**: `guideModal` 追加、ナビに `[修理手順]` ボタン、`openStatus` のヘッダに手順リンク、`guideRender(type, currentStatus)` / `guideOpen(type, currentStatus)`。
- **追加するトップレベル識別子(すべて `GUIDE_`/`guide` 接頭辞・全一覧)**: 定数 `GUIDE_DATA` `GUIDE_STEP_BASE` `GUIDE_ICONS` `GUIDE_URL_WIKI` `GUIDE_URL_ZEBRA` `GUIDE_URL_SLACK` `GUIDE_DEFAULT_FLOW` `guideState` ／ 関数 `guideSafeUrl` `guideDeepLink` `guideCopyUrl` `guidePrint` `guideLinksFor` `guideRender` `guideOpen` ／ DOM id `guideModal` `guideTabs` `guideBody` `guideCopyBtn` `guidePrintBtn` ／ CSS class `guide-*` `here-badge` `first-aid`。現行 index.html に同名は無いことを `docs/mockup/check_identifiers.py`(単語境界一致・旧名3つも対象・終了コード付き)で確認。実行結果(2026-09-12、origin/main と bytes 一致の index.html):

```
target: C:\Users\sakrhiro\Documents\aki_data\dej6-it-mgmt\index.html (74965 bytes, sha1 37968613df6e6ea5043092b7bc006ed32ace2341)
  GUIDE_DATA           0
  GUIDE_STEP_BASE      0
  GUIDE_ICONS          0
  GUIDE_URL_WIKI       0
  GUIDE_URL_ZEBRA      0
  GUIDE_URL_SLACK      0
  GUIDE_DEFAULT_FLOW   0
  guideState           0
  guideSafeUrl         0
  guideDeepLink        0
  guideCopyUrl         0
  guidePrint           0
  guideLinksFor        0
  guideRender          0
  guideOpen            0
  guideModal           0
  guideTabs            0
  guideBody            0
  guideCopyBtn         0
  guidePrintBtn        0
  REPAIR_GUIDES        0
  renderGuide          0
  openGuide            0
RESULT: OK (0 collisions)
```
(`wc -c index.html` = 74965 / `sha1sum index.html` = 37968613df6e6ea5043092b7bc006ed32ace2341 と一致することを別コマンドで照合済み)

- **既定フロー**: `FLOWS` に無い type(Other)は `GUIDE_DEFAULT_FLOW`(=`['修理待ち','SIM起票済み','発送済み','返却済み','正常']`)。実装時は `openStatus` 内の同じリテラル配列もこの定数に置き換え、既定フローの二重管理を無くす。
- **ディープリンク**: 起動時 `new URL(location).searchParams.get('guide')` を見る。パラメータが**無い**時は何も開かない(通常起動)。**有る**時は値をそのまま `guideOpen()` に渡し、`GUIDE_DATA` のキー以外(空文字・未知値・`<script>` 等)は `Other`(表示「その他」・汎用フロー)へ正規化して開く(`has('guide')` で判定。`|| 既定値` で空文字を握りつぶさない)。[URLをコピー]はその形式で生成。
- **印刷**: 既存 `printManifest` と同じ「別ウィンドウにHTMLを書いて `window.print()`」方式(本体CSSに @media print を増やさない)。A4縦・余白12mm・本文10pt、ステップカードは `break-inside: avoid` でページ跨ぎを防ぐ。Playwright `page.pdf(format='A4')` の実測(2026-09-12、モック): SSP 3枚 / ZD611 3枚 / 他7機種 2枚(1枚要約は対象外)。`.btn` は印刷では非表示。[URLコピー] は `?guide=<機種>` を `navigator.clipboard` に書き、toast で通知。
- **XSS**: HTML へ入る動的値はすべて既存 `esc()` を通す。動的値をインライン `onclick` の JS 文字列に埋め込まない(タブは `data-guide-type` 属性 + `addEventListener` 委譲、機種値は `GUIDE_DATA` のキーでホワイトリスト検証)。アイコンは `GUIDE_ICONS` 対応表から選ぶ。URL は `guideSafeUrl()` で `https://` 以外を `#` に落とす。住所(appCfg)は利用者入力なので必ず `esc`。印刷ウィンドウも同じ描画結果(esc 済み HTML)を流し込む。
- 変更しないもの: Supabase スキーマ、qr-app、sync.py/digest.py、LEGACY、PIN周り、既存モーダルの挙動。

## 6. 受容設計(レビュー時の指摘対象外として明記)
- ガイド本文は**コード内定数**で管理(編集=commit)。DB化・画面編集UIは v1 対象外(内容の正は Wiki、ツールは要約+導線)。
- 機種の判定は既存 `device_type` の8値+`Other`。未知の type は `Other`(表示「その他」・`TYPE_LABEL` に追加)に正規化し、汎用フロー(修理待ち→SIM→発送→返却→正常、`openStatus` と同じ既定)と汎用手順を表示。`Other` はタブにも出す(8機種の後ろ)。
- 写真・動画の埋め込みは v1 対象外(点検SOP pptx へのリンクで補う。ホスト先URLは本人確認待ち)。
- 未検証の Wiki 下位ページURLは載せない(QuickLinkトップのみ)。Midway更新後に個別URLを確認して追記する。

## 7. 検証計画(実装時)
- 静的テスト(`py tests/test_repair_guide.py`、index.html をテキスト解析):
  ⓪ 1行1操作の機械チェック = `docs/mockup/check_one_action.py`(実装時は tests/ へ移す): `GUIDE_STEP_BASE[*].actions`・`step_extra[*].actions`・`step_extra[*].fallback.actions` の各行について、括弧内を除いた本文が正規表現 `して|し、|し「|、|て(?!$)` に一致しない(末尾以外の「て」で「貼り付けて起票する」型の連結を検出)。スクリプトは起動時に自己テストを行う: must-fail 6件(貼り付けて起票する / まとめて選択する / 貼り付けて投稿する / 選び、症状を入力する / タップし「返却済み」を押す / 確認して送信する)が全件違反、must-pass 7件(貼り付ける / 起票する / 台数を Manifest / RMA と照合する / 機器ID・シリアル・症状を入力する / 括弧付き補足2件 / 箱を開ける)が全件通過、でなければ rc=2。現データでの実行結果(2026-09-12): `self-test OK (6 must-fail / 7 must-pass); checked 94 action lines; violations: 0`。加えて SSP・ZD611・PC の修理待ち/SIM ステップは期待 actions 配列との完全一致で回帰検証。`first_aid` と `cautions` は「症状→対処」の説明文なので対象外
  ① `GUIDE_DATA` の全 type について、`step_extra` のキーが解決済みフロー `FLOWS[type] || GUIDE_DEFAULT_FLOW`(描画と同じ解決)に含まれる(存在しないステータス名を使っていない)。`actions` を持つ step_extra は `replace:true` である(追記モード禁止)
  ② `done` / `title` / `actions` に登場するステータス名は `FLOWS` の正式6値のみ(「返却済み・要設定」等の表示名は括弧内の補足としてのみ許可)
  ③ 全 type で `first_aid` ≥3 件・`return_check` ≥1 件。`GUIDE_STEP_BASE` と `step_extra` を**マージした後**の各フローステップで actions ≥1 件(cautions だけの step_extra は許容)。ZD611 の「修理待ち」と PC の「SIM起票済み」はマージ結果が期待配列と一致(重複・逆順の回帰テスト)
  ④ 定数 URL(`GUIDE_URL_WIKI`/`GUIDE_URL_ZEBRA`/`GUIDE_URL_SLACK`/`SIM_TEMPLATES`/`links[].url`)は `https://` で始まる。`links[].url` が null の項目は `note` を持つ。描画された全 `href` は `https://` か `#` のみ
  ⑤ 識別子の不変条件(旧名 `openGuide`/`renderGuide`/`REPAIR_GUIDES` は0件): 既存の `statusModal`/`openStatus`/`printManifest`/`LEGACY`/`FLOWS`/`SIM_TEMPLATES`/`simGuide` が1回ずつ定義されたまま、§5 に列挙した**新規識別子の全件**(定数7・関数7・DOM id 5)が単語境界一致で**ちょうど1回**定義される。実装前の index.html では同じ全件が**0回**であることも同じテストで確認する(トップレベル `const` の総数は数えない)
  ⑧ 見出しの不変条件: ガイド本文に `A. 修理に出す前に試す` `B. 修理フロー` `C. 復帰チェック` `D. リンク集` `E. 発送の鉄則` がこの順で各1回
  ⑥ ガイド描画コード内に、動的値を埋め込んだインライン `onclick="...${...}"` が無い(正規表現で検出)。タブは `data-guide-type` + 委譲、アイコンは `GUIDE_ICONS` 対応表、URL は `guideSafeUrl()`(https 以外は `#`)
  ⑦ `links[].url` に `javascript:` を与えた場合 `guideSafeUrl` により `href="#"` になる。定数 `GUIDE_URL_WIKI/ZEBRA/SLACK` と `SIM_TEMPLATES[type]` を不正スキームに差し替えた場合も、描画後の対応する `href` が `#` になる(リンク集の全 `href` は `guideSafeUrl` 経由)
- 動的テスト(Playwright headless、Supabase/Firebase への fetch は route で差し替え・実データに触れない):
  ① ナビ [修理手順] → `#guideModal.show`、タブ9個(8機種+その他)、各タブクリックでカード数 = `FLOWS[type].length`(Other は汎用フロー5)
  ② `?guide=ZD611` で直接開く / `?guide=<不正値>`・`?guide=`(空文字)・`?guide=%3Cscript%3E` は `Other`(表示「その他」)にフォールバックし、コンソールエラー0 / パラメータ無しではモーダルが開かない
  ③ デバイス行 → モーダル → 手順リンク → 現ステータスのカードだけに「いまここ」(1個)
  ④ [URLコピー] のクリップボード内容が `?guide=<機種>` 形式で、その URL を開くと同じ機種が表示される
  ⑤ [印刷] で開く新ウィンドウの `document.title` に機種名、本文に A〜E の5見出しがこの順で含まれ、ステップ数 = `FLOWS[type].length`、`.btn` が非表示。Playwright の `page.pdf(format='A4')` で出力し、ページ数が 1〜3 かつ各 `.guide-step` が `break-inside: avoid` を持つ(PDF の枚数上限は 3)
  ⑥ `appCfg` の住所に `<script>`・引用符・改行を含む値を注入しても、テキストとして表示されスクリプトは実行されない(`window.__xss` フラグ未設定)
  ⑦ `links[].url` に `javascript:` を与えた場合 `guideSafeUrl` により `href="#"` になる
  ⑨ Avery の「SIM起票済み」カードに共通注意「同じ機種はまとめて1件のSIM」が**表示されない**(replace:true で共通 cautions も置換)
  ⑧ コンソールエラー0 / モバイル幅390pxでタブ横スクロール・ヘッダボタンはアイコンのみ・折返し崩れなし
- cross-model review: `--fixer none --rounds 1`(UIかつ本番DB接続を持つファイルのため自動fixerは使わない) → 指摘は作者が手で修正 → PASSまで再実行。プラン段階の r1 は 8 major → 全件修正済み(`docs/xreview_plan_2026-09-12_r1.md`)

## 8. 本人確認事項(実装前に回答が欲しい)
1. 点検SOP(SSP/FS pptx)の共有先URL(SharePoint等)。無ければリンク無しで進める
2. 無線機のSIMテンプレ(Radio)で発送先がTYO4以外を指示される例はあるか
3. ZD611をZebraへ送る際の「Amazon code」(#dej6-it-poc 2026-02 の質問)の正体。不明なら記載しない
4. Midway再認証(`mwinit`)をしてもらえれば、Wikiの下位ページURL(TC57/RS5100/ZD611/無線機の個別手順)を確認して追記する

## 9. 工程
1. GO → `index.html.bak.<ts>` 作成(レシート) → 実装(約300行追加見込み) → 静的+動的テスト → cross-model review PASS → `_pm_state.md`/README 更新 → commit
2. push は本人承認後(github-mcp)。Pages反映後に実機スマホで確認
