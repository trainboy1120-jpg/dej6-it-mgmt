#!/usr/bin/env python3
"""qr-app snapshot(qrapp-capture/snapshot_*.json) の qr_fault_counts を devices.fault_count へ投入する(1回限り)。
使い方:
  py scripts/import_qrapp.py                 # dry-run(既定): 何を PATCH するかを表示するだけ
  py scripts/import_qrapp.py --apply         # 実際に PATCH(device_id ごとに 1 リクエスト)
  py scripts/import_qrapp.py --snapshot PATH # snapshot を明示(既定: ../dej6-itpoc-restart/qrapp-capture/snapshot_*.json の最新)
環境変数 SUPABASE_URL / SUPABASE_KEY(未設定なら index.html と同じ公開 anon 設定を scripts/sync.py から借りる)。
安全設計: 読み取り1回+差分のある行だけ PATCH。fault_count が既に snapshot 以上の行は触らない(再実行しても増えない)。
"""
import argparse, glob, json, os, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sync as S   # SB_URL / SB_KEY / http / sb_headers を流用(Firebase には触らない)

def load_snapshot(path):
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    fc = snap.get("qr_fault_counts") or {}
    out = {}
    for k, v in fc.items():
        m = re.fullmatch(r"(?:SSP-)?(\d{1,3})", str(k))
        n = int(v) if isinstance(v, int) else int((v or {}).get("count", 0) or 0)
        if not m or n <= 0:
            continue
        out["SSP-" + m.group(1).zfill(3)] = n
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--snapshot", default=None)
    a = ap.parse_args()
    path = a.snapshot
    if not path:
        cands = sorted(glob.glob(os.path.join(HERE, "..", "..", "dej6-itpoc-restart", "qrapp-capture", "snapshot_*.json")))
        if not cands:
            print("snapshot が見つかりません(--snapshot で指定)"); return 2
        path = cands[-1]
    want = load_snapshot(path)
    print(f"snapshot: {path}  fault_counts: {len(want)} 台 / {sum(want.values())} 回")
    devices = S.http("GET", S.SB_URL + "/rest/v1/devices?select=device_id,fault_count&device_id=like.SSP-*", headers=S.sb_headers())
    cur = {d["device_id"]: int(d.get("fault_count") or 0) for d in devices}
    todo = {k: v for k, v in want.items() if k in cur and cur[k] < v}
    missing = [k for k in want if k not in cur]
    print(f"devices(SSP): {len(cur)} 台 / 更新対象 {len(todo)} 台 / マスタに無い {len(missing)} 台 {missing[:10]}")
    for k in sorted(todo):
        print(f"  {k}: {cur[k]} -> {todo[k]}")
    if not a.apply:
        print("dry-run(--apply で実行)"); return 0
    for k, v in sorted(todo.items()):
        S.http("PATCH", S.SB_URL + "/rest/v1/devices?device_id=eq." + urllib.parse.quote(k), body={"fault_count": v},
               headers=S.sb_headers("return=minimal"))
    print(f"PATCH 完了: {len(todo)} 台")
    return 0

if __name__ == "__main__":
    sys.exit(main())
