import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv


# Environment Setup

# Load environment variables from a .env file to securely manage database credentials
load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "airflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
POSTGRES_DB = os.getenv("POSTGRES_DB", "crypto_pipeline")
DB_HOST = os.getenv("DB_HOST", "localhost")

# Construct the SQLAlchemy database connection string for PostgreSQL
DB_CONN = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:5432/{POSTGRES_DB}"

# Page Setup

# Configure the Streamlit page layout and metadata.
st.set_page_config(
    page_title="DeFi Analytics Engine",
    layout="wide",
    page_icon="bar-chart"
)

st.title("DeFi Market Intelligence Dashboard")
st.markdown("Automated insights generated directly from the Airflow Data Warehouse.")

# Data Extraction Functions
@st.cache_data(ttl=60)
def load_defi_data():
    """
    Extracts and harmonises market data and TVL metrics from the PostgreSQL dimensional warehouse.
    
    This query utilises Common Table Expressions (CTEs) and the DISTINCT ON clause to 
    ensure only the most recent snapshot for each protocol is retrieved. It then performs 
    relational JOINs across the Star Schema (utilising the bridge table) to produce a 
    unified dataset containing both speculative market metrics and fundamental protocol data.
    
    Returns:
        pd.DataFrame: The harmonised analytical dataset.
    """
    engine = create_engine(DB_CONN)
    query = """
    WITH LatestMarket AS (
        SELECT DISTINCT ON (token_key)
            token_key, price_usd, volume_24h_usd, market_cap_usd, is_trending
        FROM fact_token_market
        ORDER BY token_key, timestamp DESC
    ),
    LatestTVL AS (
        SELECT DISTINCT ON (protocol_key)
            protocol_key, tvl_usd
        FROM fact_protocol_tvl
        ORDER BY protocol_key, timestamp DESC
    )
    SELECT 
        p.name AS protocol, t.symbol, m.price_usd AS price,
        m.volume_24h_usd AS volume, m.market_cap_usd AS mcap,
        tvl.tvl_usd AS tvl, m.is_trending
    FROM dim_tokens t
    JOIN protocol_token_map bridge ON t.token_key = bridge.token_key
    JOIN dim_protocols p ON bridge.protocol_key = p.protocol_key
    JOIN LatestMarket m ON t.token_key = m.token_key
    JOIN LatestTVL tvl ON p.protocol_key = tvl.protocol_key
    WHERE m.price_usd > 0 
        AND m.market_cap_usd > 0
        AND tvl.tvl_usd > 0
        AND p.name != 'Binance CEX'
    """
    df = pd.read_sql(query, engine)
    
    # Compute critical analytical ratios and format large numerical values into billions/millions
    df["mcap_tvl_ratio"] = df["mcap"] / df["tvl"]
    df["mcap_billions"] = df["mcap"] / 1e9
    df["tvl_billions"] = df["tvl"] / 1e9
    df["volume_millions"] = df["volume"] / 1e6
    return df

@st.cache_data(ttl=60)
def load_trending_data():
    """
    Extracts currently trending tokens globally, serving as a proxy dataset 
    for retail attention and speculative trading behaviour.
    
    Returns:
        pd.DataFrame: A dataset containing recently flagged trending tokens.
    """
    engine = create_engine(DB_CONN)
    query = """
    WITH LatestMarket AS (
        SELECT DISTINCT ON (token_key) token_key, price_usd, volume_24h_usd, market_cap_usd
        FROM fact_token_market WHERE is_trending = True
        ORDER BY token_key, timestamp DESC
    )
    SELECT t.name as protocol, t.symbol, m.price_usd, m.volume_24h_usd, m.market_cap_usd
    FROM dim_tokens t JOIN LatestMarket m ON t.token_key = m.token_key
    ORDER BY m.market_cap_usd DESC
    """
    return pd.read_sql(query, engine)

try:
    # Execute data loading
    df = load_defi_data()
    trending_df = load_trending_data()

    # Graceful degradation if the Airflow pipeline has not populated the database yet
    if df.empty:
        st.info("Waiting for data to populate from Airflow...")
        st.stop()
        
    # Sidebar Filters
    st.sidebar.header("Data Filters")
    protocols = sorted(df["protocol"].unique())
    selected_protocols = st.sidebar.multiselect(
        "Select Protocols",
        protocols,
        default=protocols
    )

    # Apply user filters to the primary dataframe
    df_filtered = df[df["protocol"].isin(selected_protocols)]

    # KPI Section

    # Display high-level aggregate metrics for the current dataset snapshot
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Protocols Tracked", df_filtered["protocol"].nunique())
    c2.metric("Total TVL", f"${df_filtered['tvl_billions'].sum():,.2f}B")
    c3.metric("Total Market Cap", f"${df_filtered['mcap_billions'].sum():,.2f}B")
    c4.metric("Global Trending Tokens", len(trending_df))

    st.divider()
    
    # GRAPH 1: MARKET CAP VS TVL COMPARISON

    st.subheader("Market Capitalisation vs. Total Value Locked (Top 10 Protocols)")
    st.markdown("""
    *This visualisation explicitly compares the market capitalisation against the actual capital secured within the smart contracts. 
    It reveals that foundational DeFi infrastructure (e.g., Aave V3) holds significantly more TVL than its token valuation suggests.*
    """)

    # Extract the top 10 protocols by TVL and sort ascending for the horizontal bar chart
    top_10_tvl = df_filtered.nlargest(10, "tvl_billions").sort_values("tvl_billions", ascending=True)
    
    # Rename columns for cleaner Plotly legend integration
    comparison_df = top_10_tvl[['protocol', 'tvl_billions', 'mcap_billions', 'mcap_tvl_ratio']].copy()
    comparison_df.rename(columns={'tvl_billions': 'TVL (USD Billions)', 'mcap_billions': 'Market Cap (USD Billions)'}, inplace=True)

    # Generate a grouped bar chart to visually prove the divergence between TVL and Market Cap
    # Applying an explicit, highly readable professional color palette
    fig_comparison = px.bar(
        comparison_df,
        y="protocol",
        x=["TVL (USD Billions)", "Market Cap (USD Billions)"],
        orientation="h",
        barmode="group",
        text_auto=".2f",
        labels={"value": "USD (Billions)", "variable": "Metric", "protocol": ""},
        hover_data={"mcap_tvl_ratio": ":.3f"},
        color_discrete_map={
            "TVL (USD Billions)": "#2A669F",       # Deep professional blue for fundamental utility
            "Market Cap (USD Billions)": "#E36C0A" # Contrasting orange for speculative market cap
        }
    )
    
    # Format the layout for academic presentation
    fig_comparison.update_layout(
        legend_title_text="Financial Metric",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Enforce white text color and a larger font size for maximum contrast and readability
    fig_comparison.update_traces(textfont_color='white', textfont_size=16)
    
    st.plotly_chart(fig_comparison, use_container_width=True)

    with st.expander("Analysis Guide: Market Cap vs. TVL Divergence"):
        st.markdown("""
        * **The Goal:** This grouped bar chart directly compares fundamental utility against speculative market valuation.
        * **Interpretation:** Look for protocols where the "TVL" bar significantly exceeds the "Market Cap" bar. This visually indicates that users have deposited more real capital into the platform than the market is willing to pay for the associated governance token, suggesting potential undervaluation.
        """)

    st.divider()

    # GRAPH 2: VALUATION SCATTER PLOT

    st.subheader("Protocol Valuation: TVL vs Market Capitalisation")
    
    # Statistical Clipping: Calculate the 95th percentile to prevent extreme outliers from breaking the visual gradient
    ratio_cap = df_filtered["mcap_tvl_ratio"].quantile(0.95)

    # Plotly scatter chart utilising logarithmic scaling to accommodate the extreme variance in crypto valuations
    fig1 = px.scatter(
        df_filtered, x="tvl_billions", y="mcap_billions", size="volume_millions", color="mcap_tvl_ratio",
        hover_name="protocol", hover_data={"symbol": True, "price": ":.2f", "mcap_tvl_ratio": ":.3f"},
        labels={"tvl_billions": "Total Value Locked (Billions)", "mcap_billions": "Market Cap (Billions)", "mcap_tvl_ratio": "Valuation Ratio"},
        log_x=True, log_y=True, color_continuous_scale="Spectral_r", range_color=[0, ratio_cap]
    )
    
    # Define explicit, moderate tick intervals for the Y-axis to improve logarithmic readability
    mod_ticks_b = [0.01, 0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000]
    mod_labels_b = [f"${t}B" for t in mod_ticks_b]
    
    fig1.update_yaxes(tickvals=mod_ticks_b, ticktext=mod_labels_b)
    st.plotly_chart(fig1, use_container_width=True)
    
    with st.expander("Analysis Guide: Protocol Valuation"):
        st.markdown("""
        * **X-Axis (TVL):** The amount of real capital locked in the protocol's smart contracts (Logarithmic Scale). 
        * **Y-Axis (Market Cap):** The total market value of the protocol's circulating token supply (Logarithmic Scale).
        * **Color Gradient (Valuation Ratio):** Clipped at the 95th percentile. Blue dots represent potentially undervalued protocols. Red dots represent high speculative premiums.
        * **Bubble Size:** Represents 24h Trading Volume.
        """)

    st.divider()


    # GRAPH 3: MARKET ACTIVITY

    st.subheader("Market Activity: Trading Volume vs Market Capitalisation")

    fig_activity = px.scatter(
        df_filtered, x="mcap_billions", y="volume_millions", size="tvl_billions", color="protocol",
        hover_name="protocol", labels={"mcap_billions": "Market Cap (Billions)", "volume_millions": "24h Volume (Millions)"},
        log_x=True, log_y=True
    )
    
    # Define explicit tick intervals for the Millions scale (Y-axis)
    mod_ticks_m = [1, 2, 5, 10, 50, 100, 500, 1000, 5000, 10000]
    mod_labels_m = [f"${t}M" for t in mod_ticks_m]
    
    # Explicitly use the Billions scale for the X-axis to showcase the logarithmic nature
    fig_activity.update_yaxes(tickvals=mod_ticks_m, ticktext=mod_labels_m)
    fig_activity.update_xaxes(tickvals=mod_ticks_b, ticktext=mod_labels_b) 
    
    fig_activity.update_layout(showlegend=False) 
    st.plotly_chart(fig_activity, use_container_width=True)
    
    with st.expander("Analysis Guide: Market Activity"):
        st.markdown("""
        * **X-Axis (Market Cap):** Total asset valuation mapped on a **Logarithmic Scale** to resolve the extreme variance between small-cap and large-cap assets.
        * **Y-Axis (Trading Volume):** Asset turnover frequency, also scaled logarithmically. High volume relative to market cap indicates high retail interest or speculation.
        * **Bubble Size (TVL):** Represents foundational liquidity. Large bubbles show protocols with deep capital reserves.
        """)

    st.divider()

    # GRAPH 4: TOP 10 PROTOCOLS BY TVL

    st.subheader("Top 10 Protocols by TVL")
    fig2 = px.bar(
        top_10_tvl, x="tvl_billions", y="protocol", orientation="h",
        color="tvl_billions", color_continuous_scale="Blues",
        text_auto=".2f", labels={"tvl_billions": "TVL ($ Billions)", "protocol": ""}
    )
    fig2.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Analysis Guide: Total Value Locked"):
        st.markdown("""
        * **The Metric:** TVL represents the dollar value of all tokens locked in the protocol's smart contracts.
        * **Interpretation:** This serves as a non-speculative baseline for protocol adoption. High TVL indicates product-market fit and user trust.
        """)

    st.divider()

    # GRAPH 5: MOST UNDERVALUED PROTOCOLS

    st.subheader("Most Undervalued Protocols")
    st.markdown("Isolates protocols exhibiting strong fundamental adoption relative to token valuation (Ratio < 1.5).")
    
    # Filter dataset for protocols with mathematically low valuation ratios
    ratio_df = df_filtered[df_filtered["mcap_tvl_ratio"] < 1.5].nsmallest(10, "mcap_tvl_ratio").sort_values("mcap_tvl_ratio", ascending=False)

    fig3 = px.bar(
        ratio_df, x="mcap_tvl_ratio", y="protocol", orientation="h",
        color="mcap_tvl_ratio", color_continuous_scale="Greens_r",
        text_auto=".3f", labels={"mcap_tvl_ratio": "Market Cap / TVL Ratio", "protocol": ""}
    )
    fig3.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Analysis Guide: Valuation Ratio"):
        st.markdown("""
        * **The Metric:** Analogous to the Price-to-Book (P/B) ratio in traditional equities. 
        * **Interpretation:** A ratio under 1.0 indicates the protocol holds more capital inside its smart contracts than the market is pricing its governance token, highlighting an inefficient market valuation.
        """)

    st.divider()


    # DATA EXPLORER

    st.subheader("Gold Layer Data Explorer")
    st.markdown("Provides a transparent view of the final harmonised dataset joined across the dimensional schema.")
    
    display_df = df_filtered[["protocol", "symbol", "price", "mcap_billions", "tvl_billions", "mcap_tvl_ratio"]].copy()
    display_df.columns = ["Protocol", "Token", "Price ($)", "Market Cap (B)", "TVL (B)", "Valuation Ratio"]

    st.dataframe(
        display_df.style.format({
            "Price ($)": "${:.4f}",
            "Market Cap (B)": "${:.2f}B",
            "TVL (B)": "${:.2f}B",
            "Valuation Ratio": "{:.3f}"
        }),
        use_container_width=True,
        height=400
    )
    
    with st.expander("Analysis Guide: Data Explorer"):
        st.markdown("""
        * **Transparency:** This table provides raw access to the unified 'Gold Layer' data resulting from the Airflow Medallion pipeline.
        * **Interactivity:** Column headers can be clicked to sort the dataset (e.g., sort by the lowest Valuation Ratio to find fundamentally strong protocols).
        """)
    
    st.divider()


    # TRENDING TOKENS
  
    st.subheader("Current Trending Tokens (Global)")
    st.markdown("Raw feed of high-velocity search assets, serving as an indicator of unadulterated retail speculation.")
    
    if not trending_df.empty:
        st.dataframe(
            trending_df.style.format({
                'price_usd': '${:,.4f}',
                'volume_24h_usd': '${:,.0f}',
                'market_cap_usd': '${:,.0f}'
            }),
            column_config={
                "protocol": "Token Name",
                "symbol": "Ticker",
                "price_usd": "Price (USD)",
                "volume_24h_usd": "24h Volume",
                "market_cap_usd": "Market Cap"
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
    else:
        st.warning("No trending tokens detected in the latest batch.")

    with st.expander("Analysis Guide: Trending Tokens"):
        st.markdown("""
        * **The Data Source:** Populated directly from the CoinGecko Trending API, representing top global retail search velocity.
        * **Interpretation:** Unlike the DeFi charts above, this feed does *not* require the asset to have TVL. It highlights high-volatility, hype-driven assets, proving that retail speculation often diverges entirely from fundamental protocol utility.
        """)

except Exception as e:
    st.error(f"Database connection or query failed: {e}")