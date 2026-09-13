"""修理手順ガイド v2.1 — 静的テスト(プラン §7 ⓪〜⑧)。index.html をテキスト解析し、JS 定数は Node(bun) で評価して検査する。
使い方: py tests/test_repair_guide.py   終了コード 0=全PASS / 1=FAIL"""
import re, sys, json, subprocess, pathlib, importlib.util
sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # 出力先がパイプ/ファイルでも cp932 で落ちない(≤ 等を含む)

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDX = ROOT / 'index.html'
src = IDX.read_text(encoding='utf-8')
fails = []
def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  -- {detail}' if detail and not cond else ''))
    if not cond: fails.append(name)

# ── JS 定数を Node で評価して JSON 化(FLOWS / SIM_TEMPLATES / ZEBRA_TYPES / TYPE_LABEL / GUIDE_*) ──
def grab_const(name):
    m = re.search(r'^const %s\s*=\s*' % re.escape(name), src, re.M); assert m, name
    i = m.end(); depth = 0; j = i
    # 配列/オブジェクト/文字列のいずれか: 括弧の対応で終端を探す(文字列内の括弧は無視)
    if src[i] == "'":
        j = src.index("'", i + 1) + 1
    else:
        opener = src[i]; closer = {'[': ']', '{': '}'}[opener]; in_str = None
        while True:
            c = src[j]
            if in_str:
                if c == in_str: in_str = None
            elif c in "'\"`": in_str = c
            elif c == opener: depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0: j += 1; break
            j += 1
    return src[i:j]
NAMES = ['FLOWS', 'SIM_TEMPLATES', 'ZEBRA_TYPES', 'TYPE_LABEL', 'GUIDE_URL_WIKI', 'GUIDE_URL_ZEBRA', 'GUIDE_URL_SLACK',
         'GUIDE_DEFAULT_FLOW', 'GUIDE_STEP_BASE', 'GUIDE_DATA']
def js_to_json(t):
    """JS オブジェクトリテラル(単一引用符文字列・裸キー・末尾カンマ・true/false/null)を JSON 文字列へ。Node 不要。"""
    out = []; i = 0; n = len(t)
    while i < n:
        c = t[i]
        if c == "'":                                   # 単一引用符文字列 → JSON 文字列
            j = i + 1; buf = ''
            while t[j] != "'":
                if t[j] == '\\': buf += t[j:j+2]; j += 2
                else: buf += t[j]; j += 1
            out.append(json.dumps(buf, ensure_ascii=False)); i = j + 1
        elif c == '/' and t[i:i+2] == '//':            # 行コメントを捨てる
            i = t.index('\n', i)
        else:
            out.append(c); i += 1
    t = ''.join(out)
    t = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', t)   # 裸キー
    t = re.sub(r',(\s*[}\]])', r'\1', t)                                    # 末尾カンマ
    return t
C = {}
for nme in NAMES:
    raw = grab_const(nme)
    try: C[nme] = json.loads(js_to_json(raw))
    except Exception as e: print('FAIL const parse', nme, e); sys.exit(1)
FLOWS, GD, GSB, DEF = C['FLOWS'], C['GUIDE_DATA'], C['GUIDE_STEP_BASE'], C['GUIDE_DEFAULT_FLOW']
def flow_of(t): return FLOWS.get(t) or DEF
def merged_actions(t, s):
    ex = GD[t].get('step_extra', {}).get(s, {}); base = GSB.get(s, {})
    return ex.get('actions', []) if ex.get('replace') else base.get('actions', [])

# ⓪ 1行1操作(check_one_action.py を再利用: 自己テスト + 全 actions)
spec = importlib.util.spec_from_file_location('coa', ROOT / 'docs/mockup/check_one_action.py')
RULE = re.compile(r"して|し、|し「|、|て(?!$)")
def violates(line): return bool(RULE.search(re.sub(r"\([^)]*\)|（[^）]*）", "", line)))
all_actions = [a for st in GSB.values() for a in st.get('actions', [])]
for t, g in GD.items():
    for st in g.get('step_extra', {}).values():
        all_actions += st.get('actions', []) + st.get('fallback', {}).get('actions', [])
check('⓪ 1行1操作: 全 actions/fallback.actions が規則に一致しない', not any(violates(a) for a in all_actions), str([a for a in all_actions if violates(a)]))
check('⓪ 自己テスト(must-fail)', all(violates(x) for x in ['依頼文を貼り付けて起票する', 'まとめて選択する', '選び、症状を入力する']))
check('⓪ 自己テスト(must-pass)', not any(violates(x) for x in ['台数を Manifest / RMA と照合する', 'SIMテンプレートを開く(下のリンク)']))
r = subprocess.run(['py', str(ROOT / 'docs/mockup/check_one_action.py'), str(IDX)], capture_output=True, text=True, encoding='utf-8')
check('⓪ check_one_action.py index.html → rc=0', r.returncode == 0, r.stdout.strip()[-120:])

# ① step_extra のキーが解決済みフローに含まれる / actions を持つなら replace:true
for t, g in GD.items():
    for s, ex in g.get('step_extra', {}).items():
        check(f'① {t}.step_extra[{s}] はフロー内', s in flow_of(t))
        if 'actions' in ex: check(f'① {t}.step_extra[{s}] actions は replace:true', ex.get('replace') is True)

# ② done/title の中のステータス名は正式6値のみ(「返却済み・要設定」は括弧内補足のみ許可)
OFFICIAL = ['修理待ち', 'SIM起票済み', 'RMA登録済み', '発送済み', '返却済み', '正常']
texts = [st.get('done', '') + st.get('title', '') for st in GSB.values()] + \
        [ex.get('done', '') + ex.get('title', '') for g in GD.values() for ex in g.get('step_extra', {}).values()]
for tx in texts:
    core = re.sub(r"\([^)]*\)|（[^）]*）", "", tx)
    check(f'② 表示名「返却済み・要設定」を正式名として使わない: {tx[:30]}', '返却済み・要設定' not in core)

# ③ first_aid≥3 / return_check≥1 / マージ後 actions≥1 / 回帰(ZD611・PC・SSP)
for t, g in GD.items():
    check(f'③ {t}.first_aid ≥3', len(g['first_aid']) >= 3)
    check(f'③ {t}.return_check ≥1', len(g['return_check']) >= 1)
    for s in flow_of(t): check(f'③ {t}[{s}] マージ後 actions ≥1', len(merged_actions(t, s)) >= 1)
check('③ ZD611 修理待ち 期待配列', merged_actions('ZD611', '修理待ち') == ['番号札(No.)を確認する', 'このツールで機器をタップする', '「修理待ち」を押す', '不具合カテゴリーを選ぶ', '症状を入力する', '「保存する」を押す', '修理中ゾーンの定位置に置く(カートに戻さない)'])
check('③ PC SIM起票済み 期待配列', merged_actions('PC', 'SIM起票済み') == ['JP-OTS QuickLink(Wiki)を開く(下のリンク)', 'ページ内の PC 依頼テンプレートを開く', '機器ID・シリアル・症状を入力する', '起票する', '起票できたSIMのURLをこのツールの「SIM URL」欄に貼る', '「保存する」を押す'])
check('③ SSP 修理待ち 期待配列(v2.2 スキャン受付)', merged_actions('SSP', '修理待ち') == ['チェックシートに ✓ を書く', 'スキャン受付の PC で端末の QR を読む', 'FAULT の QR を読む(15秒以内)', '画面が緑になるのを確認する', '修理依頼品 BOX へ入れる'])
check('③ SSP 修理待ち fallback あり(v2.2)', GD['SSP']['step_extra']['修理待ち']['fallback']['title'] == 'スキャン受付が使えない時(SA が修理デーに登録)')

# ④ URL は https で始まる / url null は note を持つ
for n in ['GUIDE_URL_WIKI', 'GUIDE_URL_ZEBRA', 'GUIDE_URL_SLACK']: check(f'④ {n} https', C[n].startswith('https://'))
for t, u in C['SIM_TEMPLATES'].items(): check(f'④ SIM_TEMPLATES[{t}] https', u.startswith('https://'))
for t, g in GD.items():
    for l in g['links']:
        check(f'④ {t}.links[{l["label"][:12]}] url https or (null+note)', (l['url'] or '').startswith('https://') if l['url'] else bool(l.get('note')))

# ⑤ 識別子の不変条件: 既存が1回、新規が1回、旧名0
def defs(name): return len(re.findall(r'(?:^|\n)(?:const|let|function|window\.)\s*%s\b\s*(?:=|\()' % re.escape(name), src)) + \
                        len(re.findall(r'id="%s"' % re.escape(name), src))
for name in ['statusModal', 'openStatus', 'printManifest', 'LEGACY', 'FLOWS', 'SIM_TEMPLATES', 'simGuide']: check(f'⑤ 既存 {name} 定義1回', defs(name) == 1, defs(name))
NEW = ['GUIDE_DATA', 'GUIDE_STEP_BASE', 'GUIDE_ICONS', 'GUIDE_URL_WIKI', 'GUIDE_URL_ZEBRA', 'GUIDE_URL_SLACK', 'GUIDE_DEFAULT_FLOW', 'guideState',
       'guideSafeUrl', 'guideDeepLink', 'guideCopyUrl', 'guidePrint', 'guideLinksFor', 'guideRender', 'guideOpen', 'guideOpenFromStatus', 'guideReturnToStatus', 'guideStatusFading',
       'guideModal', 'guideTabs', 'guideBody', 'guideCopyBtn', 'guidePrintBtn']
for name in NEW: check(f'⑤ 新規 {name} 定義ちょうど1回', defs(name) == 1, defs(name))
for name in ['REPAIR_GUIDES', 'renderGuide', 'openGuide']: check(f'⑤ 旧名 {name} 0件', len(re.findall(r'\b%s\b' % name, src)) == 0)
check('⑤ openStatus の既定フローが GUIDE_DEFAULT_FLOW を参照', "const flow = (FLOWS[d.device_type] || GUIDE_DEFAULT_FLOW)" in src)
check('⑤ TYPE_LABEL に Other', C['TYPE_LABEL'].get('Other') == 'その他')
check('⑤ statusModal/guideModal は getOrCreateInstance(new で二重インスタンスを作らない)', "new bootstrap.Modal(document.getElementById('statusModal'))" not in src and "new bootstrap.Modal(document.getElementById('guideModal'))" not in src)
check('⑤ 速いタップ対策: フェードイン中は shown.bs.modal 後にやり直す', "if (guideStatusFading) { el.addEventListener('shown.bs.modal', () => window.guideOpenFromStatus(), { once: true }); return }" in src)

# ⑥ ガイド描画コード内に動的値を埋め込んだ inline onclick が無い / data-guide-type 委譲 / GUIDE_ICONS / guideSafeUrl
guide_js = src[src.index('// ─── 修理手順ガイド v2.1: 描画'):src.index('// ─── 起動')]
check('⑥ ガイド描画コードに onclick="...${...}" 無し', not re.search(r'onclick="[^"]*\$\{', guide_js))
check('⑥ data-guide-type 委譲', 'data-guide-type=' in guide_js and "closest('[data-guide-type]')" in guide_js)
check('⑥ アイコンは GUIDE_ICONS 対応表', 'GUIDE_ICONS[l.icon]' in guide_js)
hrefs = re.findall(r'href="\$\{([^}]*)\}"', guide_js)
check('⑥ ガイド内の全 href が esc(guideSafeUrl(..))', all(h.startswith('esc(guideSafeUrl(') for h in hrefs), str(hrefs))
check('⑥ guideSafeUrl は https 以外を # に', "return /^https:\\/\\//.test(String(u||'')) ? u : '#'" in guide_js)

# ⑦ モーダル数 6→7 / ⑧ 見出し A〜E がこの順で各1回
check('⑦ modal fade = 8(v2.2 で棚卸モーダル +1)', src.count('class="modal fade"') == 8, src.count('class="modal fade"'))
heads = ['A. 修理に出す前に試す', 'B. 修理フロー', 'C. 復帰チェック', 'D. リンク集', 'E. 発送の鉄則']
pos = [guide_js.find(h) for h in heads]
check('⑧ 見出し A〜E がこの順で各1回', all(p >= 0 for p in pos) and pos == sorted(pos) and all(guide_js.count(h) == 1 for h in heads), str(pos))

# 保全: 絶対ルール(PIN/Webhook をリポジトリに入れない・LEGACY 維持・Firebase 読み取りのみ)
check('保全 LEGACY マッピング維持', "const LEGACY = { '修理中':'修理待ち', 'Zebra登録済み':'RMA登録済み', '修理完了':'返却済み' }" in src)
# PIN の平文はこのテストファイルにも書かない(リポジトリは公開)。PIN 定数が hash+salt の2つだけで、'dej6-xxxxxxxx' 形の8文字トークン文字列が無いことを見る
check('保全 PIN は PIN_SALT/PIN_HASH のみ(平文トークン無し)', len(re.findall(r"const PIN_HASH = '[0-9a-f]{64}'", src)) == 1 and not re.search(r"['\"]dej6-[a-z0-9]{8}['\"]", src))
check('保全 ディープリンクは has(\'guide\')', "if (q.has('guide')) guideOpen(q.get('guide'), null)" in src)
check('ディープリンクは loadAll 完了後(finally)に開く', "loadAll().finally(() => { const q = new URL(location.href).searchParams; if (q.has('guide'))" in src)

print(f'\n{len(fails)} FAIL / {sum(1 for _ in [])}' if fails else '\nALL PASS')
print('summary:', 'FAIL ' + str(len(fails)) if fails else 'PASS', f'(checks run: see above)')
sys.exit(1 if fails else 0)
