"""修理手順ガイド v2.1 — 動的テスト(プラン §7 動的①〜⑧)。Playwright headless。
Supabase / Firebase への通信は page.route で差し替え、実データには一切触れない。
使い方: py tests/test_repair_guide_e2e.py   終了コード 0=全PASS / 1=FAIL"""
import asyncio, json, re, sys, pathlib, urllib.parse
from playwright.async_api import async_playwright
sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # 出力先がパイプ/ファイルでも cp932 で落ちない(≤ 等を含む)

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = (ROOT / 'index.html').as_uri()
XSS_ADDR = '<script>window.__xss=1</script>"\'&<b>青梅</b>\n2行目'
DEVICES = [
    {'device_id': 'SSP-001', 'device_type': 'SSP', 'status': 'SIM起票済み', 'model': 'TC57', 'serial_number': 'S1', 'asset_number': 'A1', 'memo': '', 'zebra_rma': '', 'ops_handler': 'x', 'status_changed_at': '2026-09-01T00:00:00Z'},
    {'device_id': 'FS-001', 'device_type': 'FS', 'status': '修理中', 'model': 'RS5100', 'serial_number': 'S2', 'asset_number': 'A2', 'memo': '', 'zebra_rma': '', 'ops_handler': 'x', 'status_changed_at': '2026-09-01T00:00:00Z'},  # LEGACY 名
    {'device_id': 'ZD-001', 'device_type': 'ZD611', 'status': '正常', 'model': 'ZD611', 'serial_number': 'S3', 'asset_number': 'A3', 'memo': '', 'zebra_rma': '', 'ops_handler': 'x', 'status_changed_at': None},
]
CFG = [{'key': 'addr_zebra', 'value': XSS_ADDR}, {'key': 'addr_tyo4', 'value': 'TYO4住所<i>'}, {'key': 'addr_return', 'value': 'DEJ6'}]
fails = []
def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  -- {detail}' if detail and not cond else ''))
    if not cond: fails.append(name)

async def new_page(b, **kw):
    ctx = await b.new_context(**kw)
    await ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin='file://') if False else None
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' else None)
    async def route(r):
        u = r.request.url
        if 'supabase.co' in u:
            if '/devices' in u: await r.fulfill(status=200, content_type='application/json', body=json.dumps(DEVICES))
            elif '/app_config' in u: await r.fulfill(status=200, content_type='application/json', body=json.dumps(CFG))
            else: await r.fulfill(status=200, content_type='application/json', body='[]')
        elif 'firebasedatabase.app' in u: await r.fulfill(status=200, content_type='application/json', body='{}')
        else: await r.continue_()
    await pg.route('**/*', route)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # ── ① ナビ[修理手順] → モーダル・タブ9・各タブのカード数 = フロー長 ──
        pg, errs = await new_page(b, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        check('起動時: guideModal は開いていない(パラメータ無し)', not await pg.query_selector('#guideModal.show'))
        await pg.click('button:has-text("修理手順")'); await pg.wait_for_selector('#guideModal.show')
        tabs = await pg.eval_on_selector_all('#guideTabs .nav-link', 'e=>e.map(x=>x.textContent)')
        check('① タブ9個(8機種+その他)', tabs == ['SSP', 'FS', 'ZD611', '無線機', 'Avery', 'Handy', 'PC', '携帯', 'その他'], str(tabs))
        flows = await pg.evaluate('({...FLOWS, Other: GUIDE_DEFAULT_FLOW})')
        for t in ['SSP', 'FS', 'ZD611', 'Radio', 'Avery', 'Handy', 'PC', 'Mobile', 'Other']:
            await pg.click(f'[data-guide-type="{t}"]'); await pg.wait_for_timeout(50)
            n = await pg.eval_on_selector_all('.guide-step', 'e=>e.length')
            check(f'① {t} カード数 = フロー長 {len(flows[t])}', n == len(flows[t]), n)
            active = await pg.eval_on_selector('#guideTabs .active', 'e=>e.dataset.guideType')
            check(f'① {t} タブがアクティブ', active == t)
        # ⑥ XSS: appCfg の住所がテキスト表示・スクリプト未実行
        await pg.click('[data-guide-type="SSP"]'); await pg.wait_for_timeout(50)
        txt = await pg.eval_on_selector('.guide-summary', 'e=>e.textContent')
        check('⑥ 住所の <script> がテキストとして表示', '<script>window.__xss=1</script>' in txt)
        check('⑥ 住所内スクリプト未実行', await pg.evaluate('window.__xss') is None)
        check('⑥ 住所の <b> が要素化されていない', await pg.eval_on_selector_all('.guide-summary b', 'e=>e.length') == 0)
        # ⑦ 全 href が https か #
        hrefs = await pg.eval_on_selector_all('#guideBody a[href]', 'e=>e.map(a=>a.getAttribute("href"))')
        check('⑦ ガイド内 href は https:// か # のみ', all(h.startswith('https://') or h == '#' for h in hrefs), str(hrefs)[:200])
        bad = await pg.evaluate("""() => { const t = { ...GUIDE_DATA.SSP, links: [{label:'x', url:'javascript:alert(1)'}] };
            const keep = GUIDE_DATA.SSP; GUIDE_DATA.SSP = t; guideRender('SSP', null); GUIDE_DATA.SSP = keep;
            const a = [...document.querySelectorAll('#guideBody a')].find(a=>a.textContent.includes('x'));
            return a ? a.getAttribute('href') : 'NOLINK' }""")
        check('⑦ links[].url が javascript: → href="#"', bad == '#', bad)
        check('⑦ guideSafeUrl(不正スキーム) → #', await pg.evaluate("guideSafeUrl('http://x') === '#' && guideSafeUrl('javascript:1') === '#' && guideSafeUrl(GUIDE_URL_WIKI) === GUIDE_URL_WIKI"))
        # ④ URLコピー → ?guide=<機種> 形式 → その URL を開くと同じ機種
        await pg.click('[data-guide-type="ZD611"]'); await pg.wait_for_timeout(50)
        link = await pg.evaluate('guideDeepLink(guideState.type)')
        check('④ guideDeepLink が ?guide=ZD611', urllib.parse.parse_qs(urllib.parse.urlparse(link).query) == {'guide': ['ZD611']}, link)
        # ⑤ 印刷: 新ウィンドウの title・見出し・ステップ数・.btn 非表示・A4 3枚以内
        async with pg.context.expect_page() as pw:
            await pg.evaluate("window.print = () => {}; guidePrint()")   # 印刷ダイアログは無効化
        w = await pw.value; await w.wait_for_load_state('load'); await w.wait_for_timeout(300)
        title = await w.title(); body = await w.evaluate('document.body.innerText')
        heads = ['A. 修理に出す前に試す', 'B. 修理フロー', 'C. 復帰チェック', 'D. リンク集', 'E. 発送の鉄則']
        pos = [body.find(h) for h in heads]
        check('⑤ 印刷 title に機種名', 'ZD611' in title, title)
        check('⑤ 印刷 本文に A〜E がこの順', all(x >= 0 for x in pos) and pos == sorted(pos), str(pos))
        check('⑤ 印刷 ステップ数 = フロー長', await w.eval_on_selector_all('.guide-step', 'e=>e.length') == len(flows['ZD611']))
        check('⑤ 印刷 .btn 非表示', await w.evaluate("[...document.querySelectorAll('.btn')].every(b=>getComputedStyle(b).display==='none')"))
        pdf = await w.pdf(format='A4', print_background=True)
        pages = len(re.findall(rb'/Type\s*/Page[^s]', pdf))
        check('⑤ 印刷 A4 枚数 ≤3', 1 <= pages <= 3, pages)
        await w.close()
        check('①〜⑦ コンソール/ページエラー 0', not errs, str(errs)[:300])
        await pg.context.close()

        # ── ② ディープリンク ──
        for q, exp in [('?guide=ZD611', 'ZD611'), ('?guide=%3Cscript%3E', 'Other'), ('?guide=', 'Other'), ('?guide=Radio', 'Radio')]:
            pg, errs = await new_page(b)
            await pg.goto(URL + q, wait_until='networkidle'); await pg.wait_for_selector('#guideModal.show')
            await pg.wait_for_selector('#deviceBody tr td.fw-semibold')   # loadAll 完了
            act = await pg.eval_on_selector('#guideTabs .active', 'e=>e.dataset.guideType')
            check(f'② {q} → {exp}', act == exp and not errs, f'{act} {errs}')
            summary = await pg.eval_on_selector('.guide-summary', 'e=>e.textContent')
            exp_addr = 'TYO4住所<i>' if exp in ('Other', 'Radio') else XSS_ADDR.split('\n')[0]
            check(f'② {q}: loadAll 後に登録済み住所が反映', exp_addr in summary and '住所はマスタ設定で登録' not in summary, summary[-120:])
            await pg.context.close()

        # ── ③ デバイス行 → statusModal → 手順リンク → 「いまここ」1個(LEGACY 名の機器でも) ──
        for dev_id, exp_type, exp_status in [('SSP-001', 'SSP', 'SIM起票済み'), ('FS-001', 'FS', '修理待ち'), ('ZD-001', 'ZD611', '正常')]:
            pg, errs = await new_page(b, viewport={'width': 1280, 'height': 900})
            # 編集者状態(localStorage)を先に入れて入力欄を有効化する。PIN は使わない(検証済みフラグのみ)
            await pg.add_init_script("localStorage.setItem('dej6_editor_v2', JSON.stringify({ok:true, alias:'e2e-test'}))")
            await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
            await pg.evaluate("window.__statusShown0 = 0; document.getElementById('statusModal').addEventListener('shown.bs.modal', () => window.__statusShown0++)")
            await pg.click(f'#deviceBody tr td.fw-semibold:has-text("{dev_id}")'); await pg.wait_for_function('window.__statusShown0 > 0', timeout=5000)   # フェードイン完了(実利用と同じタイミング)
            check(f'③ {dev_id}: 編集モードでメモ欄が有効', await pg.evaluate("!document.getElementById('mMemoInput').disabled"))
            await pg.fill('#mMemoInput', 'memo-keep')
            # Bootstrap はフェード完了(shown.bs.modal)までキー操作を無視する。実利用と同じく表示完了を待ってから Esc を送る(100ms 固定待ちはフェード .15s と競合して不安定)
            await pg.evaluate("window.__guideShown = 0; document.getElementById('guideModal').addEventListener('shown.bs.modal', () => window.__guideShown++)")
            await pg.click('#mGuideBtn'); await pg.wait_for_function('window.__guideShown > 0', timeout=5000)
            check(f'③ {dev_id}: 表示完了後フォーカスはガイド内(Esc が届く)', await pg.evaluate("document.getElementById('guideModal').contains(document.activeElement)"))
            act = await pg.eval_on_selector('#guideTabs .active', 'e=>e.dataset.guideType')
            here = await pg.eval_on_selector_all('.guide-step.current', 'e=>e.map(x=>x.querySelector(".status-badge").textContent)')
            check(f'③ {dev_id}: 機種 {exp_type} / いまここ=[{exp_status}]', act == exp_type and here == [exp_status], f'{act} {here}')
            check(f'③ {dev_id}: here-badge は1個', await pg.eval_on_selector_all('.here-badge', 'e=>e.length') == 1)
            # ガイド表示中は statusModal は隠れている(多重モーダル回避)。入力値を変えてから Esc で閉じる → statusModal が同じ入力値のまま戻る
            check(f'③ {dev_id}: ガイド表示中 statusModal は非表示', not await pg.query_selector('#statusModal.show'))
            # Esc → ガイドがフェードアウト → hidden.bs.modal → statusModal 再表示(shown.bs.modal)。固定待ちではなく再表示イベントを待つ(5秒で打ち切り=FAIL)
            await pg.evaluate("window.__statusShown = 0; document.getElementById('statusModal').addEventListener('shown.bs.modal', () => window.__statusShown++)")
            await pg.keyboard.press('Escape')
            try: await pg.wait_for_function('window.__statusShown > 0', timeout=5000); reshown = True
            except Exception: reshown = False
            check(f'③ {dev_id}: Esc 後 5秒以内に statusModal の shown.bs.modal', reshown)
            check(f'③ {dev_id}: Esc でガイドが閉じる', not await pg.query_selector('#guideModal.show'))
            check(f'③ {dev_id}: statusModal が再表示・同じ機器', bool(await pg.query_selector('#statusModal.show')) and await pg.eval_on_selector('#mDeviceId', 'e=>e.textContent') == dev_id)
            check(f'③ {dev_id}: 入力途中のメモが保持されている', await pg.eval_on_selector('#mMemoInput', 'e=>e.value') == 'memo-keep')
            check(f'③ {dev_id}: body.modal-open・backdrop 1枚', await pg.evaluate("document.body.classList.contains('modal-open') && document.querySelectorAll('.modal-backdrop').length===1"))
            check(f'③ {dev_id}: エラー0', not errs, str(errs)[:200])
            await pg.context.close()

        # ── ③' 速いタップ: statusModal の .show 直後(フェードイン中)に手順ボタンを押しても、表示完了後にガイドが開く(Bootstrap は遷移中の hide() を無視する) ──
        pg, errs = await new_page(b, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        await pg.evaluate("window.__guideShown = 0; document.getElementById('guideModal').addEventListener('shown.bs.modal', () => window.__guideShown++)")
        await pg.click('#deviceBody tr td.fw-semibold:has-text("SSP-001")'); await pg.wait_for_selector('#statusModal.show')
        await pg.evaluate("guideOpenFromStatus()")   # .show 付与直後 = フェードイン中に押す
        try: await pg.wait_for_function('window.__guideShown > 0', timeout=5000); opened = True
        except Exception: opened = False
        check("③' フェードイン中の押下でも 5秒以内にガイドが開く", opened)
        check("③' その時 statusModal は隠れている", not await pg.query_selector('#statusModal.show'))
        check("③' エラー0", not errs, str(errs)[:200])
        await pg.context.close()

        # ── ③'' 同一ページで再オープン: 機器A→閉じる→機器B→手順→Esc→機器B に復帰→もう一度手順(2周目も statusModal が隠れてガイドが開く) ──
        pg, errs = await new_page(b, viewport={'width': 1280, 'height': 900})
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        await pg.evaluate("window.__sShown = 0; window.__gShown = 0; document.getElementById('statusModal').addEventListener('shown.bs.modal', () => window.__sShown++); document.getElementById('guideModal').addEventListener('shown.bs.modal', () => window.__gShown++)")
        await pg.click('#deviceBody tr td.fw-semibold:has-text("SSP-001")'); await pg.wait_for_function('window.__sShown === 1', timeout=5000)
        await pg.keyboard.press('Escape'); await pg.wait_for_function("!document.querySelector('#statusModal.show') && !document.querySelector('.modal-backdrop')", timeout=5000)
        await pg.click('#deviceBody tr td.fw-semibold:has-text("ZD-001")'); await pg.wait_for_function('window.__sShown === 2', timeout=5000)
        check("③'' 2台目の statusModal は ZD-001", await pg.eval_on_selector('#mDeviceId', 'e=>e.textContent') == 'ZD-001')
        for n in (1, 2):
            await pg.click('#mGuideBtn')
            try: await pg.wait_for_function(f'window.__gShown === {n}', timeout=5000); ok = True
            except Exception: ok = False
            check(f"③'' {n}周目: 手順ボタンでガイドが開く", ok)
            check(f"③'' {n}周目: statusModal は隠れている / 機種 ZD611", not await pg.query_selector('#statusModal.show') and await pg.eval_on_selector('#guideTabs .active', 'e=>e.dataset.guideType') == 'ZD611')
            await pg.keyboard.press('Escape')
            try: await pg.wait_for_function(f'window.__sShown === {2+n}', timeout=5000); back = True
            except Exception: back = False
            check(f"③'' {n}周目: Esc で statusModal(ZD-001) に復帰", back and await pg.eval_on_selector('#mDeviceId', 'e=>e.textContent') == 'ZD-001')
        check("③'' backdrop 1枚・エラー0", await pg.evaluate("document.querySelectorAll('.modal-backdrop').length===1") and not errs, str(errs)[:200])
        await pg.context.close()

        # ── ⑧ モバイル 390px: タブ横スクロール・ヘッダボタンはアイコンのみ・横はみ出し無し ──
        pg, errs = await new_page(b, viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        await pg.goto(URL + '?guide=SSP', wait_until='networkidle'); await pg.wait_for_selector('#guideModal.show'); await pg.wait_for_timeout(300)
        check('⑧ タブは横スクロール(overflow-x auto, scrollWidth>clientWidth)', await pg.evaluate("(e=>getComputedStyle(e).overflowX==='auto' && e.scrollWidth>e.clientWidth)(document.getElementById('guideTabs'))"))
        check('⑧ ヘッダボタンのラベル非表示(アイコンのみ)', await pg.evaluate("[...document.querySelectorAll('#guideCopyBtn span,#guidePrintBtn span')].every(s=>getComputedStyle(s).display==='none')"))
        check('⑧ モーダル本文が横にはみ出さない', await pg.evaluate("(e=>e.scrollWidth<=e.clientWidth+1)(document.querySelector('#guideModal .modal-body'))"))
        await pg.screenshot(path=str(ROOT / 'docs/mockup/impl_mobile.png'))
        check('⑧ エラー0', not errs, str(errs)[:200])
        await pg.context.close()
        # 実装スクショ(デスクトップ・SSP から いまここ)
        pg, errs = await new_page(b, viewport={'width': 1280, 'height': 900}, device_scale_factor=1.5)
        await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_selector('#deviceBody tr td.fw-semibold')
        await pg.click('#deviceBody tr:has-text("SSP-001")'); await pg.wait_for_selector('#statusModal.show'); await pg.click('#mGuideBtn')
        await pg.wait_for_selector('#guideModal.show'); await pg.wait_for_timeout(400); await pg.screenshot(path=str(ROOT / 'docs/mockup/impl_desktop.png'))
        await pg.context.close(); await b.close()
    print('\nsummary:', ('FAIL ' + str(len(fails))) if fails else 'PASS', f'({len(fails)} fail)')
    sys.exit(1 if fails else 0)
asyncio.run(asyncio.wait_for(main(), timeout=300))
