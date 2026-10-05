import pandas as pd
from sqlalchemy import text
from src.utils.db_connection import get_engine

def load_market_data(silver_filepath: str):
    """Loads CoinCap CSV data into the dim_tokens and fact_token_market tables.

    Args:
        silver_filepath (str): The absolute file path to the Silver layer CSV containing market data.
    """
    print(f"Loading Market Data to Postgres: {silver_filepath}")
    df = pd.read_csv(silver_filepath)
    if df.empty: return
    
    # Casts to datetime and snaps to the nearest minute to align with CoinGecko
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.floor('min')
    
    engine = get_engine()
    with engine.begin() as conn:
        # Utilises DO NOTHING on conflict to prevent database bloat and unnecessary WAL writes
        dim_sql = text("""
            INSERT INTO dim_tokens (api_id, symbol, name)
            VALUES (:api_id, :symbol, :name)
            ON CONFLICT (api_id) DO NOTHING
        """)
        dims_df = df[['api_id', 'symbol', 'name']].drop_duplicates()
        conn.execute(dim_sql, dims_df.to_dict(orient='records'))
        
        # Executes an efficient lookup utilising an IN clause instead of fetching the whole table
        api_ids = tuple(df['api_id'].unique())
        lookup_sql = text("SELECT token_key, api_id FROM dim_tokens WHERE api_id IN :api_ids")
        key_map_df = pd.read_sql(lookup_sql, conn, params={"api_ids": api_ids})
        
        df = df.merge(key_map_df, on='api_id', how='inner')
        
        fact_sql = text("""
            INSERT INTO fact_token_market 
            (token_key, timestamp, price_usd, volume_24h_usd, market_cap_usd)
            VALUES (:token_key, :timestamp, :price_usd, :volume_24h_usd, :market_cap_usd)
            ON CONFLICT (token_key, timestamp) 
            DO UPDATE SET 
                price_usd = EXCLUDED.price_usd,
                volume_24h_usd = EXCLUDED.volume_24h_usd,
                market_cap_usd = EXCLUDED.market_cap_usd
        """)
        facts_df = df[['token_key', 'timestamp', 'price_usd', 'volume_24h_usd', 'market_cap_usd']]
        conn.execute(fact_sql, facts_df.to_dict(orient='records'))
        
    print(f"Successfully loaded {len(facts_df)} Market facts.")


def load_trending_data(silver_filepath: str):
    """Loads CoinGecko CSV data, updating the trending flags within the Fact table.

    Args:
        silver_filepath (str): The absolute file path to the Silver layer CSV containing trending data.
    """
    print(f"Loading Trending Data to Postgres: {silver_filepath}")
    df = pd.read_csv(silver_filepath)
    if df.empty: return
    
    # Snaps to the nearest minute to ensure it perfectly hits the 'ON CONFLICT' condition
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.floor('min')
    
    engine = get_engine()
    with engine.begin() as conn:
        dim_sql = text("""
            INSERT INTO dim_tokens (api_id, symbol, name)
            VALUES (:api_id, :symbol, :name)
            ON CONFLICT (api_id) DO NOTHING
        """)
        dims_df = df[['api_id', 'symbol', 'name']].drop_duplicates()
        conn.execute(dim_sql, dims_df.to_dict(orient='records'))
        
        # Executes an efficient lookup for the required token keys
        api_ids = tuple(df['api_id'].unique())
        lookup_sql = text("SELECT token_key, api_id FROM dim_tokens WHERE api_id IN :api_ids")
        key_map_df = pd.read_sql(lookup_sql, conn, params={"api_ids": api_ids})
        
        df = df.merge(key_map_df, on='api_id', how='inner')
        
        fact_sql = text("""
            INSERT INTO fact_token_market (token_key, timestamp, is_trending, trending_score)
            VALUES (:token_key, :timestamp, TRUE, :score)
            ON CONFLICT (token_key, timestamp) 
            DO UPDATE SET 
                is_trending = TRUE,
                trending_score = EXCLUDED.trending_score
        """)
        facts_df = df[['token_key', 'timestamp', 'score']]
        conn.execute(fact_sql, facts_df.to_dict(orient='records'))

    print(f"Successfully loaded {len(facts_df)} Trending facts.")


def load_tvl_data(silver_filepath: str):
    """Loads DefiLlama CSV data into dim_protocols, fact_protocol_tvl, and the Bridge Table.

    Args:
        silver_filepath (str): The absolute file path to the Silver layer CSV containing TVL data.
    """
    print(f"Loading TVL Data to Postgres: {silver_filepath}")
    df = pd.read_csv(silver_filepath)
    if df.empty: return
    
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.floor('min')
    
    engine = get_engine()
    with engine.begin() as conn:
        dim_sql = text("""
            INSERT INTO dim_protocols (defillama_id, name, category)
            VALUES (:defillama_id, :name, :category)
            ON CONFLICT (defillama_id) DO NOTHING
        """)
        dims_df = df[['defillama_id', 'name', 'category']].drop_duplicates()
        conn.execute(dim_sql, dims_df.to_dict(orient='records'))
        
        defillama_ids = tuple(df['defillama_id'].unique())
        lookup_sql = text("SELECT protocol_key, defillama_id FROM dim_protocols WHERE defillama_id IN :ids")
        proto_map = pd.read_sql(lookup_sql, conn, params={"ids": defillama_ids})
        
        df = df.merge(proto_map, on='defillama_id', how='inner')
        
        fact_sql = text("""
            INSERT INTO fact_protocol_tvl (protocol_key, timestamp, tvl_usd)
            VALUES (:protocol_key, :timestamp, :tvl_usd)
            ON CONFLICT (protocol_key, timestamp) 
            DO UPDATE SET tvl_usd = EXCLUDED.tvl_usd
        """)
        facts_df = df[['protocol_key', 'timestamp', 'tvl_usd']]
        conn.execute(fact_sql, facts_df.to_dict(orient='records'))
        
        # Enterprise bridge table logic to maintain relational integrity
        bridge_df = df.dropna(subset=['symbol'])[['protocol_key', 'symbol']].drop_duplicates()
        if not bridge_df.empty:
            symbols = tuple(bridge_df['symbol'].unique())
            
            # Utilises MIN(token_key) and GROUP BY to guarantee uniqueness.
            # This prevents a Cartesian explosion if multiple tokens share the same symbol.
            token_sql = text("""
                SELECT MIN(token_key) as token_key, symbol 
                FROM dim_tokens 
                WHERE symbol IN :symbols 
                GROUP BY symbol
            """)
            token_map = pd.read_sql(token_sql, conn, params={"symbols": symbols})
            
            bridge_insert_df = bridge_df.merge(token_map, on='symbol', how='inner')
            
            if not bridge_insert_df.empty:
                bridge_sql = text("""
                    INSERT INTO protocol_token_map (protocol_key, token_key)
                    VALUES (:protocol_key, :token_key)
                    ON CONFLICT DO NOTHING
                """)
                conn.execute(bridge_sql, bridge_insert_df[['protocol_key', 'token_key']].to_dict(orient='records'))
                
    print(f"Successfully loaded {len(facts_df)} TVL facts and safely updated the Bridge Table.")