-- =====================================================================
-- THE BLACK-BUDGET CEMETERY // SUPABASE DUAL-VAULT & RAG INITIALIZATION
-- =====================================================================

-- 1. Enable multimodal vector search (pgvector) and geospatial intelligence (PostGIS)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Create isolated schemas (Invisible to public anonymous web APIs by default)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- 3. Automated Discovery Manifest Table (Tracks NARA/FBI/AARO cases & future releases)
CREATE TABLE IF NOT EXISTS raw.ingestion_manifest (
    nara_id TEXT PRIMARY KEY,
    source_archive TEXT NOT NULL,           -- e.g., 'NARA-595466', 'FBI-VAULT', 'AARO'
    source_path_or_url TEXT NOT NULL,       -- Local path or remote S3/FOIA URL
    ingestion_status TEXT DEFAULT 'PENDING',-- 'PENDING', 'COMPLETED', 'FAILED'
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_log TEXT
);

-- 4. Primary Evidence Vault: Unified Forensic Intelligence Table (Government Case Files)
CREATE TABLE IF NOT EXISTS raw.forensic_intelligence (
    nara_id TEXT PRIMARY KEY REFERENCES raw.ingestion_manifest(nara_id),
    document_title TEXT NOT NULL,
    pristine_transcript TEXT NOT NULL,

    -- Fast-filter scalar columns promoted from BlackBudgetCemeterySchema
    craft_type TEXT,
    historical_era TEXT,
    redaction_fingerprint TEXT,
    linguistic_stress_score INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    -- Full structured Pydantic sub-schemas stored as binary JSON (JSONB)
    sector_alpha JSONB NOT NULL,
    sector_beta JSONB NOT NULL,
    sector_gamma JSONB NOT NULL,

    -- Native PostGIS geographic point (SRID 4326 / WGS84) for spatial incident queries
    geom GEOGRAPHY(POINT, 4326),

    -- Native pgvector column (768 dims for local Ollama nomic-embed-text embeddings)
    embedding VECTOR(768),

    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Private Deep-Reference RAG Vault: E-Books, Peer-Reviewed Papers & Technical Lore
CREATE TABLE IF NOT EXISTS raw.reference_knowledge_chunks (
    chunk_id BIGSERIAL PRIMARY KEY,
    source_title TEXT NOT NULL,             -- e.g., 'The Report on Unidentified Flying Objects'
    author TEXT,                            -- e.g., 'Edward J. Ruppelt', 'Puthoff & Targ (SRI)'
    publication_year INTEGER,
    document_category TEXT NOT NULL,        -- 'EBOOK', 'PEER_REVIEWED_PAPER', 'TECHNICAL_MONOGRAPH'
    sector_domain TEXT NOT NULL,            -- 'ALPHA', 'BETA', 'GAMMA', or 'ALL'
    chunk_index INTEGER NOT NULL,           -- Paragraph/chunk sequence number within the book/paper
    chunk_text TEXT NOT NULL,               -- The ~500-word passage text for RAG context injection
    metadata JSONB DEFAULT '{}'::jsonb,     -- Page numbers, DOI, ISBN, or chapter headings

    -- 768-dimension semantic vector embedding matching our primary evidence vault
    embedding VECTOR(768),

    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    -- Prevents accidentally loading the same book chunk twice
    UNIQUE (source_title, chunk_index)
);

-- 6. High-speed indexes: PostGIS GIST spatial index + pgvector HNSW cosine similarity indexes
CREATE INDEX IF NOT EXISTS idx_forensic_geom
    ON raw.forensic_intelligence USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_forensic_embedding_hnsw
    ON raw.forensic_intelligence USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_reference_embedding_hnsw
    ON raw.reference_knowledge_chunks USING hnsw (embedding vector_cosine_ops);