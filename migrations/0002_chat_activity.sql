-- Team activity: each request Jordan and Kylee send to the site's Claude chat.
-- The site also creates this table by itself on first use (functions/_lib/activity.js).
CREATE TABLE IF NOT EXISTS chat_activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  updated INTEGER NOT NULL,
  who TEXT NOT NULL,
  ask TEXT NOT NULL,
  place TEXT,
  state TEXT NOT NULL,
  progress TEXT,
  reply TEXT,
  links TEXT
);
