# Wealth Simulator

## Overview
The Wealth Simulator is a comprehensive tool designed to assist users in understanding wealth accumulation and distribution, accounting for various economic scenarios and variables.

## Features
- **Zombie Portfolio Fix**: Implements a floor using `np.maximum` for better performance during downturns.
- **Log-Normal Trap Correction**: Applies `np.clip` to ensure returns do not drop below -0.999.
- **Sequence of Returns Handling**: Enhanced depletion tracking for accurate outcomes.
- **Amnesic Guardrails Fix**: Adjusted `base_amount` now persists outside the yearly loop.
- **Safe Anthropic API Integration**: Incorporates a Streamlit secrets check and graceful fallback strategy.
- **Tax Drag Slider**: Allows users to adjust the impact of taxes on positive returns.
- **Accumulation/Distribution Phase Toggle**: Users can switch between accumulation and distribution phases seamlessly.
- **Dynamic Glide Path**: A strategy that reduces volatility over time, adjusting risk profiles as needed.
- **Stress-Test Scenarios**: Includes predefined scenarios like 2008, Dot-Com Boom, Flash Crash, and a customizable option.
- **Inflation-Adjusted Withdrawals**: Ensures withdrawals account for inflation over the desired period.
- **PDF Export with ReportLab**: Users can export their simulation results as PDF documents.
- **Monte Carlo Simulation**: Comprehensive simulation with 2000 iterations for robust data analysis.
- **Full Streamlit UI**: An intuitive user interface featuring hero metrics, visualizations, risk analysis, and an AI client memo generator powered by Claude.

## Usage
To run the Wealth Simulator, ensure all required libraries are installed and execute the Streamlit application. Follow the prompts to input definitions and scenario parameters, then observe the visual representation of your wealth scenarios. 

## Requirements
- Python 3.x
- Streamlit
- NumPy
- pandas
- ReportLab

## Installation
```bash
pip install streamlit numpy pandas reportlab
```

## Running the Application
```bash
streamlit run pages/3_Wealth_Simulator.py
```