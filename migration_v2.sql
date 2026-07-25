-- ============================================================
-- DEJ6 IT機器管理システム v2.0 マイグレーションSQL
-- 実行方法: https://supabase.com/dashboard/project/tetigwcotdqgkwfswbyc/sql/new
--           に全文貼り付け → RUN (Role: postgres)
-- 作成: 2026-07-25 by sakrhiro / Aki
-- ============================================================

BEGIN;

-- ── 1. 新カラム追加 ─────────────────────────────────────────
-- fault_source: 故障登録の発生源 ('qr-app'=自動同期 / 'manual'=手動)
-- status_changed_at: ステータス最終変更日時 (滞留日数の計算基準)
ALTER TABLE devices ADD COLUMN IF NOT EXISTS fault_source TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ DEFAULT NOW();

-- ── 2. アプリ設定テーブル (宛先マスタ等を全員で共有) ─────────
CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_by TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE app_config DISABLE ROW LEVEL SECURITY;

INSERT INTO app_config (key, value) VALUES
  ('addr_zebra',  E'Zebra社 修理センター\n※Zebra Direct RMA SOPの送付先住所を設定画面から登録してください'),
  ('addr_tyo4',   E'〒198-0025\n東京都青梅市末広町2-9-14 ランドポート青梅Ⅲ\nアマゾン青梅FC IT担当者 宛\nTEL: 042-827-0244'),
  ('addr_return', E'DEJ6 (返送先)\n※設定画面からDEJ6の住所・宛名を登録してください'),
  ('stagnation_days', '14'),
  ('alert_threshold', '10')
ON CONFLICT (key) DO NOTHING;

-- ── 3. 旧ステータス名の正規化 ───────────────────────────────
UPDATE devices SET status = '修理待ち'   WHERE status = '修理中';
UPDATE devices SET status = 'RMA登録済み' WHERE status = 'Zebra登録済み';
UPDATE devices SET status = '返却済み'   WHERE status = '修理完了';

-- ── 4. 凍結データの棚卸しリセット ───────────────────────────
-- 6/17以降更新が止まっており「修理待ち(旧:修理中)」112台の大半は実際には修理済み。
-- 全台いったん「正常」に戻し、履歴に理由を記録する。
-- 実際に修理中の機器は、リセット後にv2の一括操作で再登録する
-- (qr-app故障登録分は30分毎の自動同期が勝手に「修理待ち」へ戻す)。
INSERT INTO repair_history (device_id, from_status, to_status, handler, note)
SELECT device_id, status, '正常', 'v2-migration',
       'v2移行時の棚卸しリセット(6/17以降の凍結データを初期化)'
FROM devices WHERE status <> '正常';

UPDATE devices SET
  status = '正常',
  fault_source = NULL,
  status_changed_at = NOW(),
  zebra_rma = NULL,
  defect_category = NULL,
  defect_detail = NULL,
  shipping_date = NULL,
  tracking_number = NULL,
  return_date = NULL
WHERE status <> '正常';

-- ── 5. インデックス ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_devices_status_changed ON devices(status_changed_at);

COMMIT;

-- 実行後の確認クエリ (すべて0件・479台正常ならOK):
-- SELECT status, count(*) FROM devices GROUP BY status;
-- SELECT * FROM app_config;
