import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="GPU Market Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for that "Pro" look
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .stDataFrame { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. DATA LOADING & ENGINEERING
# ==========================================
@st.cache_data(ttl=600)
def load_and_clean_data():
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            dbname=st.secrets["postgres"]["dbname"],
            port=st.secrets["postgres"]["port"],
            sslmode="require"
        )
        query = "SELECT * FROM gpu_prices"
        df = pd.read_sql(query, conn)
        conn.close()

        # --------------------------------------------------------
        # CRITICAL FIX: Renaming DB columns to match App Logic
        # Database returns: gpu_name, price, benchmark_score...
        # App expects: GPU_Name, Price_USD, Benchmark_Score...
        # --------------------------------------------------------
        df = df.rename(columns={
            "gpu_name": "GPU_Name",
            "price": "Price_USD",
            "benchmark_score": "Benchmark_Score",
            "manufacturer": "Manufacturer",
            # DB has 'value_rating', App calculates 'Value_Score' later, 
            # but we can map it just in case.
            "value_rating": "Value_Score_DB" 
        })

        # Ensure numeric types
        df['Price_USD'] = pd.to_numeric(df['Price_USD'], errors='coerce')
        df['Benchmark_Score'] = pd.to_numeric(df['Benchmark_Score'], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return pd.DataFrame()


# Invoking function to get the data

df_raw = load_and_clean_data()

# Safety Check: Stop if database is empty or connection failed
if df_raw.empty:
    st.warning("⚠️ No data loaded from Supabase. Please check your database connection.")
    st.stop()
    
# ==========================================
# 3. SIDEBAR CONTROLS (UX UPGRADES)
# ==========================================
st.sidebar.header("🛠️ Market Filters")

# --- UX FEATURE 2: CURRENCY CONVERTER ---
currency = st.sidebar.radio("Currency", ["USD ($)", "INR (₹)"], horizontal=True)

# Currency Logic
if currency == "INR (₹)":
    EXCHANGE_RATE = 87.0  # Approx Rate
    SYMBOL = "₹"
    # Create a display column for filtering/plotting
    df_raw['Price_Display'] = df_raw['Price_USD'] * EXCHANGE_RATE
else:
    EXCHANGE_RATE = 1.0
    SYMBOL = "$"
    df_raw['Price_Display'] = df_raw['Price_USD']

# Brand Filter
brands = st.sidebar.multiselect(
    "Select Manufacturer",
    options=df_raw['Manufacturer'].unique(),
    default=["NVIDIA", "AMD", "Intel"]
)

# --- TEXT SEARCH ---
search_query = st.sidebar.text_input("🔍 Search GPU Name", placeholder="e.g. 4070, RX 7800")

# Logic (Place this BEFORE you create 'filtered_df')
if search_query:
    # Filter raw data first based on search
    df_raw = df_raw[df_raw['GPU_Name'].str.contains(search_query, case=False)]


# --- UX FEATURE 1: PRECISE PRICE INPUT ---
# We use a container to put Slider + Input closer together
st.sidebar.subheader("💰 Budget Range")

# Determine max price in current currency for the slider limits
max_dataset_price = int(df_raw['Price_Display'].max())
min_dataset_price = int(df_raw['Price_Display'].min())

col_min, col_max = st.sidebar.columns(2)
with col_min:
    min_price_input = st.number_input(f"Min ({SYMBOL})", min_value=0, value=min_dataset_price)
with col_max:
    # Default to a reasonable high value (e.g., 2000 USD or 1.5 Lakh INR)
    default_max = 1500 if currency == "USD ($)" else 150000
    max_price_input = st.number_input(f"Max ({SYMBOL})", min_value=0, value=default_max)

# Filter Logic (Using the Inputs, not just a sticky slider)
mask = (
        (df_raw['Manufacturer'].isin(brands)) &
        (df_raw['Price_Display'] >= min_price_input) &
        (df_raw['Price_Display'] <= max_price_input)
)
filtered_df = df_raw[mask].copy()

# Update Value Score for Display (Points per Displayed Currency)
filtered_df['Value_Score_Display'] = filtered_df['Benchmark_Score'] / filtered_df['Price_Display']

# ---About---
st.sidebar.markdown("---")
with st.sidebar.expander("ℹ️ How is this calculated?"):
    st.write("""
    1. **Price:** Real-time market data scraped from major retailers.
    2. **Performance:** Based on PassMark G3D Mark scores.
    3. **Value Score:** `Performance Score / Price`. Higher is better!
    """)

# ==========================================
# 4. MAIN DASHBOARD UI
# ==========================================
# --- UX FEATURE 4: PROFESSIONAL NAMING ---
st.title("📈 GPU Market Watch: Live Deal Hunter")
st.markdown("### ⚡ Real-Time Arbitrage & Performance Tracker")
st.markdown(f"""
Tracking **{len(df_raw)} GPUs**. Identifying undervalued assets via **Price-to-Performance** ratios.
""")

st.divider()

# --- TOP LEVEL METRICS ---
if not filtered_df.empty:
    best_value = filtered_df.loc[filtered_df['Value_Score_Display'].idxmax()]
    best_perf = filtered_df.loc[filtered_df['Benchmark_Score'].idxmax()]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🏆 Best Value Deal",
            value=best_value['GPU_Name'],
            delta=f"{best_value['Value_Score_Display']:.2f} Pts/{SYMBOL}"
        )

    with col2:
        st.metric(
            label="🚀 Top Performance",
            value=best_perf['GPU_Name'],
            delta=f"{best_perf['Benchmark_Score']} G3D Mark"
        )

    with col3:
        st.metric(
            label="📊 Market Sample Size",
            value=f"{len(filtered_df)} Cards",
            delta=f"Range: {SYMBOL}{min_price_input} - {SYMBOL}{max_price_input}"
        )
else:
    st.warning(f"⚠️ No GPUs found between {SYMBOL}{min_price_input} and {SYMBOL}{max_price_input}. Check your filters.")

# ==========================================
# 5. STRATEGIC VISUALIZATION
# ==========================================
st.divider()
st.subheader(f"🔍 Market Landscape: Price ({SYMBOL}) vs. Performance")

if not filtered_df.empty:
    fig = px.scatter(
        filtered_df,
        x="Price_Display",
        y="Benchmark_Score",
        color="Manufacturer",
        size="Value_Score_Display",
        hover_name="GPU_Name",
        hover_data={"Price_Display": f":.2f", "Benchmark_Score": True, "Value_Score_Display": ":.2f"},
        color_discrete_map={"NVIDIA": "#76b900", "AMD": "#ed1c24", "Intel": "#0071c5"},
        title="<b>The Efficiency Frontier</b> (Top Left = Best Deals)",
        labels={"Price_Display": f"Price ({SYMBOL})", "Benchmark_Score": "3DMark Score",
                "Value_Score_Display": "Value Score"},
        height=600,
        template="plotly_dark"
    )
    st.plotly_chart(fig, width='stretch')

    st.caption(
        "💡 **Pro Tip:** Look for large bubbles in the top-left quadrant. These are high-performance cards at low prices.")

# ... (Previous code remains unchanged) ...

# ==========================================
# 6. DEAL HUNTER TABLE (With "Show All" Option)
# ==========================================
st.divider()
c_header, c_toggle = st.columns([3, 1])

with c_header:
    st.subheader("💰 Deal Hunter: Best Value Cards")
with c_toggle:
    # UX FEATURE 5: SHOW ALL TOGGLE
    show_all = st.checkbox("Show All GPUs", value=False)

if not filtered_df.empty:
    # Sort by Value Score (Always show best value first)
    deals = filtered_df.sort_values(by='Value_Score_Display', ascending=False)

    # Toggle Logic
    if not show_all:
        deals = deals.head(10)

    # Clean Index
    deals = deals.reset_index(drop=True)
    deals.index += 1

    # Select & Rename Columns
    cols = ['GPU_Name', 'Price_Display', 'Benchmark_Score', 'Value_Score_Display', 'Manufacturer']
    deals = deals[cols].rename(columns={
        'Price_Display': f'Price ({SYMBOL})',
        'Value_Score_Display': 'Value Rating'
    })

    # Display Table with Green Heatmap on Value Rating
    st.dataframe(
        deals.style.background_gradient(subset=['Value Rating'], cmap="Greens")
        .format({f'Price ({SYMBOL})': "{:.2f}"}),
        width='stretch',
        height=500 if show_all else "content"
    )






