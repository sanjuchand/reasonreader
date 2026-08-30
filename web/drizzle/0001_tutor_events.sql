CREATE TABLE IF NOT EXISTS tutor_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  copy_id uuid NOT NULL REFERENCES copies(id) ON DELETE CASCADE,
  thread_id text,
  unit_id text,
  kind text NOT NULL,
  concept text,
  score text,
  recitation boolean,
  overall double precision,
  attempt integer,
  answer_chars integer,
  answer_clip text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tutor_events_user_copy_unit
  ON tutor_events (user_id, copy_id, unit_id, created_at);

CREATE INDEX IF NOT EXISTS tutor_events_thread
  ON tutor_events (thread_id, created_at);
