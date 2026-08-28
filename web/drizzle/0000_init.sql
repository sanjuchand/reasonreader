CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  google_sub text NOT NULL UNIQUE,
  email text NOT NULL,
  name text NOT NULL DEFAULT '',
  avatar_url text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS copies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind text NOT NULL CHECK (kind IN ('demo', 'private')),
  owner_id uuid REFERENCES users(id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT '',
  author text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'uploading'
    CHECK (status IN ('uploading', 'ingesting', 'ready', 'failed')),
  flavor text,
  source_content_type text,
  source_filename text,
  rights_attested_at timestamptz,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (kind = 'demo' AND owner_id IS NULL) OR
    (kind = 'private' AND owner_id IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS copies_one_demo ON copies ((kind)) WHERE kind = 'demo';

INSERT INTO copies (
  id, kind, owner_id, title, author, status, flavor, source_content_type
) VALUES (
  'a0000000-0000-4000-8000-000000000001',
  'demo',
  NULL,
  'An Inquiry into the Nature and Causes of the Wealth of Nations',
  'Adam Smith',
  'uploading',
  'smith',
  'text/html'
) ON CONFLICT (id) DO NOTHING;

DROP TABLE IF EXISTS user_threads;
CREATE TABLE user_threads (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  copy_id uuid NOT NULL REFERENCES copies(id) ON DELETE CASCADE,
  langgraph_thread_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, copy_id)
);

DROP TABLE IF EXISTS unit_progress;
CREATE TABLE unit_progress (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  copy_id uuid NOT NULL REFERENCES copies(id) ON DELETE CASCADE,
  unit_id text NOT NULL,
  status text NOT NULL DEFAULT 'locked',
  score double precision NOT NULL DEFAULT 0,
  unlocked boolean NOT NULL DEFAULT false,
  concepts jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, copy_id, unit_id)
);
