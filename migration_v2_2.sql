-- ============================================================
-- DEJ6 IT機器管理 v2.2 マイグレーション(Supabase SQL Editor で1回実行。再実行しても安全)
--  1. devices.fault_count(故障回数)  2. repair_history.event(棚卸/スキャン受付の種別)
--  3. fs_lots(FS 発送ロット)+ RPC fs_ship / fs_unship  4. app_config 既定値
--  5. 旧 qr-app 同期分(fault_source='qr-app') を 'legacy' へ(sync.py が二度と触らない)
-- ============================================================

-- 1. 故障回数(修理待ちへ遷移するごとに +1。復帰してもクリアしない。初期値は scripts/import_qrapp.py で投入)
ALTER TABLE devices ADD COLUMN IF NOT EXISTS fault_count integer NOT NULL DEFAULT 0;

-- 2. 履歴の種別: hold_open / hold_close / unregistered_found / inventory_ok / scan_fault / scan_return(NULL=従来の状態変更)
ALTER TABLE repair_history ADD COLUMN IF NOT EXISTS event text;
CREATE INDEX IF NOT EXISTS idx_repair_history_event ON repair_history(event, created_at DESC);
-- 端末ごとの最新 hold_open / hold_close(保留判定。全件走査で取得上限の影響を受けない)
CREATE OR REPLACE VIEW v_hold_latest AS
  SELECT DISTINCT ON (device_id) device_id, event, created_at
  FROM repair_history
  WHERE event IN ('hold_open', 'hold_close')
  ORDER BY device_id, created_at DESC, id DESC;

-- 3. FS 発送ロット(FS は個体でなく台数で管理。稼働 = fs_total - fs_wait - Σ(qty-received) - Σ(received-ready))
CREATE TABLE IF NOT EXISTS fs_lots (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  shipped_at    date NOT NULL DEFAULT current_date,
  qty           integer NOT NULL CHECK (qty > 0),
  rma_numbers   text,
  received_at   date,
  received_qty  integer NOT NULL DEFAULT 0,
  ready_qty     integer NOT NULL DEFAULT 0,
  note          text,
  created_by    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fs_lots_qty_order CHECK (0 <= ready_qty AND ready_qty <= received_qty AND received_qty <= qty)
);
ALTER TABLE fs_lots DISABLE ROW LEVEL SECURITY;   -- 既存 devices / repair_history / app_config と同じ方針(anon key + アプリ側 PIN)

-- 発送: app_config.fs_wait(BOX 内の修理待ち台数) を p_qty 減らし、ロットを1件作る(1トランザクション。不足なら例外)
CREATE OR REPLACE FUNCTION fs_ship(p_qty integer, p_rma text, p_by text DEFAULT NULL)
RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE v_wait integer; v_id uuid;
BEGIN
  IF p_qty IS NULL OR p_qty <= 0 THEN RAISE EXCEPTION 'p_qty must be > 0'; END IF;
  SELECT COALESCE(NULLIF(value, '')::integer, 0) INTO v_wait FROM app_config WHERE key = 'fs_wait' FOR UPDATE;
  IF v_wait IS NULL THEN v_wait := 0; END IF;
  IF v_wait < p_qty THEN RAISE EXCEPTION 'fs_wait (%) < p_qty (%)', v_wait, p_qty; END IF;
  INSERT INTO app_config (key, value, updated_by, updated_at) VALUES ('fs_wait', (v_wait - p_qty)::text, p_by, now())
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at;
  INSERT INTO fs_lots (qty, rma_numbers, created_by) VALUES (p_qty, NULLIF(p_rma, ''), p_by) RETURNING id INTO v_id;
  RETURN v_id;
END $$;

-- 取消(受領前のみ): ロットを消し、台数を fs_wait へ戻す
CREATE OR REPLACE FUNCTION fs_unship(p_lot uuid)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_qty integer; v_rec integer; v_recat date;
BEGIN
  SELECT qty, received_qty, received_at INTO v_qty, v_rec, v_recat FROM fs_lots WHERE id = p_lot FOR UPDATE;
  IF v_qty IS NULL THEN RAISE EXCEPTION 'lot not found'; END IF;
  IF v_rec > 0 OR v_recat IS NOT NULL THEN RAISE EXCEPTION 'lot already received (received_qty=%, received_at=%)', v_rec, v_recat; END IF;
  DELETE FROM fs_lots WHERE id = p_lot;
  INSERT INTO app_config (key, value, updated_at) VALUES ('fs_wait', v_qty::text, now())
    ON CONFLICT (key) DO UPDATE SET value = (COALESCE(NULLIF(app_config.value, '')::integer, 0) + v_qty)::text, updated_at = now();
END $$;

-- BOX 内の修理待ち台数の更新(棚卸・FS パネル): BOX + 発送中 + 要設定 ≤ 総台数 を DB 側でも検証(稼働がマイナスになる値は保存しない)
CREATE OR REPLACE FUNCTION fs_set_wait(p_wait integer, p_by text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_total integer; v_open integer;
BEGIN
  IF p_wait IS NULL OR p_wait < 0 THEN RAISE EXCEPTION 'p_wait must be >= 0'; END IF;
  SELECT COALESCE(NULLIF(value, '')::integer, 0) INTO v_total FROM app_config WHERE key = 'fs_total';
  SELECT COALESCE(SUM((qty - received_qty) + (received_qty - ready_qty)), 0) INTO v_open FROM fs_lots;
  IF p_wait + v_open > COALESCE(v_total, 0) THEN RAISE EXCEPTION 'fs_wait (%) + open lots (%) > fs_total (%)', p_wait, v_open, v_total; END IF;
  INSERT INTO app_config (key, value, updated_by, updated_at) VALUES ('fs_wait', p_wait::text, p_by, now())
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at;
END $$;

-- ロットの受領・設定済み台数は減らせない / 発送台数は変えられない(誤入力の訂正は SA が SQL で行う。履歴消失を防ぐ)
CREATE OR REPLACE FUNCTION fs_lots_no_decrease() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.received_qty < OLD.received_qty OR NEW.ready_qty < OLD.ready_qty THEN
    RAISE EXCEPTION 'received_qty/ready_qty cannot decrease (lot %)', OLD.id;
  END IF;
  IF NEW.qty <> OLD.qty THEN RAISE EXCEPTION 'qty is immutable (lot %)', OLD.id; END IF;
  IF NEW.received_qty > 0 AND NEW.received_at IS NULL THEN NEW.received_at := current_date; END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_fs_lots_no_decrease ON fs_lots;
CREATE TRIGGER trg_fs_lots_no_decrease BEFORE UPDATE ON fs_lots FOR EACH ROW EXECUTE FUNCTION fs_lots_no_decrease();

-- 4. app_config 既定値(既にあるキーは触らない)
INSERT INTO app_config (key, value) VALUES
  ('stagnation_days',         '7'),
  ('stagnation_days_shipped', '14'),
  ('repair_days',             ''),
  ('repair_roster',           ''),
  ('fs_qty_mode',             '1'),
  ('fs_total',                '190'),
  ('fs_wait',                 '0'),
  ('scan_delim',              'Enter'),
  ('scan_fault',              'FAULT')
ON CONFLICT (key) DO NOTHING;
-- v2.1 の alert_threshold は撤去(index.html から参照を外した)
DELETE FROM app_config WHERE key = 'alert_threshold';

-- 5. 旧 qr-app 同期分を legacy 化(scripts/sync.py は fault_source='qr-app' の行だけを触るため、以後は触られない)
UPDATE devices SET fault_source = 'legacy' WHERE fault_source = 'qr-app';

-- 確認(実行後に目で見る)
-- SELECT count(*) FILTER (WHERE fault_source='legacy') AS legacy, count(*) FILTER (WHERE fault_source='qr-app') AS qrapp_should_be_0 FROM devices;
-- SELECT key, value FROM app_config WHERE key IN ('fs_qty_mode','fs_total','fs_wait','scan_delim','scan_fault','stagnation_days','stagnation_days_shipped') ORDER BY key;
