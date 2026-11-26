-- Shared helper chat on invicta.arcanedrift.net
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,            -- ms since epoch
  name TEXT NOT NULL,
  text TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'chat',  -- chat | proposal
  link TEXT,
  ip TEXT,                        -- hashed visitor address, for rate limits only
  hidden INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS messages_ip_ts ON messages (ip, ts);
CREATE TABLE IF NOT EXISTS presence (
  client TEXT PRIMARY KEY,
  name TEXT,
  seen INTEGER NOT NULL
);
