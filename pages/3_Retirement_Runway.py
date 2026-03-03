import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Clean, decoupled import from the pure math core
from math_core import cholesky_from_corr, gaussian_copula_draw, sample_lognormal_from_z

st.set_page_config(layout="wide", page_title="FinOps | Sequence of Returns Risk")

# ---------------- UI & Settings ----------------
st.title("📉 Sequence of Returns: Risk Engine V3")
st.markdown("Fully Vectorized Monte Carlo with Inflation & Dynamic Drawdowns")

st.sidebar.header("Client Portfolio Settings")
initial_portfolio = st.sidebar.number_input("Initial Portfolio Value ($)", 1000000, 50000000, 5000000, step=500000)
withdrawal_rate = st.sidebar.slider("Initial Withdrawal Rate (%)", 1.0, 10.0, 4.0, step=0.1) / 100.0
inflation_rate = st.sidebar.slider("Annual Inflation Rate (%)", 0.0, 10.0, 2.5, step=0.1) / 100.0
years = st.sidebar.slider("Years in Retirement", 10, 50, 30)
iterations = st.sidebar.number_input("Monte Carlo Iterations", 500, 20000, 10000, step=500)

st.sidebar.markdown("---")
st.sidebar.header("Asset Allocation & Assumptions")
weight_eq = st.sidebar.slider("Equity Allocation (%)", 0, 100, 60, step=5) / 100.0
weight_bd = 1.0 - weight_eq
st.sidebar.caption(f"Bond Allocation: {weight_bd*100:.0f}%")

mu_eq = st.sidebar.number_input("Equities Expected Return (Log)", 0.0, 0.20, 0.07, step=0.01)
sig_eq = st.sidebar.number_input("Equities Volatility", 0.0, 0.40, 0.15, step=0.01)

mu_bd = st.sidebar.number_input("Bonds Expected Return (Log)", 0.0, 0.20, 0.03, step=0.01)
sig_bd = st.sidebar.number_input("Bonds Volatility", 0.0, 0.20, 0.05, step=0.01)

corr_eq_bd = st.sidebar.slider("Stock/Bond Correlation", -1.0, 1.0, 0.1, step=0.1)

# ---------------- Vectorized Simulation Engine ----------------
@st.cache_data(show_spinner=False)
def run_vectorized_wealth_simulation(init_val, w_rate, infl_rate, yrs, iters, w_eq, w_bd, mu_eq, sig_eq, mu_bd, sig_bd, corr):
    corr_matrix = [[1.0, corr], [corr, 1.0]]
    L = cholesky_from_corr(corr_matrix)
    
    # Dynamic seed based on inputs to prevent flickering while maintaining interactivity
    seed_val = int((init_val + w_rate + mu_eq) * 10000) % 2**32
    rng = np.random.default_rng(seed_val)
    
    # Pre-allocate the matrix for maximum performance
    paths = np.zeros((yrs + 1, iters))
    portfolios = np.full(iters, init_val, dtype=float)
    paths[0] = portfolios
    
    current_withdrawal = init_val * w_rate
    
    for y in range(yrs):
        # 1. Start-of-Year Withdrawal (Only apply to portfolios with money)
        active = portfolios > 0
        portfolios[active] -= current_withdrawal
        portfolios[portfolios < 0] = 0 
        
        # Recalculate active mask after withdrawal
        active = portfolios > 0
        
        # Short-circuit if all timelines are bankrupt
        if not np.any(active):
            paths[y+1:] = 0
            break
            
        # 2. Market Returns (Draw for ALL iterations simultaneously)
        z, _ = gaussian_copula_draw(L, rng, 2, iters=iters)
        
        # Vectorized lognormal conversion
        ret_eq = sample_lognormal_from_z(mu_eq, sig_eq, z[0]) - 1.0
        ret_bd = sample_lognormal_from_z(mu_bd, sig_bd, z[1]) - 1.0
        blended_return = (w_eq * ret_eq) + (w_bd * ret_bd)
        
        # 3. Apply Returns
        portfolios[active] = portfolios[active] * (1 + blended_return[active])
        paths[y + 1] = portfolios
        
        # 4. Compounding Inflation
        current_withdrawal *= (1 + infl_rate)
            
    # Transpose for easier plotting and percentile math
    paths_t = paths.T
    
    p10_path = np.percentile(paths_t, 10, axis=0)
    p50_path = np.percentile(paths_t, 50, axis=0)
    p90_path = np.percentile(paths_t, 90, axis=0)
    
    roll_max = np.maximum.accumulate(p50_path)
    drawdowns = (p50_path - roll_max) / roll_max
    
    survival_count = np.sum(paths_t[:, -1] > 0)
    success_rate = (survival_count / iters) * 100
    
    return paths_t, p10_path, p50_path, p90_path, drawdowns, success_rate

# ---------------- Run Simulation ----------------
with st.spinner("Calculating Financial Constraints..."):
    paths, p10, p50, p90, drawdowns, success_rate = run_vectorized_wealth_simulation(
        initial_portfolio, withdrawal_rate, inflation_rate, years, iterations, 
        weight_eq, weight_bd, mu_eq, sig_eq, mu_bd, sig_bd, corr_eq_bd
    )

# ---------------- Dashboard UI ----------------
c1, c2, c3 = st.columns(3)
c1.metric("Probability of Success", f"{success_rate:.1f}%", 
          delta="Safe" if success_rate > 85 else "At Risk", 
          delta_color="normal" if success_rate > 85 else "inverse")
c2.metric("Median Ending Balance", f"${p50[-1]:,.0f}")
c3.metric("Max Drawdown (Median Path)", f"{min(drawdowns)*100:.1f}%", delta_color="inverse")

# --- Chart 1: Portfolio Trajectories ---
fig_traj = go.Figure()

# Plot exactly 100 paths so the browser doesn't freeze rendering SVG lines
display_paths = paths[:100] if len(paths) > 100 else paths
for p in display_paths:
    fig_traj.add_trace(go.Scatter(y=p, mode='lines', line=dict(color='rgba(150, 150, 150, 0.1)'), showlegend=False, hoverinfo='skip'))

x_axis = list(range(years + 1))
fig_traj.add_trace(go.Scatter(x=x_axis, y=p90, mode='lines', name='90th Percentile (Bull)', line=dict(color='#2ECC71', width=3)))
fig_traj.add_trace(go.Scatter(x=x_axis, y=p50, mode='lines', name='50th Percentile (Base)', line=dict(color='#3498DB', width=3)))
fig_traj.add_trace(go.Scatter(x=x_axis, y=p10, mode='lines', name='10th Percentile (Bear)', line=dict(color='#E74C3C', width=3)))

fig_traj.update_layout(title="Simulated Portfolio Trajectories (Adjusted for Inflation)", yaxis_title="Portfolio Balance ($)", hovermode="x unified", legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99))
st.plotly_chart(fig_traj, use_container_width=True)

# --- Chart 2: Drawdown Visualization ---
fig_dd = go.Figure()
fig_dd.add_trace(go.Scatter(x=x_axis, y=drawdowns * 100, mode='lines', fill='tozeroy', name='Drawdown', line=dict(color='#E74C3C', width=2), fillcolor='rgba(231, 76, 60, 0.2)'))
fig_dd.update_layout(title="Psychological Pain: Median Path Drawdowns", yaxis_title="Decline from Peak (%)", xaxis_title="Years in Retirement", hovermode="x unified", yaxis=dict(autorange="reversed"))
st.plotly_chart(fig_dd, use_container_width=True)
