-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a table to store HSB's strict underwriting guidelines
CREATE TABLE IF NOT EXISTS underwriting_guidelines (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    rule_text TEXT NOT NULL,
    -- 1536 is the default dimension for OpenAI's text-embedding-3-small/ada-002
    -- Change this if you are using a different embedding model (like Voyage AI)
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create an index to speed up cosine similarity searches
CREATE INDEX ON underwriting_guidelines USING hnsw (embedding vector_cosine_ops);

-- Bind outcomes and loss experience for feedback loop
CREATE TABLE IF NOT EXISTS bind_outcomes (
    outcome_id VARCHAR(64) PRIMARY KEY,
    bundle_id VARCHAR(64) NOT NULL,
    org_id VARCHAR(64) NOT NULL DEFAULT 'default',
    status VARCHAR(32) NOT NULL,
    policy_number VARCHAR(64),
    quoted_premium NUMERIC(14, 2),
    bound_premium NUMERIC(14, 2),
    ai_decision VARCHAR(32),
    uw_decision VARCHAR(32),
    bound_at TIMESTAMPTZ,
    policy_admin_reference VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loss_experience (
    experience_id VARCHAR(64) PRIMARY KEY,
    policy_number VARCHAR(64) NOT NULL,
    bundle_id VARCHAR(64),
    org_id VARCHAR(64) NOT NULL DEFAULT 'default',
    policy_year INT NOT NULL,
    earned_premium NUMERIC(14, 2),
    incurred_losses NUMERIC(14, 2),
    paid_losses NUMERIC(14, 2),
    claim_count INT,
    loss_ratio NUMERIC(8, 4),
    reported_at DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS uw_sign_offs (
    sign_off_id VARCHAR(64) PRIMARY KEY,
    bundle_id VARCHAR(64) NOT NULL,
    org_id VARCHAR(64) NOT NULL DEFAULT 'default',
    action VARCHAR(32) NOT NULL,
    signed_by VARCHAR(128) NOT NULL,
    license_number VARCHAR(64),
    notes TEXT,
    ai_decision VARCHAR(32),
    override_reason TEXT,
    signed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bind_outcomes_org ON bind_outcomes(org_id);
CREATE INDEX IF NOT EXISTS idx_loss_experience_policy ON loss_experience(policy_number);
CREATE INDEX IF NOT EXISTS idx_uw_sign_offs_bundle ON uw_sign_offs(bundle_id);

INSERT INTO underwriting_guidelines (category, rule_text, embedding)
VALUES (
    'Property',
    'DECLINE: Any cold storage facility with ammonia refrigeration lacking both secondary containment and central station gas monitoring.',
    array_fill(0, ARRAY[1536])::vector
);