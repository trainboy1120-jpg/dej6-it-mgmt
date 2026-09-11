"""index.html への移植前チェック: 新規識別子が現行 index.html に 0 件であることを単語境界一致で数える。
使い方: py docs/mockup/check_identifiers.py [index.html のパス]   終了コード 0=衝突なし / 1=衝突あり"""
import re, sys, pathlib
NEW_IDS = ['GUIDE_DATA','GUIDE_STEP_BASE','GUIDE_ICONS','GUIDE_URL_WIKI','GUIDE_URL_ZEBRA','GUIDE_URL_SLACK','GUIDE_DEFAULT_FLOW','guideState',
           'guideSafeUrl','guideDeepLink','guideCopyUrl','guidePrint','guideLinksFor','guideRender','guideOpen',
           'guideModal','guideTabs','guideBody','guideCopyBtn','guidePrintBtn']
OLD_IDS = ['REPAIR_GUIDES','renderGuide','openGuide']   # 改名前の名前。0 件であること
root = pathlib.Path(__file__).resolve().parents[2]
path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'index.html'
raw = path.read_bytes()                      # サイズ・ハッシュは実バイト列で取る(文字数ではない)
src = raw.decode('utf-8')
bad = 0
import hashlib
print(f'target: {path} ({len(raw)} bytes, sha1 {hashlib.sha1(raw).hexdigest()})')
for name in NEW_IDS + OLD_IDS:
    n = len(re.findall(r'\b' + re.escape(name) + r'\b', src))
    print(f'  {name:20s} {n}')
    bad += n
print('RESULT:', 'OK (0 collisions)' if bad == 0 else f'COLLISION ({bad})')
sys.exit(0 if bad == 0 else 1)
