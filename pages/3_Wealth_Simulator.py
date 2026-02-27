import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import anthropic

st.set_page_config(layout="wide", page_title="Wealth Simulator")

# ============================================
# BUG FIXES & EDGE CASES
# ============================================

def fix_zombie_portfolio(portfolio_values):
    """
    FIX: Zombie Portfolio Bug
    Ensure portfolio never goes below $0. Once depleted, it stays at $0.
    Prevents mathematically impossible negative balances.
    """
    return np.maximum(portfolio_values, 0)

def log_normal_trap_prevention(annual_returns, volatility):
    """
    FIX: Log-Normal Trap
    For very high volatility, clip returns to realistic bounds.
    A long-only portfolio cannot lose more than 100% in a single year.
    """
    # Generate returns with normal distribution
    returns = np.random.normal(annual_returns, volatility)
    # Clip to realistic bounds: -100% to +infinity
    return np.clip(returns, -0.999, None)

def handle_rapid_depletion(portfolio_value, withdrawal, year, depletion_year_tracker):
    """
    FIX: Sequence of Returns Extreme
    If portfolio hits $0 early, track the depletion year and stop withdrawals.
    """
    if portfolio_value <= 0 and depletion_year_tracker[0] is None:
        depletion_year_tracker[0] = year
    
    if depletion_year_tracker[0] is not None:
        withdrawal = 0  # No more withdrawals after depletion
    
    return withdrawal

# ============================================
# MONTE CARLO SIMULATION ENGINE
# ============================================

@st.cache_data(ttl=300, show_spinner=False)
def run_monte_carlo_wealth(
    initial_value,
    annual_withdrawal,
    mean_return,
    volatility,
    years,
    iterations,
    inflation_rate=0.0,
    use_guardrails=False,
    use_glide_path=False,
    stress_scenario=None
):
    """
    Run Monte Carlo simulation for portfolio value over time.
    
    FEATURE: Inflation-Adjusted Withdrawals
    - Annual withdrawal increases by inflation_rate each year
    
    FEATURE: Dynamic Glide Path
    - Gradually reduce volatility and return as years progress
    
    FEATURE: Guardrails Rule (Guyton-Klinger)
    - If portfolio drops >20%, reduce withdrawal by 10%
    
    FEATURE: Stress-Test Scenarios
    - Inject historical crash into specified year
    """
    
    portfolio_paths = np.zeros((iterations, years + 1))
    portfolio_paths[:, 0] = initial_value
    depletion_years = np.full(iterations, np.nan)
    
    for iteration in range(iterations):
        depletion_tracker = [None]  # Track when this simulation depletes
        previous_value = initial_value
        
        for year in range(1, years + 1):
            # FEATURE: Dynamic Glide Path
            if use_glide_path:
                glide_factor = 1 - (year / years) * 0.5  # Reduce volatility by 50% over time
                current_volatility = volatility * glide_factor
                current_return = mean_return * glide_factor
            else:
                current_volatility = volatility
                current_return = mean_return
            
            # FEATURE: Stress-Test Scenarios
            if stress_scenario and stress_scenario['year'] == year:
                # Inject historical crash
                annual_return = stress_scenario['return']
            else:
                # Generate random return with log-normal trap prevention
                annual_return = log_normal_trap_prevention(current_return, current_volatility)
            
            # Calculate new portfolio value
            portfolio_value = portfolio_paths[iteration, year - 1]
            portfolio_value = portfolio_value * (1 + annual_return)
            
            # FEATURE: Inflation-Adjusted Withdrawals
            inflation_multiplier = (1 + inflation_rate) ** year
            current_withdrawal = annual_withdrawal * inflation_multiplier
            
            # FEATURE: Guardrails Rule (Guyton-Klinger)
            if use_guardrails and year > 1:
                previous_withdrawal = annual_withdrawal * ((1 + inflation_rate) ** (year - 1))
                drawdown = (previous_value - portfolio_value) / previous_value if previous_value > 0 else 0
                
                if drawdown > 0.20:  # Portfolio dropped >20%
                    current_withdrawal = previous_withdrawal * 0.90  # Reduce withdrawal by 10%
            
            # FIX: Handle rapid depletion
            current_withdrawal = handle_rapid_depletion(
                portfolio_value, current_withdrawal, year, depletion_tracker
            )
            
            portfolio_value = portfolio_value - current_withdrawal
            
            # FIX: Zombie Portfolio Bug - floor at 0
            portfolio_value = fix_zombie_portfolio(np.array([portfolio_value]))[0]
            
            portfolio_paths[iteration, year] = portfolio_value
            previous_value = portfolio_value
            
            # Track depletion year
            if depletion_tracker[0] is not None and np.isnan(depletion_years[iteration]):
                depletion_years[iteration] = depletion_tracker[0]
    
    final_values = portfolio_paths[:, -1]
    success_count = np.sum(final_values > 0)
    success_rate = (success_count / iterations) * 100
    
    return portfolio_paths, success_rate, final_values, depletion_years

def calculate_portfolio_stats(portfolio_paths):
    """Calculate comprehensive statistics."""
    final_values = portfolio_paths[:, -1]
    
    stats = {
        'median': np.median(final_values),
        'mean': np.mean(final_values),
        'p10': np.percentile(final_values, 10),
        'p25': np.percentile(final_values, 25),
        'p75': np.percentile(final_values, 75),
        'p90': np.percentile(final_values, 90),
        'min': np.min(final_values),
        'max': np.max(final_values),
    }
    return stats

# ============================================
# AI CLIENT MEMO GENERATOR
# ============================================

@st.cache_data(ttl=3600, show_spinner=False)
def generate_ai_client_memo(
    client_name,
    initial_portfolio,
    annual_withdrawal,
    success_rate,
    p10_value,
    median_value,
    p90_value,
    inflation_rate,
    use_guardrails
):
    """
    FEATURE: AI Client Memo Generator
    Uses Anthropic Claude to generate professional client memo.
    """
    
    try:
        client = anthropic.Anthropic()
        
        prompt = f"""
Generate a professional, plain-English wealth management memo for a client based on these Monte Carlo simulation results:

Client Name: {client_name}
Initial Portfolio: ${initial_portfolio:,.0f}
Annual Withdrawal: ${annual_withdrawal:,.0f}
Inflation Rate: {inflation_rate*100:.1f}%
Success Rate: {success_rate:.1f}%

Projected Final Portfolio Values (after 30 years):
- Pessimistic (P10): ${p10_value:,.0f}
- Median (P50): ${median_value:,.0f}
- Optimistic (P90): ${p90_value:,.0f}

Additional Features:
- Dynamic Guardrails: {'Enabled' if use_guardrails else 'Disabled'}
- Inflation Adjustment: Enabled

Write a professional 3-paragraph memo that:
1. Explains the simulation in simple terms
2. Summarizes the three scenarios (P10, P50, P90)
3. Provides actionable recommendations based on the success rate

Keep it professional, warm, and avoid jargon.
"""
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    
    except Exception as e:
        return f"Error generating memo: {str(e)}"

# ============================================
# STREAMLIT UI
# ============================================

def main():
    st.title("💰 Wealth Simulator - Enterprise Edition")
    st.markdown("Advanced Monte Carlo analysis with inflation, guardrails, glide path, and AI insights.")
    
    # -------- Sidebar Controls --------
    st.sidebar.header("⚙️ Portfolio Parameters")
    
    initial_portfolio = st.sidebar.number_input(
        "Starting Portfolio Value ($)",
        min_value=100000,
        max_value=10000000,
        value=1000000,
        step=50000,
        format="%d"
    )
    
    annual_withdrawal = st.sidebar.number_input(
        "Annual Withdrawal ($)",
        min_value=10000,
        max_value=500000,
        value=50000,
        step=5000,
        format="%d"
    )
    
    mean_return_pct = st.sidebar.slider(
        "Expected Annual Return (%)",
        min_value=0.0,
        max_value=15.0,
        value=7.0,
        step=0.5
    )
    
    volatility_pct = st.sidebar.slider(
        "Annual Volatility (%)",
        min_value=0.0,
        max_value=30.0,
        value=12.0,
        step=1.0
    )
    
    # FEATURE: Inflation Rate
    inflation_pct = st.sidebar.slider(
        "Expected Inflation Rate (%)",
        min_value=0.0,
        max_value=5.0,
        value=2.5,
        step=0.1
    )
    
    # FEATURE: Guardrails Rule
    use_guardrails = st.sidebar.checkbox(
        "Enable Guardrails Rule (Guyton-Klinger)",
        value=False,
        help="Automatically reduces withdrawals by 10% if portfolio drops >20%"
    )
    
    # FEATURE: Dynamic Glide Path
    use_glide_path = st.sidebar.checkbox(
        "Enable Dynamic Glide Path",
        value=False,
        help="Gradually reduce volatility and returns over time"
    )
    
    num_iterations = st.sidebar.number_input(
        "Monte Carlo Iterations",
        min_value=500,
        max_value=5000,
        value=2000,
        step=500
    )
    
    # FEATURE: Stress-Test Scenarios
    st.sidebar.markdown("---")
    st.sidebar.subheader("📉 Stress Test Scenarios")
    
    stress_scenario_type = st.sidebar.selectbox(
        "Select Stress Scenario",
        ["None", "2008 Financial Crisis", "Dot-Com Bubble", "Flash Crash", "Custom"]
    )
    
    stress_scenarios = {
        "None": None,
        "2008 Financial Crisis": {"year": 5, "return": -0.37, "label": "2008 (-37%)"},
        "Dot-Com Bubble": {"year": 3, "return": -0.49, "label": "Dot-Com (-49%)"},
        "Flash Crash": {"year": 7, "return": -0.20, "label": "Flash Crash (-20%)"},
    }
    
    stress_scenario = stress_scenarios.get(stress_scenario_type)
    
    if stress_scenario_type == "Custom":
        stress_year = st.sidebar.slider("Crisis Year", 1, 30, 5)
        stress_return = st.sidebar.slider("Return During Crisis (%)", -80.0, 0.0, -30.0) / 100.0
        stress_scenario = {"year": stress_year, "return": stress_return, "label": f"Year {stress_year} ({stress_return*100:.0f}%)"}
    
    # Convert percentages to decimals
    mean_return = mean_return_pct / 100.0
    volatility = volatility_pct / 100.0
    inflation_rate = inflation_pct / 100.0
    
    # -------- Run Simulation --------
    portfolio_paths, success_rate, final_values, depletion_years = run_monte_carlo_wealth(
        initial_portfolio,
        annual_withdrawal,
        mean_return,
        volatility,
        years=30,
        iterations=num_iterations,
        inflation_rate=inflation_rate,
        use_guardrails=use_guardrails,
        use_glide_path=use_glide_path,
        stress_scenario=stress_scenario
    )
    
    stats = calculate_portfolio_stats(portfolio_paths)
    
    # -------- Hero Metrics --------
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "✅ Success Rate",
            f"{success_rate:.1f}%",
            delta=f"out of {num_iterations} runs",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "💵 Median Final Value",
            f"${stats['median']:,.0f}",
            delta=f"{((stats['median'] / initial_portfolio) - 1) * 100:+.1f}% vs start"
        )
    
    with col3:
        st.metric(
            "📉 P10 (Pessimistic)",
            f"${stats['p10']:,.0f}",
            delta="1-in-10 worst case"
        )
    
    with col4:
        st.metric(
            "📈 P90 (Optimistic)",
            f"${stats['p90']:,.0f}",
            delta="1-in-10 best case"
        )
    
    # -------- Main Visualizations --------
    viz_left, viz_right = st.columns([2, 1])
    
    with viz_left:
        st.subheader("Portfolio Value Over Time")
        
        fig_evolution = go.Figure()
        years_array = np.arange(0, 31)
        
        # Percentile bands
        p10_band = np.percentile(portfolio_paths, 10, axis=0)
        p25_band = np.percentile(portfolio_paths, 25, axis=0)
        p75_band = np.percentile(portfolio_paths, 75, axis=0)
        p90_band = np.percentile(portfolio_paths, 90, axis=0)
        median_band = np.median(portfolio_paths, axis=0)
        
        # P10-P90 shaded band
        fig_evolution.add_trace(go.Scatter(
            x=years_array, y=p90_band,
            fill=None,
            mode='lines',
            line_color='rgba(0,0,0,0)',
            showlegend=False,
        ))
        
        fig_evolution.add_trace(go.Scatter(
            x=years_array, y=p10_band,
            fill='tonexty',
            mode='lines',
            line_color='rgba(0,0,0,0)',
            name='P10-P90 Range',
            fillcolor='rgba(99, 110, 250, 0.2)',
        ))
        
        # P25-P75 shaded band
        fig_evolution.add_trace(go.Scatter(
            x=years_array, y=p75_band,
            fill=None,
            mode='lines',
            line_color='rgba(0,0,0,0)',
            showlegend=False,
        ))
        
        fig_evolution.add_trace(go.Scatter(
            x=years_array, y=p25_band,
            fill='tonexty',
            mode='lines',
            line_color='rgba(0,0,0,0)',
            name='P25-P75 Range',
            fillcolor='rgba(99, 110, 250, 0.4)',
        ))
        
        # Median line
        fig_evolution.add_trace(go.Scatter(
            x=years_array, y=median_band,
            mode='lines',
            name='Median Path',
            line=dict(color='#1E90FF', width=3),
        ))
        
        # Stress scenario annotation
        if stress_scenario:
            fig_evolution.add_vline(
                x=stress_scenario['year'],
                line_dash="dash",
                line_color="red",
                annotation_text=f"Stress: {stress_scenario['label']}",
                annotation_position="top right"
            )
        
        fig_evolution.update_layout(
            hovermode='x unified',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            yaxis_title="Portfolio Value ($)",
            xaxis_title="Years",
            yaxis=dict(tickformat="$,.0f"),
            height=500
        )
        
        st.plotly_chart(fig_evolution, use_container_width=True)
    
    with viz_right:
        st.subheader("Final Value Distribution")
        
        fig_dist = go.Figure()
        
        fig_dist.add_trace(go.Histogram(
            x=final_values,
            nbinsx=50,
            name='Final Values',
            marker_color='#1E90FF',
        ))
        
        # Depletion threshold
        fig_dist.add_vline(
            x=0,
            line_dash="dash",
            line_color="red",
            annotation_text="Portfolio Depleted",
            annotation_position="top right"
        )
        
        fig_dist.update_layout(
            title="Final Portfolio Values",
            xaxis_title="Final Value ($)",
            yaxis_title="Frequency",
            height=500,
            showlegend=False,
            xaxis=dict(tickformat="$,.0f")
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # -------- Outcomes Table --------
    st.subheader("📊 Outcome Summary")
    
    outcomes_df = pd.DataFrame({
        'Scenario': ['P10 (Pessimistic)', 'P25', 'Median (P50)', 'Mean', 'P75', 'P90 (Optimistic)', 'Best Case', 'Worst Case'],
        'Final Value': [
            f"${stats['p10']:,.0f}",
            f"${stats['p25']:,.0f}",
            f"${stats['median']:,.0f}",
            f"${stats['mean']:,.0f}",
            f"${stats['p75']:,.0f}",
            f"${stats['p90']:,.0f}",
            f"${stats['max']:,.0f}",
            f"${stats['min']:,.0f}"
        ],
        'vs Start': [
            f"{((stats['p10'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['p25'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['median'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['mean'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['p75'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['p90'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['max'] / initial_portfolio) - 1) * 100:+.1f}%",
            f"{((stats['min'] / initial_portfolio) - 1) * 100:+.1f}%"
        ]
    })
    
    st.dataframe(outcomes_df, use_container_width=True, hide_index=True)
    
    # -------- Risk Analysis --------
    st.subheader("⚠️ Risk Analysis")
    
    risk_col1, risk_col2, risk_col3 = st.columns(3)
    
    with risk_col1:
        threshold_success = {
            'Portfolio Survives': np.sum(final_values > 0) / len(final_values) * 100,
            'Doubles Initial': np.sum(final_values > initial_portfolio * 2) / len(final_values) * 100,
            'Maintains Initial': np.sum(final_values > initial_portfolio) / len(final_values) * 100,
        }
        
        st.markdown("**Probability of Outcomes:**")
        for outcome, prob in threshold_success.items():
            st.metric(outcome, f"{prob:.1f}%")
    
    with risk_col2:
        depleted_count = np.sum(final_values == 0)
        depletion_rate = (depleted_count / num_iterations) * 100
        
        st.markdown("**Portfolio Depletion:**")
        st.metric("Simulations Depleted", f"{depleted_count} ({depletion_rate:.1f}%)")
        
        valid_depletion_years = depletion_years[~np.isnan(depletion_years)]
        if len(valid_depletion_years) > 0:
            st.metric("Avg Depletion Year", f"{np.mean(valid_depletion_years):.1f}")
        else:
            st.metric("Avg Depletion Year", "N/A (No depletions)")
    
    with risk_col3:
        withdrawal_rate = (annual_withdrawal / initial_portfolio) * 100
        st.markdown("**Withdrawal Metrics:**")
        st.metric("Annual Withdrawal Rate", f"{withdrawal_rate:.2f}%")
        st.metric("Expected Inflation", f"{inflation_pct:.1f}%")
    
    # -------- Key Insights --------
    st.markdown("---")
    st.subheader("💡 Key Insights")
    
    insight_cols = st.columns(2)
    
    with insight_cols[0]:
        if success_rate >= 95:
            st.success(f"✅ Strong Plan: {success_rate:.1f}% success rate indicates high confidence.", icon="✅")
        elif success_rate >= 85:
            st.info(f"⚠️ Moderate Plan: {success_rate:.1f}% success rate. Monitor annually.", icon="ℹ️")
        elif success_rate >= 75:
            st.warning(f"⚠️ At Risk: {success_rate:.1f}% success rate. Consider adjustments.", icon="⚠️")
        else:
            st.error(f"🚨 Critical: {success_rate:.1f}% success rate. Action required.", icon="❌")
    
    with insight_cols[1]:
        withdrawal_pct_safe = 4.0
        if withdrawal_rate <= withdrawal_pct_safe:
            st.success(f"✅ Safe Rate: {withdrawal_rate:.2f}% is within the {withdrawal_pct_safe}% rule.", icon="✅")
        else:
            st.warning(f"🚨 High Rate: {withdrawal_rate:.2f}% exceeds {withdrawal_pct_safe}% threshold.", icon="⚠️")
    
    # -------- AI CLIENT MEMO GENERATOR --------
    st.markdown("---")
    st.subheader("📧 AI Client Memo Generator")
    
    memo_col1, memo_col2 = st.columns([3, 1])
    
    with memo_col1:
        client_name = st.text_input("Client Name", value="Valued Client")
    
    with memo_col2:
        generate_memo = st.button("🤖 Generate AI Memo", use_container_width=True)
    
    if generate_memo:
        with st.spinner("Generating professional memo..."):
            memo = generate_ai_client_memo(
                client_name=client_name,
                initial_portfolio=initial_portfolio,
                annual_withdrawal=annual_withdrawal,
                success_rate=success_rate,
                p10_value=stats['p10'],
                median_value=stats['median'],
                p90_value=stats['p90'],
                inflation_rate=inflation_rate,
                use_guardrails=use_guardrails
            )
            
            st.markdown("### Generated Memo")
            st.markdown(memo)
            
            # Download button
            st.download_button(
                label="📥 Download Memo as Text",
                data=memo,
                file_name=f"wealth_memo_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
