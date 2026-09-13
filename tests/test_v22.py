"""v2.2(案A″ qr-app 吸収)— 静的テスト。index.html / migration_v2_2.sql / scripts/import_qrapp.py / sync.yml をテキスト解析。
使い方: py tests/test_v22.py   終了コード 0=全PASS / 1=FAIL"""
import re, sys, glob, pathlib, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = pathlib.Path(__file__).resolve().parents[1]
src = (ROOT / 'index.html').read_text(encoding='utf-8')
sql = (ROOT / 'migration_v2_2.sql').read_text(encoding='utf-8')
yml = (ROOT / '.github/workflows/sync.yml').read_text(encoding='utf-8')
imp = (ROOT / 'scripts/import_qrapp.py').read_text(encoding='utf-8')
fails = []
def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  -- {detail}' if detail and not cond else ''))
    if not cond: fails.append(name)
def defs(name): return len(re.findall(r'(?:^|\n)(?:const|let|(?:async\s+)?function|window\.)\s*%s\b\s*(?:=|\()' % re.escape(name), src)) + len(re.findall(r'id="%s"' % re.escape(name), src))

# ① Firebase 依存の停止(index.html は Firebase を参照しない)
check('① FB_URL 定義なし', 'FB_URL' not in src)
check('① firebasedatabase 文字列なし', 'firebasedatabase' not in src)
check('① fbItems / fbBadge 撤去', 'fbItems' not in src and 'fbBadge' not in src)
check('① SCAN_MODE 定数(?mode=scan)', "const SCAN_MODE = new URL(location.href).searchParams.get('mode') === 'scan'" in src)
check('① SCAN_TIMEOUT_DEFAULT_MS = 15000', 'const SCAN_TIMEOUT_DEFAULT_MS = 15000' in src)
gd_start = src.index('const GUIDE_DATA = {'); gd = src[gd_start: src.index('\n}\n', gd_start) + 3]
check('① GUIDE_DATA に qr-app の語なし', 'qr-app' not in gd)
check('① UI ラベルに qr-app なし(旧ツール表記)', 'title="故障回数(旧ツールの実績を含む)"' in src and 'legacy:\'旧ツール\'' in src.replace(' ', ''))

# ② DOM: モーダル数 8、棚卸・スキャン・設定・FS の id が揃う(各1回)
check('② modal fade = 8', src.count('class="modal fade"') == 8, src.count('class="modal fade"'))
IDS = ['mainWrap', 'fsPanel', 'holdNote', 'invBtn', 'scanBtn', 'inventoryModal', 'invHeadInfo', 'invCount', 'invBody', 'invAddId', 'invAddList', 'invAdded',
       'invFsWait', 'invFsShipping', 'invFsTotal', 'invFsActive', 'invNote', 'invFooter', 'invSaveBtn',
       'scanPanel', 'scanMeta', 'scanStage', 'scanTitle', 'scanSub', 'scanCountdown', 'scanRecent', 'scanLoginBtn',
       'cfgStagDays', 'cfgStagShipped', 'cfgRepairDays', 'cfgRoster', 'cfgFsMode', 'cfgFsTotal', 'cfgScanDelim', 'cfgScanFault']
for i in IDS: check(f'② id="{i}" ちょうど1回', src.count(f'id="{i}"') == 1, src.count(f'id="{i}"'))
check('② 旧 cfgThreshold / alert_threshold 撤去', 'cfgThreshold' not in src and 'alert_threshold' not in src)
for k in ['stagnation_days_shipped', 'repair_days', 'repair_roster', 'fs_qty_mode', 'fs_total', 'scan_delim', 'scan_fault']:
    check(f'② saveConfig が app_config.{k} を書く', f"key:'{k}'" in src.replace(' ', '').replace("key:'", "key:'"), '')

# ③ 関数定義ちょうど1回 / onclick に動的値なし(棚卸・FS・スキャン描画コード)
FN = ['renderFsPanel', 'fsLotState', 'partialMsg', 'fsWaitError', 'fsSetWait', 'fsShip', 'openInventory', 'invRenderRows', 'invRenderFooter', 'invRenderAdded', 'invAddUnregistered',
      'finishInventory', 'scanInit', 'scanRenderMeta', 'scanShow', 'scanIdle', 'scanLog', 'scanKey', 'scanHandle', 'computeHolds', 'fsTotals', 'holdBadge', 'faultBadge', 'stagLimit',
      'sbPatchTable', 'sbRpc', 'cfgUpsert', 'histRow']
for f in FN: check(f'③ {f} 定義1回', defs(f) == 1, defs(f))
v22 = src[src.index('// ─── v2.2 FS 数量管理パネル'):src.index('// ─── 起動')]
check('③ v2.2 描画コードに onclick="...${...}" なし(委譲 data-* を使う)', not re.search(r'onclick="[^"]*\$\{', v22))
check('③ 棚卸行は data-inv-id 委譲', "closest('[data-inv-id]')" in v22 and 'data-inv-id="${esc(id)}"' in v22)
check('③ ロット行は data-lot-act 委譲', "closest('[data-lot-act]')" in v22)
check('③ スキャン表示は textContent(innerHTML に生の読み取り文字列を入れない)', "document.getElementById('scanTitle').textContent = title" in v22 and 'scanTitle\').innerHTML' not in v22)
check('③ 起動: SCAN_MODE なら scanInit()', '\nif (SCAN_MODE) scanInit()\napplyEditorUI()\n' in src)

# ④ ロジックの不変条件
check('④ statusPatch: 修理待ちへの実際の遷移だけ fault_count+1', "if (d.status !== '修理待ち') upd.fault_count = (parseInt(d.fault_count) || 0) + 1" in src)
check('④(r8) 一括操作は同一状態の端末を対象外+保存直前にも拒否', ".filter(d => d.status !== target)" in src and "if (bulkDevices.some(d => d.status === bulkTarget))" in src)
check('④ statusPatch: fault_source は fields.source || manual', "upd.fault_source = fields.source || 'manual'" in src)
check('④ 正常復帰で fault_count をクリアしない', not re.search(r"fault_count\s*:\s*(0|null)", src))
check('④ スキャン受付の故障登録は source: scan', "source: 'scan'" in v22)
check('④ 棚卸の未登録追加は source: manual + event unregistered_found', "source: 'manual'" in v22 and "event: 'unregistered_found'" in v22)
for ev in ['hold_open', 'hold_close', 'inventory_ok', 'scan_fault', 'scan_return']: check(f'④ event {ev} を記録', f"'{ev}'" in v22)
check('④ 棚卸の実施記録は app_config(last_inventory_*)', 'last_inventory_date: todayISO()' in v22 and 'last_inventory_by' in v22)
check('④ 棚卸は未選択があると保存不可(failsafe)', 'b.disabled = unsel > 0' in v22 and "if (unsel.length) { toast(" in v22)
check('④ 棚卸の未登録追加はマスタに無い ID を拒否', 'はマスタに無い機器IDです' in v22)
check('④ loadAll は fs_lots と v_hold_latest(端末ごと最新の hold)を読む', 'fs_lots?select=*' in src and "sbGet('v_hold_latest?select=device_id,event,created_at')" in src and 'limit=1000' not in src)
check('④ 書込 API は編集者チェックあり(finishInventory/fsShip/fsSetWait/scan)', v22.count("if (!isEditor())") >= 7, v22.count("if (!isEditor())"))
check('④ FORCERETURN は Phase 3 まで無効', "FORCERETURN は Phase 3 まで無効" in v22)
check('④ 端末QR は 3桁(SSP- 省略可)', r"code.match(/^(?:SSP-)?(\d{3})$/)" in v22)
check('④ 区切り文字は Enter/Tab のみ', "appCfg['scan_delim'] === 'Tab' ? 'Tab' : 'Enter'" in v22)
check('④(r1) FS 数量モードでは個体行を無条件に除外(トグル無し)', "if (fsMode() && d.device_type === 'FS') return false" in src and 'fsRowsVisible' not in src and 'toggleFsRows' not in src)
check('④(r1) loadAll は app_config/fs_lots/repair_history の失敗を握り潰さない', ".catch(()=>[])" not in src[src.index('async function loadAll'):src.index('function cfgNum')])
check('④(r1) 一括 修理待ち は端末ごとに PATCH(fault_count 個別)', "if (bulkTarget === '修理待ち') {" in src and "for (const d of bulkDevices) { await sbPatch(`device_id=eq.${encodeURIComponent(d.device_id)}`, statusPatch(d, bulkTarget, fields)); wrote = true }" in src)
check('④(r1) 部分保存の明示 partialMsg を 単体/一括/棚卸/スキャン×2 で使用', src.count('partialMsg(') == 6, src.count('partialMsg('))
check('④(r7) 棚卸の catch は wrote フラグで部分保存を判定(常に true にしない)', "partialMsg('棚卸保存エラー', e, wrote)" in v22 and "partialMsg('棚卸保存エラー', e, true)" not in v22)
check('④(r2) HTML へ埋め込む typeName は全て esc()(タグを含む行に未エスケープ無し)', not [l for l in src.split('\n') if re.search(r"[^(]\$\{typeName\(", l) and '<' in l])
check('④(r5) typeName の間接呼び出し(map(typeName) 等)が無い', not re.search(r"map\(\s*typeName\s*\)|typeName\)\.join", src))
check('④(r5) scan_fault は保存前に検証(予約語・端末QR形式・文字種)', 'function scanFaultError(' in src and "if (c === 'FORCERETURN') return" in src and "/^(?:SSP-)?\\d{3}$/.test(c)" in src and "toast('故障コード: ' + err, 'danger'); return" in src)
check('④(r5) 不正な scan_fault 設定は既定 FAULT にフォールバックしメタに警告', "return scanFaultError(v) ? 'FAULT' : v" in src and '設定値が不正なため既定 FAULT を使用' in src)
check('④(r2) スキャン受付は 修理待ち(保留含む) に書き込まない', "hold_close', note: 'スキャン受付" not in src and "対象外: 保留中の端末です" in v22)
check('④(r2) 棚卸: 未登録追加は書込前に全件再検証・不一致は中止', "const badAdded = invState.added.filter((id, k) => !addedDevs[k])" in v22 and "何も保存していません" in v22 and "addedDone" in v22)
check('④ 保留は内訳外(taskGroups)・FS は数量モードでタスク除外', "if (s === '修理待ち' && holdSet.has(d.device_id)) { g.hold.push(d); continue }" in src and "if (fsMode() && t === 'FS') continue" in src)
check('④(r6) updateSummary は数量モードで FS 個体を数えない', "const base = fsMode() ? allDevices.filter(d => d.device_type !== 'FS') : allDevices" in src)
check('④(r6) taskGroups は FS 除外を保留判定より先に行う', src.index("if (fsMode() && t === 'FS') continue") < src.index("if (s === '修理待ち' && holdSet.has(d.device_id)) { g.hold.push(d); continue }"))

# ⑤ 1行1操作規則(GUIDE_DATA の actions は既存 test_repair_guide で検査。ここでは SSP 新文言が規則を満たすことだけ)
sys.path.insert(0, str(ROOT / 'docs/mockup'))
RULE = re.compile(r"して|し、|し「|、|て(?!$)")
def violates(line): return bool(RULE.search(re.sub(r"\([^)]*\)|（[^）]*）", "", line)))
new_actions = ['チェックシートに ✓ を書く', 'スキャン受付の PC で端末の QR を読む', 'FAULT の QR を読む(15秒以内)', '画面が緑になるのを確認する', '修理依頼品 BOX へ入れる']
check('⑤ SSP 新 actions が 1行1操作', not any(violates(a) for a in new_actions) and all(a in gd for a in new_actions))

# ⑥ migration_v2_2.sql
for s in ['ALTER TABLE devices ADD COLUMN IF NOT EXISTS fault_count integer NOT NULL DEFAULT 0', 'ALTER TABLE repair_history ADD COLUMN IF NOT EXISTS event text',
          'CREATE TABLE IF NOT EXISTS fs_lots', 'CHECK (0 <= ready_qty AND ready_qty <= received_qty AND received_qty <= qty)', 'CREATE OR REPLACE FUNCTION fs_ship(', 'CREATE OR REPLACE FUNCTION fs_unship(',
          "UPDATE devices SET fault_source = 'legacy' WHERE fault_source = 'qr-app'", "('scan_delim',              'Enter')", "('fs_qty_mode',             '1')", 'ON CONFLICT (key) DO NOTHING']:
    check(f'⑥ SQL: {s[:50]}', s in sql)
check('⑥ SQL: fs_ship は fs_wait 不足で例外(負の在庫を作らない)', "IF v_wait < p_qty THEN RAISE EXCEPTION" in sql)
check('⑥ SQL: fs_unship は受領後(received_qty>0 または received_at あり)を拒否', "IF v_rec > 0 OR v_recat IS NOT NULL THEN RAISE EXCEPTION" in sql)
check('⑥(r4) SQL: fs_set_wait が BOX+発送中+要設定 ≤ 総台数 を検証', 'CREATE OR REPLACE FUNCTION fs_set_wait(' in sql and 'IF p_wait + v_open > COALESCE(v_total, 0) THEN RAISE EXCEPTION' in sql)
check('⑥(r4) SQL: fs_lots の受領/設定済みは減らせないトリガー', 'CREATE TRIGGER trg_fs_lots_no_decrease BEFORE UPDATE ON fs_lots' in sql and 'NEW.received_qty < OLD.received_qty OR NEW.ready_qty < OLD.ready_qty' in sql)
check('④(r4) fs_wait の保存は fsSetWait/finishInventory とも RPC fs_set_wait 経由(直接 upsert しない)', v22.count("sbRpc('fs_set_wait'") == 2 and 'fs_wait:' not in v22)
check('④(r4) fsWaitError を fsSetWait/finishInventory/saveConfig で使用', src.count('fsWaitError(') == 4, src.count('fsWaitError('))
check('④(r4) ロット PATCH は受領/設定済みの減少を拒否', "if (rec < (+lot.received_qty||0) || rdy < (+lot.ready_qty||0))" in v22)
check('⑥ SQL: repair_history の FK を外さない', 'DROP CONSTRAINT' not in sql)
check('⑥(r3) SQL: v_hold_latest は DISTINCT ON (device_id) の最新行', 'CREATE OR REPLACE VIEW v_hold_latest' in sql and 'DISTINCT ON (device_id)' in sql and 'ORDER BY device_id, created_at DESC' in sql)
check('⑥(r3) SQL: 旧 alert_threshold を削除', "DELETE FROM app_config WHERE key = 'alert_threshold';" in sql)
check('④(r3) 棚卸: 未登録追加は書込前に Supabase から再取得して検証', "const fresh = await sbGet('devices?select=*&device_id=in.(" in v22 and 'サーバー再確認' in v22)
check('⑥ SQL: 秘匿情報なし', not re.search(r'eyJ[A-Za-z0-9_-]{20,}|hooks\.slack\.com', sql))

# ⑦ sync.yml: cron なし・手動のみ / sync.py は legacy を触らない
check('⑦ sync.yml に schedule/cron なし', 'schedule:' not in yml and '- cron:' not in yml)
check('⑦ sync.yml は workflow_dispatch のみ', 'workflow_dispatch:' in yml and 'Heartbeat' not in yml)
check('⑦ sync.py は fault_source=qr-app のみ対象(legacy を触らない)', "'legacy'" not in (ROOT / 'scripts/sync.py').read_text(encoding='utf-8') and "qr-app" in (ROOT / 'scripts/sync.py').read_text(encoding='utf-8'))

# ⑧ import_qrapp.py: dry-run 既定・snapshot 解析が Firebase 実測(44台/64回)と一致
check('⑧ import_qrapp: --apply 無しは書かない', 'if not a.apply:' in imp and '"--apply", action="store_true"' in imp)
check('⑧ import_qrapp: Firebase に触らない', 'firebasedatabase' not in imp and 'FB_URL' not in imp)
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    import import_qrapp as I
    snaps = sorted(glob.glob(str(ROOT.parent / 'dej6-itpoc-restart' / 'qrapp-capture' / 'snapshot_*.json')))
    w = I.load_snapshot(snaps[-1]) if snaps else {}
    check('⑧ snapshot 解析 = 44台 / 64回', len(w) == 44 and sum(w.values()) == 64, f'{len(w)}/{sum(w.values())}')
    check('⑧ 3回 = SSP-027/036/079', sorted(k for k, v in w.items() if v == 3) == ['SSP-027', 'SSP-036', 'SSP-079'])
    check('⑧ 全 ID が SSP-ddd', all(re.fullmatch(r'SSP-\d{3}', k) for k in w))
except Exception as e:
    check('⑧ import_qrapp 読込', False, str(e))

# ⑨ 保全(v2.1 テストと重複するが v2.2 でも壊していないこと)
check('⑨ PIN は PIN_SALT/PIN_HASH のみ', len(re.findall(r"const PIN_HASH = '[0-9a-f]{64}'", src)) == 1 and not re.search(r"['\"]dej6-[a-z0-9]{8}['\"]", src))
check('⑨ LEGACY 維持', "const LEGACY = { '修理中':'修理待ち', 'Zebra登録済み':'RMA登録済み', '修理完了':'返却済み' }" in src)
check('⑨ ディープリンク維持', "loadAll().finally(() => { const q = new URL(location.href).searchParams; if (q.has('guide'))" in src)
check('⑨ 人名がコードに無い(ローテは app_config)', not re.search(r'Senmyo|Sato-san|Sakasai', src, re.I))

print('\nALL PASS' if not fails else f'\n{len(fails)} FAIL: {fails}')
print('summary:', 'FAIL ' + str(len(fails)) if fails else 'PASS')
sys.exit(1 if fails else 0)
