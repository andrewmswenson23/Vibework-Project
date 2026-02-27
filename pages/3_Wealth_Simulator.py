import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

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
    returns = np.random.normal(annual_returns, volatility)
    return np.clip(returns, -0.999, None)

def handle_rapid_depletion(portfolio_value, withdrawal, year, depletion_year_tracker):
    """
    FIX: Sequence of Returns Extreme
    If portfolio hits $0 early, track the depletion year and stop withdrawals.
    """
    if portfolio_value <= 0 and depletion_year_tracker[0] is None:
        depletion_year_tracker[0] = year
    
    if depletion_year_tracker[0] is not None:
        withdrawal = 0
    
    return withdrawal

# ============================================
# MONTE CARLO SIMULATION ENGINE
# ============================================

@st.cache_data(ttl=300, show_spinner=False)
def run_monte_carlo_wealth(
    initial_value,
    annual_amount,
    mean_return,
    volatility,
    years,
    iterations,
    inflation_rate=0.0,
    use_guardrails=False,
    use_glide_path=False,
    stress_scenario=None,
    phase="distribution",
    tax_drag=0.0
):
    """
    FIX: Amnesic Guardrails
    - Track adjusted_base_withdrawal OUTSIDE the loop
    - Permanent reduction when guardrails trigger
    
    FEATURE: Accumulation vs Distribution Toggle
    - Accumulation: Add money each year
    - Distribution: Withdraw money each year
    
    FEATURE: Tax Drag
    - Reduces positive returns by tax drag percentage
    """
    
    portfolio_paths = np.zeros((iterations, years + 1))
    portfolio_paths[:, 0] = initial_value
    depletion_years = np.full(iterations, np.nan)
    guardrail_triggers = np.zeros(iterations, dtype=int)
    
    for iteration in range(iterations):
        # FIX: Initialize adjusted base OUTSIDE yearly loop for persistent tracking
        adjusted_base_amount = annual_amount
        depletion_tracker = [None]
        previous_value = initial_value
        guardrail_triggered_this_iteration = False
        
        for year in range(1, years + 1):
            # FEATURE: Dynamic Glide Path
            if use_glide_path:
                glide_factor = 1 - (year / years) * 0.5
                current_volatility = volatility * glide_factor
                current_return = mean_return * glide_factor
            else:
                current_volatility = volatility
                current_return = mean_return
            
            # FEATURE: Stress-Test Scenarios
            if stress_scenario and stress_scenario['year'] == year:
                annual_return = stress_scenario['return']
            else:
                annual_return = log_normal_trap_prevention(current_return, current_volatility)
            
            # FEATURE: Tax Drag Implementation
            # Only apply tax drag to positive returns
            if annual_return > 0:
                annual_return = annual_return * (1 - tax_drag)
            
            # Calculate new portfolio value
            portfolio_value = portfolio_paths[iteration, year - 1]
            portfolio_value = portfolio_value * (1 + annual_return)
            
            # Calculate amount (withdrawal or contribution)
            inflation_multiplier = (1 + inflation_rate) ** year
            
            # FIX: Use adjusted_base_amount instead of original annual_amount
            current_amount = adjusted_base_amount * inflation_multiplier
            
            # FEATURE: Guardrails Rule (FIX: Persistent Memory)
            if use_guardrails and year > 1 and not guardrail_triggered_this_iteration:
                drawdown = (previous_value - portfolio_value) / previous_value if previous_value > 0 else 0
                
                if drawdown > 0.20:
                    # FIX: Permanently reduce the adjusted base for all future years
                    adjusted_base_amount *= 0.90
                    current_amount = adjusted_base_amount * inflation_multiplier
                    guardrail_triggered_this_iteration = True
                    guardrail_triggers[iteration] = year
            
            # FEATURE: Apply amount based on phase
            if phase == "distribution":
                # Withdrawal phase
                current_amount = handle_rapid_depletion(
                    portfolio_value, current_amount, year, depletion_tracker
                )
                portfolio_value = portfolio_value - current_amount
            else:
                # Accumulation phase
                portfolio_value = portfolio_value + current_amount
            
            # FIX: Zombie Portfolio Bug
            portfolio_value = fix_zombie_portfolio(np.array([portfolio_value]))[0]
            
            portfolio_paths[iteration, year] = portfolio_value
            previous_value = portfolio_value
            
            if depletion_tracker[0] is not None and np.isnan(depletion_years[iteration]):
                depletion_years[iteration] = depletion_tracker[0]
    
    final_values = portfolio_paths[:, -1]
    success_count = np.sum(final_values > 0) if phase == "distribution" else np.sum(final_values > initial_value)
    success_rate = (success_count / iterations) * 100
    guardrail_trigger_rate = (np.sum(guardrail_triggers > 0) / iterations) * 100
    
    return portfolio_paths, success_rate, final_values, depletion_years, guardrail_trigger_rate

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
# AI CLIENT MEMO GENERATOR (Safe API Integration)
# ============================================

# ============================================
# AI CLIENT MEMO GENERATOR (Fireworks AI Integration)
# ============================================

@st.cache_data(ttl=3600, show_spinner=False)
def generate_ai_client_memo(
    client_name,
    initial_portfolio,
    annual_amount,
    success_rate,
    p10_value,
    median_value,
    p90_value,
    inflation_rate,
    use_guardrails,
    phase,
    guardrail_trigger_rate
):
    """
    FEATURE: Safe Fireworks AI Integration
    - Uses OpenAI python client pointed at Fireworks base URL
    - Check Streamlit secrets first
    - Graceful fallback if API key missing
    """

    try:
        # Safely fetch API key from Streamlit secrets
        api_key = st.secrets.get("FIREWORKS_API_KEY")
        if not api_key:
            return """
⚠️ **Setup Required**

The AI memo generator requires a Fireworks API key to be configured in Streamlit secrets.

To set up:
1. Get an API key from [Fireworks AI](https://fireworks.ai/)
2. Add it to your Streamlit secrets: `FIREWORKS_API_KEY = "your-key-here"`
3. Restart the app

For now, here is a template memo:

---

Dear {client_name},

Thank you for entrusting us with your financial planning. Based on our Monte Carlo analysis of your {phase} strategy over 30 years, here are the key findings:

**Projected Outcomes:**
- Conservative Case (P10): ${p10_value:,.0f}
- Expected Case (P50): ${median_value:,.0f}
- Optimistic Case (P90): ${p90_value:,.0f}

**Success Rate: {success_rate:.1f}%**

This analysis incorporates inflation adjustments and market volatility. We recommend reviewing this plan annually and adjusting as market conditions change.

Best regards,
Your Wealth Management Team
            """.format(
                client_name=client_name,
                phase=phase,
                p10_value=p10_value,
                median_value=median_value,
                p90_value=p90_value,
                success_rate=success_rate
            )
        
        # Fireworks AI uses the standard OpenAI python package
        from openai import OpenAI
        
        client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=api_key
        )
        
        phase_text = "accumulation" if phase == "accumulation" else "retirement/distribution"
        
        prompt = f"""
Generate a professional, plain-English wealth management memo for a client based on these Monte Carlo simulation results:

Client Name: {client_name}
Initial Portfolio: ${initial_portfolio:,.0f}
Annual {phase.title()}: ${annual_amount:,.0f}
Phase: {phase_text}
Inflation Rate: {inflation_rate*100:.1f}%
Success Rate: {success_rate:.1f}%
Guardrails Active: {'Yes (triggered {:.1f}% of scenarios)'.format(guardrail_trigger_rate) if use_guardrails else 'No'}

Projected Final Portfolio Values (after 30 years):
- Conservative (P10): ${p10_value:,.0f}
- Expected (P50): ${median_value:,.0f}
- Optimistic (P90): ${p90_value:,.0f}

Write a professional 3-paragraph memo that:
1. Explains the simulation methodology in simple terms
2. Summarizes the three scenarios and what they mean
3. Provides actionable recommendations

Keep it professional, warm, and avoid jargon.
"""
        
        # Call the Llama 3 70B Instruct model via Fireworks
        response = client.chat.completions.create(
            model="accounts/fireworks/models/llama-v3p1-70b-instruct",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    except ImportError:
        return "⚠️ Error: openai library not installed. Install with: `pip install openai` and add it to requirements.txt"
    except Exception as e:
        return f"⚠️ Error generating memo: {str(e)}\n\nMake sure your FIREWORKS_API_KEY is properly configured in Streamlit secrets."

# ============================================
# PDF EXPORT (Goldman Polish)
# ============================================

def generate_pdf_report(
    client_name,
    initial_portfolio,
    annual_amount,
    phase,
    success_rate,
    stats,
    memo_text,
    fig_evolution_data
):
    """
    FEATURE: PDF Export
    Combines simulation results, charts, and AI memo into professional PDF.
    """
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1E90FF'),
            spaceAfter=30,
            alignment=1  # Center
        )
        elements.append(Paragraph(f"VibeWork AI Wealth Simulator Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Client Info
        info_data = [
            ["Client Name:", client_name],
            ["Initial Portfolio:", f"${initial_portfolio:,.0f}"],
            ["Annual Amount:", f"${annual_amount:,.0f}"],
            ["Phase:", phase.title()],
            ["Report Date:", datetime.now().strftime("%B %d, %Y")]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Results Summary
        elements.append(Paragraph("Portfolio Projection Summary", styles['Heading2']))
        
        results_data = [
            ["Metric", "Value"],
            ["Success Rate", f"{success_rate:.1f}%"],
            ["P10 (Conservative)", f"${stats['p10']:,.0f}"],
            ["P50 (Expected)", f"${stats['median']:,.0f}"],
            ["P90 (Optimistic)", f"${stats['p90']:,.0f}"],
        ]
        
        results_table = Table(results_data, colWidths=[3*inch, 2*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E90FF')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(results_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # AI Memo
        elements.append(PageBreak())
        elements.append(Paragraph("AI-Generated Client Memo", styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        memo_style = ParagraphStyle(
            'MemoText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14
        )
        elements.append(Paragraph(memo_text.replace('\n', '<br/>'), memo_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None

# ============================================
# STREAMLIT UI
# ============================================

def main():
    st.title("💰 Wealth Simulator - Enterprise Edition")
    st.markdown("Advanced Monte Carlo analysis with inflation, guardrails, glide path, tax drag, and AI insights.")
    
    # -------- Sidebar Controls --------
    st.sidebar.header("⚙️ Portfolio Parameters")
    
    # FEATURE: Phase Toggle
    phase = st.sidebar.radio(
        "Financial Phase",
        ["distribution", "accumulation"],
        format_func=lambda x: "🏖️ Distribution (Retirement)" if x == "distribution" else "📈 Accumulation (Growth)",
        help="Distribution: Withdraw from portfolio. Accumulation: Add to portfolio."
    )
    
    initial_portfolio = st.sidebar.number_input(
        "Starting Portfolio Value ($)",
        min_value=100000,
        max_value=10000000,
        value=1000000,
        step=50000,
        format="%d"
    )
    
    annual_amount_label = "Annual Withdrawal ($)" if phase == "distribution" else "Annual Contribution ($)"
    annual_amount = st.sidebar.number_input(
        annual_amount_label,
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
    
    inflation_pct = st.sidebar.slider(
        "Expected Inflation Rate (%)",
        min_value=0.0,
        max_value=5.0,
        value=2.5,
        step=0.1
    )
    
    # FEATURE: Tax Drag Slider
    tax_drag_pct = st.sidebar.slider(
        "Tax Drag (% of positive returns)",
        min_value=0.0,
        max_value=3.0,
        value=0.5,
        step=0.1,
        help="Typically 0.5-1.5% for taxable accounts. 0% for retirement accounts (401k, IRA)."
    )
    
    use_guardrails = st.sidebar.checkbox(
        "Enable Guardrails Rule (Guyton-Klinger)",
        value=False,
        help="Reduces withdrawals by 10% if portfolio drops >20% in a year"
    )
    
    use_glide_path = st.sidebar.checkbox(
        "Enable Dynamic Glide Path",
        value=False,
        help="Gradually reduce risk/returns over time"
    )
    
    num_iterations = st.sidebar.number_input(
        "Monte Carlo Iterations",
        min_value=500,
        max_value=5000,
        value=2000,
        step=500
    )
    
    # Stress Test
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
    
    # Convert percentages
    mean_return = mean_return_pct / 100.0
    volatility = volatility_pct / 100.0
    inflation_rate = inflation_pct / 100.0
    tax_drag = tax_drag_pct / 100.0
    
    # -------- Run Simulation --------
    portfolio_paths, success_rate, final_values, depletion_years, guardrail_trigger_rate = run_monte_carlo_wealth(
        initial_portfolio,
        annual_amount,
        mean_return,
        volatility,
        years=30,
        iterations=num_iterations,
        inflation_rate=inflation_rate,
        use_guardrails=use_guardrails,
        use_glide_path=use_glide_path,
        stress_scenario=stress_scenario,
        phase=phase,
        tax_drag=tax_drag
    )
    
    stats = calculate_portfolio_stats(portfolio_paths)
    
    # -------- Hero Metrics --------
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "✅ Success Rate",
            f"{success_rate:.1f}%",
            delta=f"out of {num_iterations} runs"
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
        
        p10_band = np.percentile(portfolio_paths, 10, axis=0)
        p25_band = np.percentile(portfolio_paths, 25, axis=0)
        p75_band = np.percentile(portfolio_paths, 75, axis=0)
        p90_band = np.percentile(portfolio_paths, 90, axis=0)
        median_band = np.median(portfolio_paths, axis=0)
        
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
        
        fig_evolution.add_trace(go.Scatter(
            x=years_array, y=median_band,
            mode='lines',
            name='Median Path',
            line=dict(color='#1E90FF', width=3),
        ))
        
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
        
        if phase == "distribution":
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
        if phase == "distribution":
            threshold_success = {
                'Portfolio Survives': np.sum(final_values > 0) / len(final_values) * 100,
                'Doubles Initial': np.sum(final_values > initial_portfolio * 2) / len(final_values) * 100,
                'Maintains Initial': np.sum(final_values > initial_portfolio) / len(final_values) * 100,
            }
        else:
            threshold_success = {
                'Doubles Initial': np.sum(final_values > initial_portfolio * 2) / len(final_values) * 100,
                'Triples Initial': np.sum(final_values > initial_portfolio * 3) / len(final_values) * 100,
                '5x Initial': np.sum(final_values > initial_portfolio * 5) / len(final_values) * 100,
            }
        
        st.markdown("**Probability of Outcomes:**")
        for outcome, prob in threshold_success.items():
            st.metric(outcome, f"{prob:.1f}%")
    
    with risk_col2:
        if phase == "distribution":
            depleted_count = np.sum(final_values == 0)
            depletion_rate = (depleted_count / num_iterations) * 100
            
            st.markdown("**Portfolio Depletion:**")
            st.metric("Simulations Depleted", f"{depleted_count} ({depletion_rate:.1f}%)")
            
            valid_depletion_years = depletion_years[~np.isnan(depletion_years)]
            if len(valid_depletion_years) > 0:
                st.metric("Avg Depletion Year", f"{np.mean(valid_depletion_years):.1f}")
            else:
                st.metric("Avg Depletion Year", "N/A")
        else:
            st.markdown("**Growth Metrics:**")
            st.metric("Average Final Value", f"${stats['mean']:,.0f}")
            st.metric("Std Deviation", f"${np.std(final_values):,.0f}")
    
    with risk_col3:
        if phase == "distribution":
            withdrawal_rate = (annual_amount / initial_portfolio) * 100
            st.markdown("**Withdrawal Metrics:**")
            st.metric("Annual Withdrawal Rate", f"{withdrawal_rate:.2f}%")
        else:
            contribution_rate = (annual_amount / initial_portfolio) * 100
            st.markdown("**Contribution Metrics:**")
            st.metric("Annual Contribution Rate", f"{contribution_rate:.2f}%")
        
        st.metric("Tax Drag", f"{tax_drag_pct:.2f}%")
        
        if use_guardrails:
            st.metric("Guardrails Trigger Rate", f"{guardrail_trigger_rate:.1f}%")
    
    # -------- Key Insights --------
    st.markdown("---")
    st.subheader("💡 Key Insights")
    
    insight_cols = st.columns(2)
    
    with insight_cols[0]:
        if success_rate >= 95:
            st.success(f"✅ Strong Plan: {success_rate:.1f}% success rate.", icon="✅")
        elif success_rate >= 85:
            st.info(f"⚠️ Moderate Plan: {success_rate:.1f}% success rate.", icon="ℹ️")
        elif success_rate >= 75:
            st.warning(f"⚠️ At Risk: {success_rate:.1f}% success rate.", icon="⚠️")
        else:
            st.error(f"🚨 Critical: {success_rate:.1f}% success rate.", icon="❌")
    
    with insight_cols[1]:
        if phase == "distribution":
            withdrawal_rate = (annual_amount / initial_portfolio) * 100
            if withdrawal_rate <= 4.0:
                st.success(f"✅ Safe Rate: {withdrawal_rate:.2f}% is within the 4% rule.", icon="✅")
            else:
                st.warning(f"🚨 High Rate: {withdrawal_rate:.2f}% exceeds 4% threshold.", icon="⚠️")
    
    # -------- AI CLIENT MEMO GENERATOR --------
    st.markdown("---")
    st.subheader("📧 AI Client Memo Generator")
    
    memo_col1, memo_col2 = st.columns([3, 1])
    
    with memo_col1:
        client_name = st.text_input("Client Name", value="Valued Client")
    
    with memo_col2:
        generate_memo = st.button("🤖 Generate AI Memo", use_container_width=True)
    
    memo_text = None
    if generate_memo:
        with st.spinner("Generating professional memo..."):
            memo_text = generate_ai_client_memo(
                client_name=client_name,
                initial_portfolio=initial_portfolio,
                annual_amount=annual_amount,
                success_rate=success_rate,
                p10_value=stats['p10'],
                median_value=stats['median'],
                p90_value=stats['p90'],
                inflation_rate=inflation_rate,
                use_guardrails=use_guardrails,
                phase=phase,
                guardrail_trigger_rate=guardrail_trigger_rate
            )
            
            st.markdown("### Generated Memo")
            st.markdown(memo_text)
            
            # Download Text
            st.download_button(
                label="📥 Download Memo as Text",
                data=memo_text,
                file_name=f"wealth_memo_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )
            
            # FEATURE: Download PDF Report
            pdf_buffer = generate_pdf_report(
                client_name=client_name,
                initial_portfolio=initial_portfolio,
                annual_amount=annual_amount,
                phase=phase,
                success_rate=success_rate,
                stats=stats,
                memo_text=memo_text,
                fig_evolution_data=None
            )
            
            if pdf_buffer:
                st.download_button(
                    label="📄 Download Full PDF Report",
                    data=pdf_buffer,
                    file_name=f"VibeWork_Wealth_Report_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    main()
