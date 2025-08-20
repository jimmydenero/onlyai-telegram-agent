-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- User roles enum
CREATE TYPE user_role AS ENUM ('none', 'student', 'owner');

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    role user_role DEFAULT 'none',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Whitelist table
CREATE TABLE IF NOT EXISTS whitelist (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Messages table (for group monitoring)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    kept BOOLEAN DEFAULT FALSE
);

-- Documents table
CREATE TABLE IF NOT EXISTS docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    source TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Document chunks table with vector embeddings
CREATE TABLE IF NOT EXISTS doc_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID REFERENCES docs(id) ON DELETE CASCADE,
    section TEXT,
    text TEXT NOT NULL,
    tokens INTEGER NOT NULL,
    embedding vector(1536),
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chat digests table
CREATE TABLE IF NOT EXISTS chat_digests (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    text TEXT NOT NULL,
    meta JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Q&A logs table
CREATE TABLE IF NOT EXISTS qa_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_whitelist_telegram_id ON whitelist(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_kept ON messages(kept);
CREATE INDEX IF NOT EXISTS idx_docs_title_version ON docs(title, version);
CREATE INDEX IF NOT EXISTS idx_docs_is_active ON docs(is_active);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc_id ON doc_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chat_digests_date ON chat_digests(date);
CREATE INDEX IF NOT EXISTS idx_qa_logs_user_id ON qa_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_qa_logs_created_at ON qa_logs(created_at);

-- Full-text search index for doc_chunks
CREATE INDEX IF NOT EXISTS idx_doc_chunks_text_gin ON doc_chunks USING GIN(to_tsvector('english', text));

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON doc_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_docs_updated_at_source ON docs(updated_at, source);
CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages(chat_id, created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for docs table
CREATE TRIGGER update_docs_updated_at BEFORE UPDATE ON docs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
