#!/usr/bin/env python3
"""
DEJ6 IT機器管理 v2 — qr-app(Firebase) → Supabase 自動同期
@author sakrhiro (built with Aki)

30分毎にGitHub Actionsから実行される。
 1. qr-app(Firebase)のSSP故障登録(broken)を検知 → Supabaseの該当SSPを「修理待ち」へ
 2. qr-appで故障解除(available/rented)されたら、自動登録分(fault_source='qr-app')のみ「正常」へ戻す
 3. このアクセス自体がSupabase無料プランのkeep-aliveになる(一時停止の根治)

安全設計(safe-tool-building準拠):
 - 読み取りは各1リクエスト、書き込みは差分があった時だけ最小回数
 - HTTPエラー時は即停止(リトライ暴走なし)
 - --dry-run で書き込みなし確認が可能
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

FB_URL = "https://ssp-rental-default-rtdb.asia-southeast1.firebasedatabase.app"
SB_URL = os.environ.get("SUPABASE_URL", "https://tetigwcotdqgkwfswbyc.supabase.co")
SB_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRldGlnd2NvdGRxZ2t3ZnN3YnljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEyNzQxNDgsImV4cCI6MjA5Njg1MDE0OH0.8akyRPHCOX3wfKdIqvoaJdq2D8i--Z1jBLS2RLJOuaQ")
DRY_RUN = "--dry-run" in sys.argv
TIMEOUT = 30


def http(method, url, body=None, headers=None):
    """単発HTTPリクエスト。失敗は例外で即停止(リトライしない)。"""
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=TIMEOUT) as res:
        raw = res.read().decode()
        return json.loads(raw) if raw else None


def sb_headers(prefer=None):
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
    if prefer:
        h["Prefer"] = prefer
    return h


def main():
    # 1. qr-app 現況取得
    fb = http("GET", f"{FB_URL}/qr_items.json") or {}
    broken_keys = {k for k, v in fb.items() if v and v.get("status") == "broken"}
    print(f"[fb] items={len(fb)} broken={sorted(broken_keys)}")

    # 2. Supabase SSP現況取得 (このGETがkeep-aliveを兼ねる)
    try:
        devices = http(
            "GET",
            f"{SB_URL}/rest/v1/devices?device_type=eq.SSP&select=device_id,status,fault_source",
            headers=sb_headers(),
        )
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print("[error] fault_source列が見つかりません。先に migration_v2.sql を実行してください", file=sys.stderr)
            sys.exit(1)
        raise
    print(f"[sb] SSP devices={len(devices)}")

    to_repair = []   # 正常 → 修理待ち (qr-appでbroken)
    to_normal = []   # 修理待ち(qr-app起因) → 正常 (qr-appで解除)
    for d in devices:
        did = d["device_id"]
        if not did.startswith("SSP-"):
            continue
        key = did.replace("SSP-", "").zfill(3)
        if key in broken_keys and d["status"] == "正常":
            to_repair.append(did)
        elif key not in broken_keys and d["status"] == "修理待ち" and d.get("fault_source") == "qr-app":
            to_normal.append(did)

    print(f"[plan] to_repair={to_repair} to_normal={to_normal}")
    if DRY_RUN:
        print("[dry-run] 書き込みなしで終了")
        return

    now = datetime.now(timezone.utc).isoformat()
    if to_repair:
        ids = ",".join(f'"{i}"' for i in to_repair)
        http(
            "PATCH",
            f"{SB_URL}/rest/v1/devices?device_id=in.({ids})",
            body={"status": "修理待ち", "fault_source": "qr-app", "status_changed_at": now},
            headers=sb_headers("return=minimal"),
        )
        http(
            "POST",
            f"{SB_URL}/rest/v1/repair_history",
            body=[
                {"device_id": i, "from_status": "正常", "to_status": "修理待ち",
                 "handler": "auto-sync", "note": "qr-app故障登録を自動検知"}
                for i in to_repair
            ],
            headers=sb_headers("return=minimal"),
        )
        print(f"[done] {len(to_repair)}台を修理待ちへ")

    if to_normal:
        ids = ",".join(f'"{i}"' for i in to_normal)
        http(
            "PATCH",
            f"{SB_URL}/rest/v1/devices?device_id=in.({ids})",
            body={"status": "正常", "fault_source": None, "status_changed_at": now,
                  "defect_category": None, "defect_detail": None},
            headers=sb_headers("return=minimal"),
        )
        http(
            "POST",
            f"{SB_URL}/rest/v1/repair_history",
            body=[
                {"device_id": i, "from_status": "修理待ち", "to_status": "正常",
                 "handler": "auto-sync", "note": "qr-app故障解除を自動検知"}
                for i in to_normal
            ],
            headers=sb_headers("return=minimal"),
        )
        print(f"[done] {len(to_normal)}台を正常へ")

    if not to_repair and not to_normal:
        print("[done] 差分なし (keep-aliveのみ)")


if __name__ == "__main__":
    main()
