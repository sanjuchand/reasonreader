CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  google_sub text NOT NULL UNIQUE,
  email text NOT NULL,
  name text NOT NULL DEFAULT '',
  avatar_url text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_threads (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  langgraph_thread_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unit_progress (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  unit_id text NOT NULL,
  status text NOT NULL DEFAULT 'locked',
  score double precision NOT NULL DEFAULT 0,
  unlocked boolean NOT NULL DEFAULT false,
  concepts jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, unit_id)
);
