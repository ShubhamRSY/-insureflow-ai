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

-- Insert a sample rule for testing
INSERT INTO underwriting_guidelines (category, rule_text, embedding)
VALUES (
    'Property',
    'DECLINE: Any cold storage facility with ammonia refrigeration lacking both secondary containment and central station gas monitoring.',
    array_fill(0, ARRAY[1536])::vector
);