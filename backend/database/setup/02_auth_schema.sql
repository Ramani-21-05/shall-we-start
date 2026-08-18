-- ============================================================
-- PharmaCast User Authentication & RBAC Schema
-- Roles: 'ADMIN', 'STAFF', 'MARKETING'
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('ADMIN', 'STAFF', 'MARKETING')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed initial demo accounts
INSERT INTO users (email, username, hashed_password, full_name, role)
VALUES
  ('727823tuad122@skct.edu.in', 'ranjeet', '$2b$12$eImiTXuWVxfM37uY4JANjO20XpT2.XNnO1d4x2z4q7g7q7g7q7g7q', 'ranjeet c', 'ADMIN'),
  ('admin@pharmacast.com', 'admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'System Administrator', 'ADMIN'),
  ('staff@pharmacast.com', 'staff', '1b059f8174f885e3d74c0f86538479e000d0755582f05259926b484439f041ff', 'Pharmacy Staff Member', 'STAFF'),
  ('marketing@pharmacast.com', 'marketing', 'ef8f8c9b3a3cfc684693a201c107f9c89e1b212f8a1e2f465c40461cbca5e0d4', 'Marketing & Sales Strategist', 'MARKETING')
ON CONFLICT (username) DO NOTHING;

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read users" ON users;
CREATE POLICY "Allow public read/write users" ON users FOR ALL USING (true) WITH CHECK (true);
