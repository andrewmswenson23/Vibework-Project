import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class WealthSimulator:
    def __init__(self, initial_investment, annual_contribution, years, 
                 annual_return_rate, inflation_rate):
        self.initial_investment = initial_investment
        self.annual_contribution = annual_contribution
        self.years = years
        self.annual_return_rate = annual_return_rate
        self.inflation_rate = inflation_rate

    def simulate(self, num_simulations):
        results = []
        for _ in range(num_simulations):
            total_wealth = self.initial_investment
            wealth_over_time = []
            for year in range(self.years):
                annual_growth = total_wealth * np.random.normal(self.annual_return_rate, 0.1)
                total_wealth += annual_growth + self.annual_contribution
                wealth_over_time.append(total_wealth)
            results.append(wealth_over_time)
        return np.array(results) 

    def plot_results(self, results):
        plt.figure(figsize=(10, 6))
        for simulation in results:
            plt.plot(simulation, alpha=0.1)
        plt.title('Wealth Simulation Over Time')
        plt.xlabel('Years')
        plt.ylabel('Total Wealth')
        plt.grid()
        plt.show()

    def generate_client_memo(self, final_wealth):
        memo = f"Dear Client,\n\n" 
        memo += f"After conducting a Monte Carlo simulation, your projected wealth is: ${final_wealth:,.2f}.\n" 
        memo += "The simulation took into account inflation and market variability.\n\n" 
        return memo

# Simulation parameters
initial_investment = 100000
annual_contribution = 15000
years = 30
annual_return_rate = 0.07
inflation_rate = 0.03
num_simulations = 1000

# Run simulation
simulator = WealthSimulator(initial_investment, annual_contribution, years, annual_return_rate, inflation_rate)
results = simulator.simulate(num_simulations)

# Plot results
simulator.plot_results(results)

# Generate client memo
final_wealth = results[-1].mean()
client_memo = simulator.generate_client_memo(final_wealth)
print(client_memo)