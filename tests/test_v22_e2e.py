"""v2.2(案A″ qr-app 吸収)— 動的テスト。Playwright headless。Supabase への通信は page.route で差し替え、実データには触れない。
検査: 通常画面(FS 数量モード・保留・棚卸モーダルと書込本文) / スキャン受付 ?mode=scan(状態機械を keyboard で駆動)。
使い方: py tests/test_v22_e2e.py   終了コード 0=全PASS / 1=FAIL"""
import asyncio, json, sys, pathlib, urllib.parse
from playwright.async_api import async_playwright
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = (ROOT / 'index.html').as_uri()

def dev(id_, t, st, **kw):
    d = {'device_id': id_, 'device_type': t, 'status': st, 'model': 'M', 'serial_number': 'S', 'asset_number': 'A', 'memo': '', 'zebra_rma': '', 'ops_handler': 'x',
         'status_changed_at': '2026-09-01T00:00:00Z', 'fault_source': None, 'fault_count': 0}
    d.update(kw); return d
DEVICES = [
    dev('SSP-005', 'SSP', '正常', status_changed_at=None, fault_count=2),
    dev('SSP-006', 'SSP', '修理待ち', fault_source='legacy', fault_count=3),
    dev('SSP-007', 'SSP', '修理待ち', fault_source='manual', fault_count=1),       # 保留中(hold_open が最新)
    dev('SSP-012', 'SSP', '返却済み', fault_count=1),
    dev('SSP-020', 'SSP', '正常', status_changed_at=None),
    dev('FS-001', 'FS', '修理待ち'), dev('FS-002', 'FS', '正常', status_changed_at=None), dev('FS-003', 'FS', '発送済み'),
    dev('ZD-001', 'ZD611', '正常', status_changed_at=None),
    dev('XX-001', '<img src=x onerror="window.__xss2=1">', '正常', status_changed_at=None),   # r2: 保存型 XSS の検査用
]
CFG_BASE = [{'key': 'addr_zebra', 'value': 'Z'}, {'key': 'addr_tyo4', 'value': 'T'}, {'key': 'addr_return', 'value': 'R'},
            {'key': 'fs_qty_mode', 'value': '1'}, {'key': 'fs_total', 'value': '190'}, {'key': 'fs_wait', 'value': '3'},
            {'key': 'scan_delim', 'value': 'Enter'}, {'key': 'scan_fault', 'value': 'FAULT'}, {'key': 'scan_timeout_ms', 'value': '600'},
            {'key': 'repair_days', 'value': ''}, {'key': 'repair_roster', 'value': ''}]
LOTS = [{'id': 'lot-1', 'shipped_at': '2026-09-01', 'qty': 10, 'rma_numbers': 'R1', 'received_qty': 4, 'ready_qty': 1, 'received_at': '2026-09-08'},   # 発送中6・要設定3
        {'id': 'lot-2', 'shipped_at': '2026-08-01', 'qty': 5, 'rma_numbers': 'R2', 'received_qty': 5, 'ready_qty': 5, 'received_at': '2026-08-10'}]    # 完了
HOLDS = [{'device_id': 'SSP-007', 'event': 'hold_open', 'created_at': '2026-09-10T00:00:00Z'},   # v_hold_latest(端末ごと最新)
         {'device_id': 'FS-001', 'event': 'hold_open', 'created_at': '2026-09-10T00:00:00Z'},    # r6: 保留中の FS(数量モードではどこにも出ない)
         {'device_id': 'SSP-006', 'event': 'hold_close', 'created_at': '2026-09-09T00:00:00Z'}]
fails = []
def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  -- {detail}' if detail and not cond else ''))
    if not cond: fails.append(name)

async def new_page(b, editor=True, cfg=None, fail_get=(), fail_post=(), state=None, **kw):
    state = state if state is not None else {}   # state['devices'] を差し替えると「サーバー側の現在値」を変えられる
    ctx = await b.new_context(**kw); pg = await ctx.new_page()
    errs, writes = [], []            # writes: (method, table, query, body)
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' else None)
    if editor: await pg.add_init_script("localStorage.setItem('dej6_editor_v2', JSON.stringify({ok:true, alias:'e2e-test'}))")
    async def route(r):
        u = r.request.url; m = r.request.method
        if 'supabase.co' not in u: await r.continue_(); return
        p = urllib.parse.urlparse(u); table = p.path.split('/rest/v1/')[-1]
        if m in ('PATCH', 'POST'):
            try: body = json.loads(r.request.post_data or 'null')
            except Exception: body = r.request.post_data
            writes.append((m, table, p.query, body))
            if table.split('?')[0] in fail_post: await r.fulfill(status=500, content_type='application/json', body='{"message":"e2e-forced-failure"}'); return
            await r.fulfill(status=204, body=''); return
        if table in fail_get: await r.fulfill(status=404, content_type='application/json', body='{"message":"relation does not exist"}'); return
        if table == 'devices':
            rows = state.get('devices', DEVICES); q = urllib.parse.parse_qs(p.query)
            if 'device_id' in q and q['device_id'][0].startswith('in.('):   # 再検証クエリ device_id=in.("A","B")
                ids = [x.strip('"') for x in q['device_id'][0][4:-1].split(',')]; rows = [d for d in rows if d['device_id'] in ids]
            await r.fulfill(status=200, content_type='application/json', body=json.dumps(rows))
        elif table == 'app_config': await r.fulfill(status=200, content_type='application/json', body=json.dumps(cfg if cfg is not None else CFG_BASE))
        elif table == 'fs_lots': await r.fulfill(status=200, content_type='application/json', body=json.dumps(LOTS))
        elif table == 'v_hold_latest': await r.fulfill(status=200, content_type='application/json', body=json.dumps(HOLDS))
        else: await r.fulfill(status=200, content_type='application/json', body='[]')
    await pg.route('**/*', route)
    return pg, errs, writes

async def scan(pg, text):
    await pg.keyboard.type(text, delay=5); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
async def stage(pg): return await pg.eval_on_selector('#scanStage', 'e=>e.className.replace("scan-stage ","")')
async def title(pg): return await pg.eval_on_selector('#scanTitle', 'e=>e.textContent')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # ── A. 通常画面(編集者・FS 数量モード ON) ──
        stateA = {}
        pg, errs, writes = await new_page(b, state=stateA, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        ids = await pg.eval_on_selector_all('#deviceBody tr td.fw-semibold', 'e=>e.map(x=>x.textContent.trim())')
        check('A 一覧: FS 個体行は非表示(数量モード)', not any(i.startswith('FS-') for i in ids) and 'SSP-005' in ids, str(ids))
        fs = await pg.eval_on_selector_all('#fsPanel [data-fs]', 'e=>Object.fromEntries(e.map(x=>[x.dataset.fs, +x.textContent]))')
        check('A FS 5区分: 総台数190 / BOX3 / 発送中6 / 要設定3 / 稼働178', fs == {'稼働': 178, '修理待ち(BOX)': 3, '発送中': 6, '返却済み・要設定': 3, '総台数': 190}, str(fs))
        check('A FS 5区分の合計 = 総台数', fs['稼働'] + fs['修理待ち(BOX)'] + fs['発送中'] + fs['返却済み・要設定'] == fs['総台数'])
        lots = await pg.eval_on_selector_all('#fsLotTable tbody tr[data-lot]', 'e=>e.map(x=>x.dataset.lot)')
        check('A ロット表は進行中のみ(完了 lot-2 は非表示)', lots == ['lot-1'], str(lots))
        check('A(r1) FS 個体行の表示トグルは存在しない', not await pg.query_selector('#fsPanel button:has-text("個体行")'))
        task_txt = await pg.eval_on_selector('#taskList', 'e=>e.textContent')
        check('A(r6) 数量モード: 今日やること(保留行含む)に FS 個体 ID が出ない', 'FS-00' not in task_txt and 'SSP-007' in task_txt, task_txt[:200])
        check('A サマリー(数量モード): FS 個体を除き 総台数7・修理待ち = 2(SSP-006, SSP-007保留) − 保留1 = 1', await pg.eval_on_selector('#cntTotal', 'e=>e.textContent') == '7' and await pg.eval_on_selector('#cntWait', 'e=>e.textContent') == '1' and '保留 1' in await pg.eval_on_selector('#holdNote', 'e=>e.textContent'), await pg.eval_on_selector('.row.g-2', 'e=>e.textContent'))
        check('A 保留バッジ: SSP-007 のみ', await pg.eval_on_selector_all('#deviceBody tr', 'e=>e.filter(r=>r.querySelector(".hold-badge")).map(r=>r.querySelector("td.fw-semibold").textContent.trim())') == ['SSP-007'])
        fb = await pg.eval_on_selector_all('#deviceBody .fault-badge', 'e=>e.map(x=>[x.textContent, x.classList.contains("bad")])')
        check('A 故障バッジ: 2回(黄)・3回(赤)、1回は非表示', sorted(fb) == [['故障2回', False], ['故障3回', True]], str(fb))
        # ロット更新: 受領 4→7 は PATCH fs_lots、不正値は拒否
        await pg.fill('tr[data-lot="lot-1"] [data-lot-field="received_qty"]', '7'); await pg.click('tr[data-lot="lot-1"] [data-lot-act="save"]'); await pg.wait_for_timeout(200)
        w = [x for x in writes if x[1] == 'fs_lots']
        check('A ロット更新 → PATCH fs_lots id=eq.lot-1 {received_qty:7, ready_qty:1}', len(w) == 1 and w[0][0] == 'PATCH' and w[0][2] == 'id=eq.lot-1' and w[0][3] == {'received_qty': 7, 'ready_qty': 1}, str(w))
        await pg.wait_for_timeout(200); writes.clear()
        await pg.fill('tr[data-lot="lot-1"] [data-lot-field="ready_qty"]', '9'); await pg.click('tr[data-lot="lot-1"] [data-lot-act="save"]'); await pg.wait_for_timeout(200)
        check('A ロット更新: 設定済み > 受領 は拒否(書込なし)', not [x for x in writes if x[1] == 'fs_lots'])
        await pg.fill('tr[data-lot="lot-1"] [data-lot-field="received_qty"]', '2'); await pg.fill('tr[data-lot="lot-1"] [data-lot-field="ready_qty"]', '0'); await pg.click('tr[data-lot="lot-1"] [data-lot-act="save"]'); await pg.wait_for_timeout(200)
        check('A(r4) ロット更新: 受領 4→2 の減少は拒否(書込なし)', not [x for x in writes if x[1] == 'fs_lots'] and '減らせません' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        check('A(r4) 受領済みロットに取消ボタンなし', not await pg.query_selector('tr[data-lot="lot-1"] [data-lot-act="unship"]'))
        await pg.fill('#fsWaitInput', '182'); await pg.click('#fsPanel button:has-text("台数を更新")'); await pg.wait_for_timeout(200)
        check('A(r4) BOX 台数 182(+発送中6+要設定3=191>190) は拒否・書込なし', not writes and '総台数 190 を超えます' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        await pg.fill('#fsWaitInput', '181'); await pg.click('#fsPanel button:has-text("台数を更新")'); await pg.wait_for_timeout(300)
        check('A(r4) BOX 台数 181 は RPC fs_set_wait {p_wait:181}', [x for x in writes if 'rpc/fs_set_wait' in x[1] and x[3] == {'p_wait': 181, 'p_by': 'e2e-test'}])
        writes.clear()
        await pg.click('#configBtn'); await pg.wait_for_selector('#configModal.show')
        await pg.fill('#cfgFsTotal', '11'); await pg.click('#configModal button:has-text("保存")'); await pg.wait_for_timeout(200)
        check('A(r4) 設定: 総台数 11 < BOX3+発送中6+要設定3 は拒否・書込なし', not writes and '稼働がマイナス' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        await pg.fill('#cfgFsTotal', '12')
        for bad in ['FORCERETURN', '005', 'SSP-005', 'FA ULT', 'ab']:
            await pg.fill('#cfgScanFault', bad); await pg.click('#configModal button:has-text("保存")'); await pg.wait_for_timeout(150)
            check(f'A(r5) 設定: 故障コード "{bad}" は拒否・書込なし', not writes and '故障コード' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        await pg.fill('#cfgScanFault', 'fault-2'); await pg.click('#configModal button:has-text("保存")'); await pg.wait_for_timeout(300)
        cw = [x for x in writes if x[1] == 'app_config']
        check('A(r4) 設定: 総台数 12 は保存(app_config upsert に fs_total=12)', cw and any(r['key'] == 'fs_total' and r['value'] == '12' for r in cw[0][3]), str(cw)[:200])
        check('A(r5) 設定: 故障コード fault-2 は大文字化して保存', cw and any(r['key'] == 'scan_fault' and r['value'] == 'FAULT-2' for r in cw[0][3]))
        writes.clear(); await pg.wait_for_timeout(300); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        # 発送: BOX 台数超えは拒否、正しい値は RPC fs_ship
        await pg.fill('#fsShipQty', '4'); await pg.fill('#fsShipRma', 'RMA-1'); await pg.click('#fsPanel button:has-text("発送(ロット作成)")'); await pg.wait_for_timeout(200)
        check('A 発送: BOX 台数(3)超えは拒否', not [x for x in writes if 'rpc/fs_ship' in x[1]])
        await pg.fill('#fsShipQty', '2'); await pg.click('#fsPanel button:has-text("発送(ロット作成)")'); await pg.wait_for_timeout(300)
        w = [x for x in writes if 'rpc/fs_ship' in x[1]]
        check('A 発送 → RPC fs_ship {p_qty:2, p_rma, p_by}', len(w) == 1 and w[0][3] == {'p_qty': 2, 'p_rma': 'RMA-1', 'p_by': 'e2e-test'}, str(w))
        writes.clear()
        # 棚卸モーダル
        await pg.click('#invBtn'); await pg.wait_for_selector('#inventoryModal.show')
        rows = await pg.eval_on_selector_all('#invBody tr', 'e=>e.map(r=>r.querySelector("strong")?.textContent)')
        check('A 棚卸対象 = 修理待ちの非FS(SSP-006, SSP-007)', rows == ['SSP-006', 'SSP-007'], str(rows))
        check('A 棚卸: 未選択なら保存ボタン無効', await pg.eval_on_selector('#invSaveBtn', 'e=>e.disabled') and '未選択 2件' in await pg.eval_on_selector('#invFooter', 'e=>e.textContent'))
        check('A 棚卸 FS 欄: BOX=3 / 稼働=178', await pg.input_value('#invFsWait') == '3' and await pg.input_value('#invFsActive') == '178')
        await pg.fill('#invFsWait', '5'); await pg.dispatch_event('#invFsWait', 'input')
        check('A 棚卸 FS 欄: BOX を 5 にすると稼働 176', await pg.input_value('#invFsActive') == '176')
        await pg.fill('#invFsWait', '200'); await pg.dispatch_event('#invFsWait', 'input')
        check('A(r4) 棚卸 FS 欄: 200 で稼働マイナス表示(赤)', await pg.eval_on_selector('#invFsActive', 'e=>e.classList.contains("text-danger")'))
        await pg.fill('#invFsWait', '5'); await pg.dispatch_event('#invFsWait', 'input')
        await pg.fill('#invAddId', 'SSP-999'); await pg.click('#inventoryModal button:has-text("追加")'); await pg.wait_for_timeout(100)
        await pg.fill('#invAddId', 'SSP-006'); await pg.click('#inventoryModal button:has-text("追加")'); await pg.wait_for_timeout(100)
        check('A 未登録追加: マスタに無い ID・既に修理待ちの ID は拒否', (await pg.eval_on_selector('#invAdded', 'e=>e.textContent')).strip() == 'なし')
        await pg.fill('#invAddId', '20'); await pg.click('#inventoryModal button:has-text("追加")'); await pg.wait_for_timeout(100)
        check('A 未登録追加: 「20」→ SSP-020(正常) を追加', 'SSP-020' in await pg.eval_on_selector('#invAdded', 'e=>e.textContent'))
        await pg.click('[data-inv-id="SSP-006"][data-inv-val="ok"]'); await pg.click('[data-inv-id="SSP-007"][data-inv-val="in"]'); await pg.wait_for_timeout(100)
        check('A 棚卸: 全行選択で保存ボタン有効', not await pg.eval_on_selector('#invSaveBtn', 'e=>e.disabled'))
        await pg.fill('#invFsWait', '200'); await pg.click('#invSaveBtn'); await pg.wait_for_timeout(300)
        check('A(r4) 棚卸保存: BOX 200 は書込前に拒否(何も保存していません)', not writes and '何も保存していません' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        await pg.fill('#invFsWait', '5')
        stateA['devices'] = [dict(d, status='発送済み') if d['device_id'] == 'SSP-020' else d for d in DEVICES]   # サーバー側だけ変わった(ローカルは正常のまま)
        await pg.click('#invSaveBtn'); await pg.wait_for_timeout(400)
        check('A(r3) 未登録追加がサーバー側で正常でなくなった → 再取得で検知・中止・書込なし・ID を明示', not writes and 'SSP-020' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent') and 'サーバー再確認' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent') and not await pg.eval_on_selector('#invSaveBtn', 'e=>e.disabled'))
        check('A(r3) 再検証はローカル allDevices ではなくサーバー応答(ローカルは正常のまま)', await pg.evaluate("allDevices.find(d=>d.device_id==='SSP-020').status") == '正常')
        check('A(r7) 書込前の中止では「途中まで保存」と言わない', '途中まで保存' not in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        stateA.pop('devices')
        await pg.fill('#invNote', 'e2e メモ'); await pg.click('#invSaveBtn'); await pg.wait_for_timeout(600)
        patches = [x for x in writes if x[0] == 'PATCH' and x[1] == 'devices']
        hist = [x for x in writes if x[1] == 'repair_history']
        cfgw = [x for x in writes if x[1] == 'app_config']
        p020 = [x for x in patches if x[2] == 'device_id=eq.SSP-020']; p006 = [x for x in patches if x[2] == 'device_id=eq.SSP-006']
        check('A 棚卸保存: SSP-020 → 修理待ち(manual, fault_count 1)', len(p020) == 1 and p020[0][3]['status'] == '修理待ち' and p020[0][3]['fault_source'] == 'manual' and p020[0][3]['fault_count'] == 1, str(p020))
        check('A 棚卸保存: SSP-006 → 正常(fault_count はクリアされない)', len(p006) == 1 and p006[0][3]['status'] == '正常' and 'fault_count' not in p006[0][3], str(p006))
        check('A 棚卸保存: SSP-007 は PATCH なし(BOX にある)', not [x for x in patches if 'SSP-007' in x[2]])
        ev = sorted((h['device_id'], h['event']) for h in (hist[0][3] if hist else []))
        check('A 棚卸保存: 履歴 = 020 unregistered_found / 006 inventory_ok / 007 hold_close', ev == [('SSP-006', 'inventory_ok'), ('SSP-007', 'hold_close'), ('SSP-020', 'unregistered_found')], str(ev))
        ck = {r['key']: r['value'] for r in (cfgw[0][3] if cfgw else [])}
        check('A 棚卸保存: app_config に last_inventory_*(fs_wait は直接書かない)', ck.get('last_inventory_by') == 'e2e-test' and 'fs_wait' not in ck and ck.get('last_inventory_note') == 'e2e メモ' and len(ck.get('last_inventory_date', '')) == 10, str(ck))
        check('A(r4) 棚卸保存: fs_wait=5 は RPC fs_set_wait', [x for x in writes if 'rpc/fs_set_wait' in x[1] and x[3] == {'p_wait': 5, 'p_by': 'e2e-test'}], str(writes)[:200])
        check('A 書込順: devices PATCH → repair_history → fs_set_wait → app_config', [x[1] for x in writes if x[1] in ('repair_history', 'rpc/fs_set_wait', 'app_config')] == ['repair_history', 'rpc/fs_set_wait', 'app_config'] and writes.index(patches[-1]) < writes.index(hist[0]))
        # openBulk は FLOWS に無い機種を SIM 対象から外すため UI からは混在にならない。描画関数を直接呼んでエスケープを検査する
        await pg.evaluate("bulkDevices = allDevices.filter(d => ['SSP-005','XX-001'].includes(d.device_id)); buildBulkForm('SIM起票済み')"); await pg.wait_for_timeout(100)
        check('A(r5) 一括SIM 混在機種の警告も device_type をエスケープ(XSS 未実行)', await pg.evaluate('window.__xss2') is None and await pg.eval_on_selector_all('#bulkForm img', 'e=>e.length') == 0 and '<img' in await pg.eval_on_selector('#bulkForm', 'e=>e.textContent'), await pg.eval_on_selector('#bulkForm', 'e=>e.innerHTML.slice(0,300)'))
        await pg.click('#deviceBody tr:has-text("XX-001")'); await pg.wait_for_selector('#statusModal.show'); await pg.wait_for_timeout(100)
        check('A(r2) device_type の HTML は一覧・モーダルでテキスト表示(XSS 未実行)', await pg.evaluate('window.__xss2') is None and await pg.eval_on_selector_all('#deviceBody img, #mType img', 'e=>e.length') == 0 and '<img' in await pg.eval_on_selector('#mType', 'e=>e.textContent'))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        check('A 通常画面 エラー0', not errs, str(errs)[:300])
        await pg.context.close()

        # ── B. 閲覧者(非編集者): 棚卸/スキャンボタン・FS の操作 UI が出ない ──
        pg, errs, writes = await new_page(b, editor=False, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        check('B 閲覧者: 棚卸/スキャン受付ボタン非表示', await pg.eval_on_selector('#invBtn', 'e=>e.classList.contains("d-none")') and await pg.eval_on_selector('#scanBtn', 'e=>e.classList.contains("d-none")'))
        check('B 閲覧者: FS 発送フォーム・ロット編集なし', not await pg.query_selector('#fsShipQty') and not await pg.query_selector('[data-lot-act]'))
        check('B 閲覧者: openInventory は拒否', await pg.evaluate('(openInventory(), !document.querySelector("#inventoryModal.show"))'))
        check('B 閲覧者 エラー0', not errs, str(errs)[:300])
        await pg.context.close()

        # ── C. FS 数量モード OFF: パネル非表示・FS 個体行が出る ──
        cfg_off = [r if r['key'] != 'fs_qty_mode' else {'key': 'fs_qty_mode', 'value': '0'} for r in CFG_BASE]
        pg, errs, writes = await new_page(b, cfg=cfg_off, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        ids = await pg.eval_on_selector_all('#deviceBody tr td.fw-semibold', 'e=>e.map(x=>x.textContent.trim())')
        check('C 数量モード OFF: fsPanel 非表示・FS 個体行あり', await pg.eval_on_selector('#fsPanel', 'e=>e.classList.contains("d-none")') and 'FS-001' in ids)
        check('C(r6) 数量モード OFF: サマリーは FS 個体を含む(総台数10・修理待ち 3−保留2=1)', await pg.eval_on_selector('#cntTotal', 'e=>e.textContent') == '10' and await pg.eval_on_selector('#cntWait', 'e=>e.textContent') == '1' and '保留 2' in await pg.eval_on_selector('#holdNote', 'e=>e.textContent'))
        check('C(r6) 数量モード OFF: 保留中の FS-001 がタスクの保留行に出る', 'FS-001' in await pg.eval_on_selector('#taskList', 'e=>e.textContent'))
        check('C 数量モード OFF エラー0', not errs, str(errs)[:300])
        await pg.context.close()

        # ── D. スキャン受付 ?mode=scan(編集者) ──
        pg, errs, writes = await new_page(b, viewport={'width': 1280, 'height': 800})
        await pg.goto(URL + '?mode=scan', wait_until='networkidle'); await pg.wait_for_timeout(200)
        check('D キオスク表示: body.scan-mode / nav・main 非表示 / scanPanel 表示', await pg.evaluate('document.body.classList.contains("scan-mode") && document.querySelector("nav.navbar").classList.contains("d-none") && document.getElementById("mainWrap").classList.contains("d-none") && !document.getElementById("scanPanel").classList.contains("d-none")'))
        meta = await pg.eval_on_selector('#scanMeta', 'e=>e.textContent')
        check('D メタ: 編集者名・区切り Enter・FAULT', all(x in meta for x in ['e2e-test', 'Enter', 'FAULT']), meta)
        check('D 初期: 待機', await stage(pg) == 'stage-idle')
        await scan(pg, '005')
        check('D 005(正常) → FAULT 待ち(黄)・カウントダウン表示', await stage(pg) == 'stage-wait' and 'SSP-005' in await title(pg) and 'あと' in await pg.eval_on_selector('#scanCountdown', 'e=>e.textContent'))
        await scan(pg, 'FAULT'); await pg.wait_for_timeout(300)
        p = [x for x in writes if x[0] == 'PATCH' and x[1] == 'devices']; h = [x for x in writes if x[1] == 'repair_history']
        check('D 005+FAULT → PATCH 修理待ち(fault_source scan, fault_count 3)', len(p) == 1 and p[0][2] == 'device_id=eq.SSP-005' and p[0][3]['status'] == '修理待ち' and p[0][3]['fault_source'] == 'scan' and p[0][3]['fault_count'] == 3, str(p))
        check('D 005+FAULT → repair_history scan_fault', len(h) == 1 and h[0][3][0]['event'] == 'scan_fault' and h[0][3][0]['to_status'] == '修理待ち' and h[0][3][0]['handler'] == 'e2e-test', str(h))
        check('D 005+FAULT → 緑「修理待ちに登録」', await stage(pg) == 'stage-ok' and '修理待ちに登録' in await title(pg))
        writes.clear(); await pg.wait_for_timeout(4200)
        check('D 登録後 4秒で待機に戻る', await stage(pg) == 'stage-idle')
        await scan(pg, 'SSP-012'); await pg.wait_for_timeout(300)
        p = [x for x in writes if x[0] == 'PATCH' and x[1] == 'devices']; h = [x for x in writes if x[1] == 'repair_history']
        check('D 012(返却済み) → 即 PATCH 正常 + scan_return', len(p) == 1 and p[0][3]['status'] == '正常' and 'fault_count' not in p[0][3] and h and h[0][3][0]['event'] == 'scan_return', str(p) + str(h))
        check('D 012 → 緑「正常に戻しました」', await stage(pg) == 'stage-ok' and '正常に戻しました' in await title(pg))
        writes.clear(); await pg.wait_for_timeout(4200)
        await scan(pg, '006')
        check('D 006(修理待ち) → 対象外(橙)・書込なし', await stage(pg) == 'stage-warn' and '処理中(修理待ち)' in await title(pg) and not writes)
        await scan(pg, 'FAULT')
        check('D 続けて FAULT → 「先に端末の QR」・書込なし', await stage(pg) == 'stage-warn' and '先に端末の QR' in await title(pg) and not writes)
        await pg.wait_for_timeout(4200)
        await scan(pg, 'FAULT')
        check('D 待機で FAULT 単独 → 「先に端末の QR」', 'stage-warn' == await stage(pg) and '先に端末の QR' in await title(pg))
        await pg.wait_for_timeout(4200)
        await scan(pg, '191')
        check('D 191(未登録) → 赤「マスタに未登録」・書込なし', await stage(pg) == 'stage-err' and 'マスタに未登録' in await title(pg) and not writes)
        await pg.wait_for_timeout(4200)
        await scan(pg, 'HELLO-WORLD')
        check('D 未知文字列 → 赤「無効な QR」', await stage(pg) == 'stage-err' and '無効な QR' in await title(pg))
        await pg.wait_for_timeout(4200)
        await scan(pg, 'FORCERETURN')
        check('D FORCERETURN → 「Phase 3 まで無効」・書込なし', 'Phase 3' in await title(pg) and not writes)
        await pg.wait_for_timeout(4200)
        await scan(pg, '005')
        check('D 005 → FAULT 待ち', await stage(pg) == 'stage-wait')
        await pg.wait_for_timeout(900)
        check('D 600ms(scan_timeout_ms) 無入力 → 待機に戻り書込なし', await stage(pg) == 'stage-idle' and not writes)
        await scan(pg, 'FAULT')
        check('D タイムアウト後の FAULT → 順序違い(書込なし)', await stage(pg) == 'stage-warn' and not writes)
        await pg.wait_for_timeout(4200)
        await scan(pg, '007')
        check('D(r2) 007(修理待ち・保留中) → 対象外(橙)・書込なし(保留解除は棚卸のみ)', not writes and await stage(pg) == 'stage-warn' and '保留中' in await pg.eval_on_selector('#scanSub', 'e=>e.textContent'), str(writes))
        recent = await pg.eval_on_selector_all('#scanRecent tr', 'e=>e.length')
        check('D 直近の受付は最大10行', recent == 10, recent)
        check('D スキャン受付 エラー0', not errs, str(errs)[:300])
        await pg.context.close()

        # ── E. スキャン受付 未ログイン: 書込拒否 / 区切り Tab 設定 ──
        pg, errs, writes = await new_page(b, editor=False, viewport={'width': 1280, 'height': 800})
        await pg.goto(URL + '?mode=scan', wait_until='networkidle'); await pg.wait_for_timeout(200)
        check('E 未ログイン: PIN ログインボタン表示・メタに未ログイン', not await pg.eval_on_selector('#scanLoginBtn', 'e=>e.classList.contains("d-none")') and '未ログイン' in await pg.eval_on_selector('#scanMeta', 'e=>e.textContent'))
        await scan(pg, '005'); await scan(pg, 'FAULT'); await pg.wait_for_timeout(200)
        check('E 未ログイン: 005+FAULT は書込なし・赤「PIN でログイン」', not writes and await stage(pg) == 'stage-err' and 'PIN でログイン' in await title(pg))
        await pg.wait_for_timeout(5200)
        await scan(pg, '012'); await pg.wait_for_timeout(200)
        check('E 未ログイン: 返却済み 012 も書込なし', not writes and await stage(pg) == 'stage-err')
        check('E 未ログイン エラー0', not errs, str(errs)[:300])
        await pg.context.close()
        cfg_badfault = [r if r['key'] != 'scan_fault' else {'key': 'scan_fault', 'value': 'FORCERETURN'} for r in CFG_BASE]
        pg, errs, writes = await new_page(b, cfg=cfg_badfault, viewport={'width': 1280, 'height': 800})
        await pg.goto(URL + '?mode=scan', wait_until='networkidle'); await pg.wait_for_timeout(200)
        check('E(r5) 不正な scan_fault(FORCERETURN) → メタに警告・既定 FAULT', '設定値が不正' in await pg.eval_on_selector('#scanMeta', 'e=>e.textContent'))
        await scan(pg, '005'); await scan(pg, 'FAULT'); await pg.wait_for_timeout(300)
        check('E(r5) 不正設定でも FAULT で故障登録できる', any(x[0] == 'PATCH' and x[3].get('fault_source') == 'scan' for x in writes))
        check('E(r5) 不正設定 エラー0', not errs, str(errs)[:300])
        await pg.context.close()
        cfg_tab = [r if r['key'] != 'scan_delim' else {'key': 'scan_delim', 'value': 'Tab'} for r in CFG_BASE]
        pg, errs, writes = await new_page(b, cfg=cfg_tab, viewport={'width': 1280, 'height': 800})
        await pg.goto(URL + '?mode=scan', wait_until='networkidle'); await pg.wait_for_timeout(200)
        await pg.keyboard.type('005', delay=5); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        check('E 区切り Tab 設定: Enter では確定しない', await stage(pg) == 'stage-idle')
        await pg.keyboard.press('Tab'); await pg.wait_for_timeout(150)
        check('E 区切り Tab 設定: Tab で確定 → FAULT 待ち', await stage(pg) == 'stage-wait' and 'SSP-005' in await title(pg))
        check('E 区切り Tab エラー0', not errs, str(errs)[:300])
        await pg.context.close()

        # ── F(r1). 障害系: fs_lots 取得失敗は接続エラー / 後続 POST 失敗は「途中まで保存」を明示 / 一括修理待ちは端末ごと fault_count ──
        pg, errs, writes = await new_page(b, fail_get=('fs_lots',), viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_timeout(300)
        check('F fs_lots 404 → 接続エラー表示・FS パネル非表示・migration 案内', await pg.eval_on_selector('#dbStatus', 'e=>e.textContent') == '接続エラー' and await pg.eval_on_selector('#fsPanel', 'e=>e.classList.contains("d-none")') and 'migration_v2_2.sql' in await pg.eval_on_selector('#deviceBody', 'e=>e.textContent'))
        await pg.context.close()
        pg, errs, writes = await new_page(b, fail_post=('repair_history',), viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        await pg.goto(URL + '?mode=scan', wait_until='networkidle'); await pg.wait_for_timeout(200)
        await scan(pg, '005'); await scan(pg, 'FAULT'); await pg.wait_for_timeout(300)
        check('F スキャン: 履歴 POST 失敗 → 赤「保存済み・履歴の保存に失敗」+途中保存の明示', await stage(pg) == 'stage-err' and '履歴の保存に失敗' in await title(pg) and '途中まで保存' in await pg.eval_on_selector('#scanSub', 'e=>e.textContent'))
        check('F スキャン: devices PATCH は実行されている', any(x[0] == 'PATCH' and x[1] == 'devices' for x in writes))
        await pg.context.close()
        pg, errs, writes = await new_page(b, fail_post=('repair_history',), viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        await pg.click('#deviceBody tr:has-text("SSP-012")'); await pg.wait_for_selector('#statusModal.show')
        await pg.evaluate("selectStatus('正常')"); await pg.wait_for_timeout(100); await pg.click('#saveBtn'); await pg.wait_for_timeout(400)
        check('F 単体保存: 履歴 POST 失敗 → toast に「途中まで保存」', '途中まで保存された可能性' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        await pg.context.close()
        # 一括: fault_count 0 と 2 の端末を 修理待ち に → 個別 PATCH で 1 と 3
        pg, errs, writes = await new_page(b, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        await pg.evaluate("selection.add('SSP-005'); selection.add('SSP-020'); openBulk('修理待ち')"); await pg.wait_for_selector('#bulkModal.show')
        await pg.evaluate("document.getElementById('bDefCat') && (document.getElementById('bDefCat').value = document.getElementById('bDefCat').options[0].value)")
        await pg.click('#bulkSaveBtn'); await pg.wait_for_timeout(500)
        pb = {x[2]: x[3] for x in writes if x[0] == 'PATCH' and x[1] == 'devices'}
        check('F 一括 修理待ち: 端末ごとに PATCH(005→3, 020→1)', pb.get('device_id=eq.SSP-005', {}).get('fault_count') == 3 and pb.get('device_id=eq.SSP-020', {}).get('fault_count') == 1, str(pb))
        check('F 一括 修理待ち: 履歴は2件', any(x[1] == 'repair_history' and len(x[3]) == 2 for x in writes))
        writes.clear(); await pg.wait_for_timeout(300)
        await pg.evaluate("selection.clear(); selection.add('SSP-006'); openBulk('修理待ち')"); await pg.wait_for_timeout(200)
        check('F(r8) 既に修理待ちの端末だけを 修理待ち へ → 対象なし(モーダル開かず・書込なし)', not writes and not await pg.query_selector('#bulkModal.show') and '対象機器がありません' in await pg.eval_on_selector('#toastMsg', 'e=>e.textContent'))
        r = await pg.evaluate("statusPatch(allDevices.find(d=>d.device_id==='SSP-006'), '修理待ち', {handler:'x'})")
        check('F(r8) statusPatch: 修理待ち→修理待ち では fault_count を含まない', 'fault_count' not in r)
        r = await pg.evaluate("statusPatch(allDevices.find(d=>d.device_id==='SSP-012'), '修理待ち', {handler:'x'})")
        check('F(r8) statusPatch: 返却済み→修理待ち は fault_count+1(1→2)', r.get('fault_count') == 2)
        check('F 障害系 エラー0(pageerror なし)', not [x for x in errs if x.startswith('pageerror')], str(errs)[:300])
        pg2 = pg
        pg, errs, writes = await new_page(b, cfg=cfg_tab, viewport={'width': 1280, 'height': 800})
        await pg.goto(URL + '?mode=scan', wait_until='networkidle'); await pg.wait_for_timeout(200)
        await pg2.context.close()
        # スクショ(モック07 と見比べる用)
        await pg.screenshot(path=str(ROOT / 'docs/mockup/impl_scan_kiosk.png'))
        await pg.context.close(); await b.close()
    print('\nsummary:', ('FAIL ' + str(len(fails))) if fails else 'PASS', f'({len(fails)} fail)')
    sys.exit(1 if fails else 0)
asyncio.run(asyncio.wait_for(main(), timeout=280))
