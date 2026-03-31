-- =============================================
-- VIRA BOT - CANONICAL DATABASE SCHEMA
-- Runtime service layer is the source of truth.
-- This script is additive, idempotent, and migration-friendly.
-- =============================================

-- =============================================
-- 1. USERS
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    lang TEXT DEFAULT 'tr',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'tr';
ALTER TABLE users ADD COLUMN IF NOT EXISTS state TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS state_data JSONB;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_model TEXT DEFAULT 'deepseek';
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- =============================================
-- 2. USER STATES
-- =============================================
CREATE TABLE IF NOT EXISTS user_states (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    state_name TEXT NOT NULL,
    state_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_states ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE user_states ADD COLUMN IF NOT EXISTS state_name TEXT;
ALTER TABLE user_states ADD COLUMN IF NOT EXISTS state_data JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE user_states ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE user_states ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_states_user_id ON user_states(user_id);
CREATE INDEX IF NOT EXISTS idx_user_states_name ON user_states(state_name);

INSERT INTO user_states (user_id, state_name, state_data)
SELECT
    user_id,
    state,
    COALESCE(state_data, '{}'::jsonb)
FROM users
WHERE state IS NOT NULL
ON CONFLICT (user_id) DO NOTHING;

-- =============================================
-- 3. NOTES
-- =============================================
CREATE TABLE IF NOT EXISTS notes (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE notes ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE notes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE notes
SET content = COALESCE(content, title, '')
WHERE content IS NULL;

ALTER TABLE notes ALTER COLUMN title DROP NOT NULL;
ALTER TABLE notes ALTER COLUMN content SET DEFAULT '';
ALTER TABLE notes ALTER COLUMN content SET NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'notes_user_id_fkey'
    ) THEN
        ALTER TABLE notes DROP CONSTRAINT notes_user_id_fkey;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);

-- =============================================
-- 4. REMINDERS
-- =============================================
CREATE TABLE IF NOT EXISTS reminders (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    chat_id TEXT,
    message TEXT,
    time TIMESTAMPTZ,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE reminders ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS chat_id TEXT;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS time TIMESTAMPTZ;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS reminder_text TEXT;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS reminder_time TIMESTAMPTZ;

UPDATE reminders
SET message = COALESCE(message, reminder_text)
WHERE message IS NULL AND reminder_text IS NOT NULL;

UPDATE reminders
SET time = COALESCE(time, reminder_time)
WHERE time IS NULL AND reminder_time IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(time);

-- =============================================
-- 5. AI USAGE
-- =============================================
CREATE TABLE IF NOT EXISTS ai_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    usage_count INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS usage_date DATE NOT NULL DEFAULT CURRENT_DATE;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS token_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;

UPDATE ai_usage
SET usage_count = GREATEST(usage_count, COALESCE(message_count, 0));

CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_usage_user_date ON ai_usage(user_id, usage_date);

-- =============================================
-- 6. GAME SCORES
-- =============================================
CREATE TABLE IF NOT EXISTS game_scores (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    game_type TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    difficulty TEXT,
    duration_seconds INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_scores_user ON game_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_game_scores_type ON game_scores(game_type);
CREATE INDEX IF NOT EXISTS idx_game_scores_score ON game_scores(score DESC);

CREATE OR REPLACE VIEW game_highscores AS
SELECT
    user_id,
    game_type,
    MAX(score) AS high_score,
    COUNT(*) AS total_games,
    AVG(score)::INTEGER AS avg_score
FROM game_scores
GROUP BY user_id, game_type;

-- =============================================
-- 7. LEGACY GAME LOGS
-- =============================================
CREATE TABLE IF NOT EXISTS xox_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    winner TEXT NOT NULL,
    difficulty TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_xox_logs_user ON xox_logs(user_id);

CREATE TABLE IF NOT EXISTS tkm_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_move TEXT NOT NULL,
    bot_move TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tkm_logs_user ON tkm_logs(user_id);

CREATE TABLE IF NOT EXISTS dice_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dice_logs_user ON dice_logs(user_id);

CREATE TABLE IF NOT EXISTS coinflip_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_coinflip_logs_user ON coinflip_logs(user_id);

-- =============================================
-- 8. TOOL USAGE
-- =============================================
CREATE TABLE IF NOT EXISTS tool_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    action TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE tool_usage ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE tool_usage ADD COLUMN IF NOT EXISTS tool_name TEXT;
ALTER TABLE tool_usage ADD COLUMN IF NOT EXISTS action TEXT;
ALTER TABLE tool_usage ADD COLUMN IF NOT EXISTS metadata JSONB;
ALTER TABLE tool_usage ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_tool_usage_user ON tool_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool_name ON tool_usage(tool_name);

-- =============================================
-- 9. METRO FAVORITES
-- =============================================
CREATE TABLE IF NOT EXISTS metro_favorites (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    line_name TEXT,
    station_id TEXT,
    station_name TEXT,
    direction_id TEXT,
    direction_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS line_id TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS line_name TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS station_id TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS station_name TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS direction_id TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS direction_name TEXT;
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE metro_favorites ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'metro_favorites_user_id_line_id_key'
    ) THEN
        ALTER TABLE metro_favorites DROP CONSTRAINT metro_favorites_user_id_line_id_key;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_metro_favorites_user ON metro_favorites(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_metro_favorites_triplet
    ON metro_favorites(user_id, station_id, direction_id)
    WHERE station_id IS NOT NULL AND direction_id IS NOT NULL;

-- =============================================
-- 10. HELPER FUNCTIONS
-- =============================================
CREATE OR REPLACE FUNCTION save_game_score(
    p_user_id TEXT,
    p_game_type TEXT,
    p_score INTEGER,
    p_difficulty TEXT DEFAULT NULL,
    p_duration INTEGER DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO game_scores (user_id, game_type, score, difficulty, duration_seconds, metadata)
    VALUES (p_user_id, p_game_type, p_score, p_difficulty, p_duration, p_metadata);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_high_score(
    p_user_id TEXT,
    p_game_type TEXT
) RETURNS INTEGER AS $$
DECLARE
    high_score INTEGER;
BEGIN
    SELECT MAX(score) INTO high_score
    FROM game_scores
    WHERE user_id = p_user_id AND game_type = p_game_type;

    RETURN COALESCE(high_score, 0);
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 11. UPDATED_AT TRIGGERS
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_states_updated_at ON user_states;
CREATE TRIGGER update_user_states_updated_at
    BEFORE UPDATE ON user_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_notes_updated_at ON notes;
CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_reminders_updated_at ON reminders;
CREATE TRIGGER update_reminders_updated_at
    BEFORE UPDATE ON reminders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ai_usage_updated_at ON ai_usage;
CREATE TRIGGER update_ai_usage_updated_at
    BEFORE UPDATE ON ai_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_metro_favorites_updated_at ON metro_favorites;
CREATE TRIGGER update_metro_favorites_updated_at
    BEFORE UPDATE ON metro_favorites
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
