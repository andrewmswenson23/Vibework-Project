import streamlit as st

st.set_page_config(
    page_title="VibeWork AI Platform",
    page_icon="🏗️",
    layout="wide"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        border-left: 4px solid #1E90FF;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 50px;
        font-weight: bold;
    }
    .platform-summary {
        background-color: #e8f4f8;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown('<p class="big-font">🚀 VibeWork AI | Enterprise Platform</p>', unsafe_allow_html=True)
st.markdown("**Centralized intelligence and probabilistic risk modeling across multiple industries.**")
st.markdown("Transform complex data into mathematically defensible business decisions.")
st.markdown("---")

# Navigation Columns
col1, col2, col3 = st.columns(3)

# ----------------- MODULE 1: SALES RADAR -----------------
with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown("### 🎯 Signal Radar")
    st.markdown("**Industry:** Construction (AEC)")
    st.markdown("Automated lead intelligence for the $18B Utah enterprise market.")
    st.markdown("**Monitors:** 63 industry leaders")
    st.markdown("**Uses:** Web scraping, NLP, signal detection")
    if st.button("→ Launch Radar", key="radar_btn"):
        st.switch_page("pages/1_Buying_Signal_Radar.py")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- MODULE 2: CONSTRUCTION RISK -----------------
with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown("### 🏗️ Project Risk Engine")
    st.markdown("**Industry:** Construction (AEC)")
    st.markdown("Probabilistic schedule simulations to quantify financial exposure.")
    st.markdown("**Simulations:** 2,000 Monte Carlo runs")
    st.markdown("**Uses:** Graph theory, CPM, shock propagation")
    if st.button("→ Launch Risk Engine", key="risk_btn"):
        st.switch_page("pages/2_Project_Risk_Engine.py")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- MODULE 3: WEALTH SIMULATOR -----------------
with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown("### 💰 Wealth Simulator")
    st.markdown("**Industry:** Financial Services")
    st.markdown("Quantitative portfolio stress-testing with AI-generated client reporting.")
    st.markdown("**Simulations:** 2,000 Monte Carlo runs")
    st.markdown("**Uses:** Stochastic modeling, guardrails, tax drag")
    if st.button("→ Launch Wealth Simulator", key="wealth_btn"):
        st.switch_page("pages/3_Wealth_Simulator.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Platform Architecture Summary
st.subheader("🏛️ Platform Architecture")

arch_col1, arch_col2 = st.columns(2)

with arch_col1:
    st.markdown("""
#### 📥 Data Ingestion Layer
- **Construction:** P6 schedules (Primavera), CSV task lists, unstructured delays
- **Finance:** Portfolio allocations, withdrawal amounts, market parameters
- **Market:** Web scraping, NLP keyword detection, digital footprint analysis
""")

with arch_col2:
    st.markdown("""
#### 🧠 Probabilistic Engine & Outputs
- **Simulation:** 2,000+ Monte Carlo iterations, NetworkX dependency graphs
- **Risk Quantification:** P90 finish dates, Liquidated Damages ($), Success Rates
- **AI Translation:** Anthropic Claude integration for executive-ready memos
""")
