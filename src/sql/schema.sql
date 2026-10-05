-- Dimension Layer (Descriptive Entities)

-- 1. Token Dimension (Source: CoinCap)
-- Stores descriptive attributes of cryptocurrency assets.
CREATE TABLE IF NOT EXISTS dim_tokens (
    token_key SERIAL PRIMARY KEY,        
    api_id VARCHAR(255) UNIQUE NOT NULL, -- Internal identifier utilised by CoinCap (e.g., 'bitcoin')
    symbol VARCHAR(50) NOT NULL,         
    name VARCHAR(255),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Protocol Dimension (Source: DefiLlama)
-- Stores descriptive attributes of decentralised finance protocols.
CREATE TABLE IF NOT EXISTS dim_protocols (
    protocol_key SERIAL PRIMARY KEY,      
    defillama_id VARCHAR(255) UNIQUE NOT NULL, 
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100)                
);

-- Bridge / Mapping Layer

-- 3. The Mapping Table
-- Resolves the granularity mismatch between disparate data sources.
CREATE TABLE IF NOT EXISTS protocol_token_map (
    protocol_key INT REFERENCES dim_protocols(protocol_key),
    token_key INT REFERENCES dim_tokens(token_key),
    PRIMARY KEY (protocol_key, token_key)
);

-- Fact Layer (Time-Series Metrics)

-- 4. Token Market Fact
-- Records time-series financial and sentiment metrics for individual tokens.
CREATE TABLE IF NOT EXISTS fact_token_market (
    fact_id SERIAL PRIMARY KEY,
    token_key INT REFERENCES dim_tokens(token_key),
    timestamp TIMESTAMP NOT NULL,
    
    -- Financial Metrics
    price_usd NUMERIC(32, 8),
    volume_24h_usd NUMERIC(32, 8),
    market_cap_usd NUMERIC(32, 8),
    
    -- Attention and Sentiment Metrics
    is_trending BOOLEAN DEFAULT FALSE,
    trending_score INT,

    -- Enforcing the Grain: Prevents duplicate records for the same token at the exact same timestamp
    CONSTRAINT uq_token_time UNIQUE (token_key, timestamp)
);

-- 5. Protocol TVL Fact
-- Records time-series Total Value Locked (TVL) metrics for protocols.
CREATE TABLE IF NOT EXISTS fact_protocol_tvl (
    fact_id SERIAL PRIMARY KEY,
    protocol_key INT REFERENCES dim_protocols(protocol_key),
    timestamp TIMESTAMP NOT NULL,
    
    -- Utility Metrics
    tvl_usd NUMERIC(32, 8),

    -- Enforcing the Grain: Prevents duplicate records for the same protocol at the exact same timestamp
    CONSTRAINT uq_protocol_time UNIQUE (protocol_key, timestamp)
);

-- Indexes for Query Performance Optimisation
-- Note: The UNIQUE constraints above automatically generate B-Tree indexes for (key, timestamp).
-- These single-column indexes are added to optimise relational joins when time filtering is absent.
CREATE INDEX IF NOT EXISTS idx_token_market_key ON fact_token_market(token_key);
CREATE INDEX IF NOT EXISTS idx_protocol_tvl_key ON fact_protocol_tvl(protocol_key);