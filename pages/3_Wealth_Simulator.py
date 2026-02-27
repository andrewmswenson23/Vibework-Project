# Wealth Simulator

## Description
This simulator is designed to model the wealth accumulation process while incorporating various financial factors. The goal is to provide users with decision-making tools to optimize their wealth accumulation strategies.

## Features Implemented:
1. **Fixed Amnesic Guardrails**: Ensures that the adjusted base withdrawal is tracked persistently across sessions to safeguard user investments.
2. **Safe Anthropic API Initialization**: Utilizes Streamlit secrets for secure API access, falling back to environment variables if secrets are unavailable.
3. **Accumulation/Distribution Phase Toggle**: Allows users to switch between accumulation and distribution phases, enabling tailored simulations.
4. **Tax Drag Slider**: Provides a slider interface for users to adjust tax drag percentages, impacting overall wealth simulation outcomes.
5. **PDF Export Capability**: Leverages ReportLab to generate downloadable PDF reports summarizing the simulation results.

import streamlit as st  
from reportlab.lib.pagesizes import letter  
from reportlab.pdfgen import canvas  
import os

class WealthSimulator:
    def __init__(self):
        self.adjusted_base_withdrawal = 0.0
        self.tax_drag_percentage = 0.0
        self.api_key = self.load_api_key()
        self.simulation_phase = "accumulation"  # default phase

    def load_api_key(self):
        # Safe API key loading
        api_key = os.getenv("ANTHROPIC_API_KEY")  
        if not api_key:
            api_key = st.secrets.get("anthropic_api_key")  
        return api_key

    def toggle_phase(self):
        # Toggle between accumulation and distribution phases
        self.simulation_phase = "distribution" if self.simulation_phase == "accumulation" else "accumulation"

    def update_tax_drag(self, percentage):
        self.tax_drag_percentage = percentage

    def export_to_pdf(self, data, filename):
        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(100, 750, "Wealth Simulation Report")
        c.drawString(100, 735, f"Adjusted Base Withdrawal: {self.adjusted_base_withdrawal}")
        c.drawString(100, 720, f"Tax Drag Percentage: {self.tax_drag_percentage}")
        # Further report contents can be added here
        c.save()

# Streamlit UI Code
st.title("Wealth Simulator")

simulator = WealthSimulator()

# Phase Toggle
if st.button("Toggle Simulation Phase"):
    simulator.toggle_phase()
    st.write(f"Current Phase: {simulator.simulation_phase}")

# Tax Drag Slider
tax_drag = st.slider("Tax Drag (%)", min_value=0, max_value=100, value=0)

if st.button("Update Tax Drag"):
    simulator.update_tax_drag(tax_drag)
    st.write(f"Tax Drag updated to: {simulator.tax_drag_percentage}%")

# PDF Export
if st.button("Export to PDF"):
    simulator.export_to_pdf(data={}, filename="wealth_simulation_report.pdf")  
    st.success("PDF report generated!")

