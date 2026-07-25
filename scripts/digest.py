#!/usr/bin/env python3
"""
DEJ6 IT機器管理 v2 — 毎朝8:00(JST) Slackダイジェスト
@author sakrhiro (built with Aki)

GitHub Actions (cron 23:00 UTC) から実行。
 - 修理パイプライン全体のサマリー (修理待ち/SIM済/RMA済/発送中/要設定)
 - qr-app実測の故障台数との突合 (乖離チェック — Senmyo-san指摘対応)
 - 滞留アラート (閾値日数を超えて同一ステータスに留まる機器)
 - 修理待ち台数の閾値超過アラート

ガード:
 - データ取得失敗時は投稿せず異常終了 (誤った0件投稿の防止)
 - SLACK_WEBHOOK_URL 未設定なら投稿スキップ (ログのみ)
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
WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
APP_URL = "https://trainboy1120-jpg.github.io/dej6-it-mgmt/"
TIMEOUT = 30

PIPELINE = ["修理待ち", "SIM起票済み", "RMA登録済み", "発送済み", "返却済み"]


def http(method, url, body=None, headers=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=TIMEOUT) as res:
        raw = res.read().decode()
        return json.loads(raw) if raw else None


def sb_get(path):
    return http("GET", f"{SB_URL}/rest/v1/{path}",
                headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"})


def main():
    # ── データ取得 (失敗したら投稿せず落ちる) ──
    try:
        devices = sb_get("devices?select=device_id,device_type,status,status_changed_at,defect_category,ops_handler")
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print("[error] status_changed_at列が見つかりません。先に migration_v2.sql を実行してください", file=sys.stderr)
            sys.exit(1)
        raise
    if not isinstance(devices, list) or not devices:
        print("[error] devices取得失敗 — 投稿中止", file=sys.stderr)
        sys.exit(1)

    try:
        cfg_rows = sb_get("app_config?select=key,value")
    except Exception:
        cfg_rows = []  # app_config未作成でもデフォルト値で動く
    cfg = {r["key"]: r["value"] for r in (cfg_rows or [])}
    stag_days = int(cfg.get("stagnation_days", "14"))
    threshold = int(cfg.get("alert_threshold", "10"))

    fb = http("GET", f"{FB_URL}/qr_items.json") or {}
    fb_broken = sum(1 for v in fb.values() if v and v.get("status") == "broken")

    # ── 集計 ──
    now = datetime.now(timezone.utc)
    counts = {s: [] for s in PIPELINE}
    stagnant = []
    for d in devices:
        st = d["status"]
        if st in counts:
            counts[st].append(d)
            ts = d.get("status_changed_at")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    days = (now - dt).days
                    if days >= stag_days:
                        stagnant.append((d["device_id"], st, days))
                except ValueError:
                    pass

    n_wait = len(counts["修理待ち"])
    total_pipeline = sum(len(v) for v in counts.values())

    # SSPの「修理待ち以降」台数 (箱の中+発送中) と qr-app brokenの突合
    ssp_in_flow = sum(1 for s in PIPELINE for d in counts[s] if d["device_type"] == "SSP")

    # ── メッセージ組み立て ──
    lines = [f":clipboard: *DEJ6 IT機器 朝のダイジェスト* ({now.astimezone().strftime('%m/%d')})"]
    if total_pipeline == 0:
        lines.append("修理パイプラインは空です。全機器正常 :tada:")
    else:
        seg = " / ".join(f"{s}: *{len(counts[s])}*" for s in PIPELINE if counts[s])
        lines.append(seg)
        # 修理待ちの内訳 (種別ごと)
        if n_wait:
            by_type = {}
            for d in counts["修理待ち"]:
                by_type.setdefault(d["device_type"], []).append(d["device_id"])
            det = " ".join(f"{t}×{len(ids)}" for t, ids in sorted(by_type.items()))
            lines.append(f":wrench: 修理待ち内訳: {det}")
        if counts["返却済み"]:
            ids = " ".join(d["device_id"] for d in counts["返却済み"][:10])
            lines.append(f":package: 要設定(返却済み): {ids}")

    lines.append(f":mag: qr-app実測の故障SSP: *{fb_broken}台* / ツール上のSSP修理フロー: {ssp_in_flow}台"
                 + ("" if fb_broken == sum(1 for d in counts['修理待ち'] if d['device_type']=='SSP') else " (差分は同期30分待ち or フロー進行中)"))

    if n_wait >= threshold:
        lines.append(f":rotating_light: *修理待ちが閾値({threshold}台)を超えています: {n_wait}台* — 発送対応をご検討ください")

    if stagnant:
        stagnant.sort(key=lambda x: -x[2])
        det = ", ".join(f"{i}({s} {d}日)" for i, s, d in stagnant[:8])
        lines.append(f":hourglass: 滞留{stag_days}日超え: {det}")

    lines.append(f"<{APP_URL}|管理ツールを開く>")
    msg = "\n".join(lines)
    print(msg)

    # ── 投稿 ──
    if not WEBHOOK:
        print("[skip] SLACK_WEBHOOK_URL未設定のため投稿スキップ")
        return
    http("POST", WEBHOOK, body={"text": msg})
    print("[done] Slack投稿完了")


if __name__ == "__main__":
    main()
