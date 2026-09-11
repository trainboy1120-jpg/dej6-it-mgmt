"""1行1操作チェック: repair_guides.js の actions / fallback.actions の各行が単一操作か検査する。
規則: 括弧内 ( ) （ ） を除いた本文に「して」「し、」「し「」「、」「て(末尾以外)」を含まない。
使い方: py docs/mockup/check_one_action.py [repair_guides.js]   終了コード 0=違反なし / 1=違反あり / 2=自己テスト失敗またはシングルクォート以外のリテラルを検出(検査不能)"""
import re, sys, pathlib

RULE = re.compile(r"して|し、|し「|、|て(?!$)")          # 「〜て+次の操作」は末尾以外の「て」で検出
def strip_parens(s: str) -> str:
    return re.sub(r"\([^)]*\)|（[^）]*）", "", s)
def violates(line: str) -> bool:
    return bool(RULE.search(strip_parens(line)))

# ── 自己テスト(ネガティブ/ポジティブ) ─────────────────
MUST_FAIL = ["依頼文を貼り付けて起票する", "発送する機器を一覧でまとめて選択する", "#dej6-it-poc に貼り付けて投稿する",
             "不具合カテゴリーを選び、症状を入力する", "このツールで機器をタップし「返却済み」を押す", "内容を確認して送信する"]
MUST_PASS = ["依頼文を貼り付ける", "起票する", "台数を Manifest / RMA と照合する", "機器ID・シリアル・症状を入力する",
             "SIMテンプレートを開く(下のリンク)", "「今日やること」の SIM起票 を押す(依頼文が自動生成される)", "箱を開ける"]
bad_self = [l for l in MUST_FAIL if not violates(l)] + [l for l in MUST_PASS if violates(l)]
if bad_self:
    print("SELF-TEST FAILED:", bad_self); sys.exit(2)

# ── 本体: actions / fallback.actions を抽出して検査 ───────
root = pathlib.Path(__file__).resolve().parent
path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / "repair_guides.js"
src = path.read_text(encoding="utf-8")
items = []
for m in re.finditer(r"actions:\s*\[(.*?)\]", src, re.S):   # step_extra.actions / fallback.actions / GUIDE_STEP_BASE.actions
    body = m.group(1)
    items += re.findall(r"'([^']*)'", body)
    # シングルクォート文字列以外(ダブルクォート・バッククォート・変数・スプレッド等)が残っていたら黙って通さず rc=2
    rest = re.sub(r"'[^']*'", "", body)
    rest = re.sub(r"[\s,]", "", rest)
    if rest:
        print("UNSUPPORTED LITERAL in actions array (only '...' strings are checked):", rest[:80]); sys.exit(2)
viol = [i for i in items if violates(i)]
print(f"self-test OK ({len(MUST_FAIL)} must-fail / {len(MUST_PASS)} must-pass); checked {len(items)} action lines; violations: {len(viol)}")
for v in viol: print("  x", v)
sys.exit(1 if viol else 0)
