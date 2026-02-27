import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

# Setting up the Streamlit application
st.title('Wealth Simulator')

# Functionality to manage zombie portfolio bug fix
def fix_zombie_portfolio(portfolio):
    return np.maximum(portfolio, 0)

# Log-normal trap prevention (clipped returns)
def log_normal_trap(returns):
    return np.clip(returns, a_min=None, a_max=1)

# Inflation-adjusted withdrawals
def inflation_adjusted_withdrawals(withdrawal, inflation_rate, years):
    return [withdrawal * ((1 + inflation_rate) ** i) for i in range(years)]

# Dynamic glide path
def dynamic_glide_path(age, retirement_age):
    if age < retirement_age:
        return (retirement_age - age) / (retirement_age)
    return 0

# Guardrails rule
def check_guardrails(investment_value, minimum_value):
    if investment_value < minimum_value:
        st.warning('Investment has fallen below the guardrails threshold!')

# Mock data for simulation
num_iterations = 2000
num_years = 30
initial_investment = 100000
mean_return = 0.07
volatility = 0.15

# Monte Carlo simulation
results = []
for _ in range(num_iterations):
    returns = np.random.normal(mean_return, volatility, num_years)
    returns = log_normal_trap(returns)
    wealth = initial_investment * np.exp(np.cumsum(returns))
    wealth = fix_zombie_portfolio(wealth)
    results.append(wealth)

# Convert simulation results to dataframe for analysis
results_df = pd.DataFrame(results)

# Visualizations
st.subheader('Simulation Results')
plt.figure(figsize=(10,6))
plt.plot(results_df.T, color='blue', alpha=0.1)
plt.title('Monte Carlo Wealth Outcomes')
plt.xlabel('Years')
plt.ylabel('Wealth')
st.pyplot(plt)

# Risk Analysis
mean_wealth = results_df.mean()
std_wealth = results_df.std()

# Print mean and standard deviation
st.subheader('Risk Analysis')
st.write(f'Mean Wealth: ${mean_wealth.iloc[-1]:,.2f}')
st.write(f'Standard Deviation: ${std_wealth.iloc[-1]:,.2f}')

# Stress test scenarios
stress_test_results = []
for stress_case in [0.2, 0.3, 0.4]:  # simulate different adverse scenarios
    adverse_returns = np.random.normal(mean_return - stress_case, volatility, num_years)
    wealth_stress_test = initial_investment * np.exp(np.cumsum(adverse_returns))
    stress_test_results.append(wealth_stress_test)

# Visualize stress test scenarios
plt.figure(figsize=(10,6))
for result in stress_test_results:
    plt.plot(result, color='red', alpha=0.5)
plt.title('Stress Test Scenarios')
plt.xlabel('Years')
plt.ylabel('Wealth')
st.pyplot(plt)

# AI Client Memo Generator
st.subheader('AI Client Memo Generator')
client_memo = st.text_input("Enter client details")
if st.button('Generate Memo'):
    st.write(f'Client Memo for {client_memo}:\n\nYour investment strategy includes dynamic asset allocation and consideration of risk tolerance.')