"""静的+動的テストを順に実行(各 300 秒タイムアウト)。要約のみ出力。rc=0 で全PASS"""
import subprocess, sys, pathlib, os
env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}   # 呼び出し元の環境に依らず子プロセスは UTF-8 出力
here = pathlib.Path(__file__).resolve().parent; rc = 0
for t in ['test_repair_guide.py', 'test_repair_guide_e2e.py', 'test_v22.py', 'test_v22_e2e.py']:
    try:
        r = subprocess.run([sys.executable, str(here / t)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, env=env)
        lines = [l for l in r.stdout.splitlines() if not l.startswith('PASS')]
        print(f'[{t}] rc={r.returncode} passes={sum(1 for l in r.stdout.splitlines() if l.startswith("PASS"))}', ' | '.join(lines[-6:]), (r.stderr.strip()[-300:] if r.returncode else ''))
        rc |= r.returncode
    except subprocess.TimeoutExpired:
        print(f'[{t}] TIMEOUT'); rc = 1
sys.exit(rc)
