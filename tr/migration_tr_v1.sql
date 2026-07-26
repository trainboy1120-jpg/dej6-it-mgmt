-- TR進捗管理 v1 マイグレーション (DEJ6)
-- 実行場所: https://supabase.com/dashboard/project/tetigwcotdqgkwfswbyc/sql/new (Role: postgres)
-- @author sakrhiro
BEGIN;

CREATE TABLE IF NOT EXISTS tr_trainees (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  alias text NOT NULL UNIQUE,
  trainer_alias text NOT NULL,
  start_date date,
  goal text,
  active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tr_items (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  block text NOT NULL,
  name text NOT NULL,
  sort int NOT NULL DEFAULT 0,
  active boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS tr_ratings (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trainee_id bigint NOT NULL REFERENCES tr_trainees(id) ON DELETE CASCADE,
  item_id bigint NOT NULL REFERENCES tr_items(id) ON DELETE CASCADE,
  rater text NOT NULL CHECK (rater IN ('trainer','trainee')),
  score int NOT NULL CHECK (score BETWEEN 1 AND 3),
  note text,
  updated_at timestamptz DEFAULT now(),
  UNIQUE (trainee_id, item_id, rater)
);

CREATE TABLE IF NOT EXISTS tr_weekly (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trainee_id bigint NOT NULL REFERENCES tr_trainees(id) ON DELETE CASCADE,
  week_no int NOT NULL,
  trainer_pct numeric,
  trainee_pct numeric,
  target_label text,
  memo text,
  created_at timestamptz DEFAULT now(),
  UNIQUE (trainee_id, week_no)
);

-- 権限 (確定パターン: GRANT USAGE ON SCHEMA → GRANT CRUD → RLSポリシー)
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON tr_trainees, tr_items, tr_ratings, tr_weekly TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon;

ALTER TABLE tr_trainees ENABLE ROW LEVEL SECURITY;
ALTER TABLE tr_items    ENABLE ROW LEVEL SECURITY;
ALTER TABLE tr_ratings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE tr_weekly   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tr_trainees_anon ON tr_trainees;
DROP POLICY IF EXISTS tr_items_anon    ON tr_items;
DROP POLICY IF EXISTS tr_ratings_anon  ON tr_ratings;
DROP POLICY IF EXISTS tr_weekly_anon   ON tr_weekly;
CREATE POLICY tr_trainees_anon ON tr_trainees FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY tr_items_anon    ON tr_items    FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY tr_ratings_anon  ON tr_ratings  FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY tr_weekly_anon   ON tr_weekly   FOR ALL TO anon USING (true) WITH CHECK (true);

-- 項目マスタ シード (SA日勤 57項目・2026-07-26時点のCDP最新版)
INSERT INTO tr_items (block, name, sort) VALUES
('①ブロック', '情報共有master sheetの確認 (L3情報共有タブの確認)', 10),
('①ブロック', 'Cycle2・3・4・誘導の配置表印刷', 20),
('①ブロック', 'SWCL- シフトアシスタント/RTS・当日 (PFSD) 「容積プランニング」「経路プランニング」「ソート前のセットアップ」「仕分け」の項目をチェック', 30),
('①ブロック', 'SUM準備 ※SUM資料の共有事項更新', 40),
('①ブロック', 'Induction準備', 50),
('①ブロック', '進捗管理ファイルの作成/共有', 60),
('②ブロック', 'SUM資料更新', 70),
('②ブロック', '出勤未確認AAを配置表に反映しFCLM登録', 80),
('②ブロック', '青ランプマンの起動/PC', 90),
('②ブロック', '出勤状況をValidationファイルに入力。日勤AreaManagerに報告', 100),
('②ブロック', 'Aging捜索（assign）', 110),
('②ブロック', 'RB回送便チェック・更新', 120),
('③ブロック', 'CXルートで残っているルートがないかSTG.A～Hを見回り', 130),
('③ブロック', 'IND残り残数の下流への共有', 140),
('③ブロック', '流し漏れ確認/sort終了確認/chimeルームに時間報告', 150),
('③ブロック', 'PTK5幹線リスト印刷', 160),
('③ブロック', 'Flow ControlのFileを格納', 170),
('③ブロック', 'SSP Compliance 配信 C2', 180),
('④ブロック', 'AMZL処理/手書き対応', 190),
('④ブロック', '看板チェックリスト印刷', 200),
('④ブロック', '誘導のFCLM登録', 210),
('④ブロック', 'ディスパッチ状況確認 15:00/15:30/16:00 も実施する', 220),
('④ブロック', 'PTK5最終幹線確認(アイル積み残し確認含む)', 230),
('⑤ブロック', 'Hub切り離し最終確認', 240),
('⑤ブロック', 'Cycle3開始/FCLM登録', 250),
('⑤ブロック', 'C2 P&S 積漏れ、ステージング漏れ確認、ステージング場所確認', 260),
('⑤ブロック', 'Aging捜索 進捗確認(捜索漏れ無いように)', 270),
('⑤ブロック', '要注意変更（HUB,PTK5どちらも処理の上連絡願います）', 280),
('⑤ブロック', 'RTS締切・確認、BCのステータス確認', 290),
('⑥ブロック', 'キャリブレーション・SidelineのStowのアサイン', 300),
('⑥ブロック', 'SSPコンプライアンス配信 C3', 310),
('⑥ブロック', 'C3 P&S積漏れ、ステージング漏れ確認、ステージング場所確認', 320),
('⑥ブロック', 'Off task修正', 330),
('⑥ブロック', 'インファード修正', 340),
('⑥ブロック', 'Safety Observation実施', 350),
('⑦ブロック', '生産性ランキング データ取得・貼り付け', 360),
('⑦ブロック', 'SWCL- 「発送」「オンロードモニタリング」「PFSDシフトの終了」「RTSの全項目」の項目をチェック', 370),
('⑦ブロック', 'GCA確認（対応漏れや、ステータス更新漏れがないか）', 380),
('⑦ブロック', 'FC返送FASHIONのクローズ（毎週火曜日・日曜日）対応者：アンバサダー', 390),
('⑦ブロック', '日時変更処理', 400),
('⑧ブロック', '翌日日勤分の配置表作成', 410),
('⑧ブロック', '毎週日曜日 Bag棚卸し作業あり', 420),
('⑧ブロック', '備品発注・在庫確認 ※ゼブラプリンターのロール/リパック資材の在庫状況も確認する', 430),
('⑧ブロック', 'Validation file更新(退勤状況をValidationファイルに入力、タイムシートと出退勤実績を精査)', 440),
('⑧ブロック', '幹線check out確認と遅延報告', 450),
('⑨ブロック', 'C2 Cap調整', 460),
('⑨ブロック', 'Milkrun Sheet作成・HDP担当AAに印刷してお渡し', 470),
('⑨ブロック', 'Saroute用のMilkrun Sheet作成・MRルートの差し込み先の決定', 480),
('時間指定なし', 'GCA(F2Fアラート)の対応漏れ、ステータス更新漏れをチェック / Process Training未受講対象者の抽出と受講依頼', 490),
('時間指定なし', '本日自分担当のEngage 1on1 実施者の確認', 500),
('時間指定なし', 'Engage 1on1 進める(日勤は1日1人目標)', 510),
('時間指定なし', 'AEDチェック(詰所とDock近くのAED2か所にチェック入れる)', 520),
('時間指定なし', 'PTK5 クラスタートランスファー依頼', 530),
('時間指定なし', 'ヒヤリハット→ドラゴンフライAtoZからの投稿に変更', 540),
('曜日指定', 'HUB定例ミーティング', 550),
('曜日指定', 'Aging全流しするためのデータ処理', 560),
('曜日指定', '前日分Mytime修正(ルーチン表10:10にも記載)', 570);

COMMIT;
