# Wealth Simulator

## Overview
This wealth simulator aids in financial planning and investment strategy by simulating various scenarios.

## Features
- **Zombie Portfolio Bug Fix**: Resolution of issues caused by underperforming asset classes that drain overall returns.
- **Log-Normal Trap Prevention**: Implements checks to prevent assumptions leading to misleading models resulting from log-normal distributions in assets.
- **Inflation Adjustment**: Adjusts investment returns based on current and projected inflation rates to ensure real return calculations.
- **Glide Path Support**: Allows users to set a glide path for asset allocation over time to align with personal risk tolerance and investment horizon.
- **Guardrails Rule**: Incorporates guardrails to limit deviations from predefined risk profiles based on volatility and drawdown thresholds.
- **AI Client Memo Generator**: Generates personalized memos for clients summarizing their investment strategies and projections using AI-driven insights.

## Usage Instructions
1. Initialize the wealth simulator with initial parameters.
2. Simulate different market conditions to observe portfolio performance.
3. Review the generated AI memos for insights on portfolio health and adjustments.

## Example
```python
if __name__ == '__main__':
    simulator = WealthSimulator(initial_investment=100000, investment_years=20)
    simulator.simulate()  # Run the simulation
    print(simulator.generate_report()) # Generate and print the report
    memo = simulator.generate_ai_client_memo()  # Create client memo
    print(memo)
```

## Notes
- Ensure that your Python environment has the necessary packages installed.
- Consider fine-tuning the parameters based on individual financial goals and market outlooks.