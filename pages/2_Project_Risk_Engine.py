# app.py
import streamlit as st
import json, copy, os, hashlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import date, datetime

# --- CRITICAL FIX: Import from separated files ---
from data_models import schedulesdb
from risk_engine import (
    compilescheduletodigraph, run_cpm, add_super_source_sink,
    correlated_monte_carlo_schedule, getcriticalpathnodes,
    visualizetopology, run_diagnostics, structural_chokepoints,
    quantile_graph, task_finish_correlations, calculate_health_score
)

st.set_page_config(layout="wide", page_title="Vibework Risk Engine")

# --- Custom Styling ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border-left: 4px solid #1E90FF; }
    .metric-card-danger { background-color: #fff0f0; padding: 20px; border-radius: 10px; text-align: center; border-left: 4px solid #FF4B4B; }
</style>
""", unsafe_allow_html=True)

# --- State Helpers ---
class State:
    def __init__(self, schedule, start_date, use_super):
        self.schedule = copy.deepcopy(schedule)
        self.start_date = start_date
        self.use_super = use_super
        self.G = compilescheduletodigraph(self.schedule)
        self.G_super = add_super_source_sink(self.G) if use_super else self.G
        self.cpm = run_cpm(self.G_super)
        self.deadline = float(self.cpm.get("ProjectDuration", 0.0))
        self.sim_results = []
        self.crit_index = {}

    def run_simulation(self, iterations):
        samples, crit = correlated_monte_carlo_schedule(
            self.G, self.schedule, iterations=iterations, 
            start_date=self.start_date, use_super_nodes=self.use_super
        )
        self.sim_results = samples
        self.crit_index = crit

class StateManager:
    def __init__(self, base_sch, start_date, use_super):
        self.A = State(base_sch, start_date, use_super)
        self.B = State(base_sch, start_date, use_super)

# --- Sidebar ---
st.sidebar.header("⚙️ Engine Parameters")
sel_pattern = st.sidebar.selectbox("Select Project Portfolio", list(schedulesdb.keys()))
ld_rate = st.sidebar.number_input("Daily Liquidated Damages ($)", 0, 250000, 15000)
iters = st.sidebar.number_input("Simulations (Monte Carlo)", 100, 10000, 1000)
project_start = st.sidebar.date_input("Project Start Date", date(2026, 1, 1))
use_super = st.sidebar.checkbox("Enable Super Nodes", value=True)

# --- State Management Logic ---
base_sch = schedulesdb[sel_pattern]
base_sch_hash = hashlib.sha256(json.dumps(base_sch).encode()).hexdigest()
state_key = (sel_pattern, project_start.isoformat(), int(iters), bool(use_super), base_sch_hash)

if "sm_key" not in st.session_state or st.session_state.sm_key != state_key:
    st.session_state.sm = StateManager(base_sch, project_start, use_super)
    st.session_state.sm_key = state_key

sm = st.session_state.sm

# --- Main Logic ---
st.title("🏗️ Project Risk & Exposure Engine")

# 1. Baseline Sim
sm.A.run_simulation(iters)
sorted_tasks = sorted([t['id'] for t in sm.A.schedule], key=lambda x: sm.A.crit_index.get(x, 0), reverse=True)

# 2. Scenario Injection
st.markdown("### ⚠️ Scenario Stress-Test")
c_left, c_right = st.columns(2)
with c_left:
    sel_task = st.selectbox("Inject Delay into Task:", sorted_tasks)
with c_right:
    delay = st.slider("Delay Severity (Days):", -10, 30, 0)

sm.B = State(sm.A.schedule, sm.A.start_date, sm.A.use_super)
if delay != 0:
    for t in sm.B.schedule:
        if t["id"] == sel_task:
            t["duration"] = max(0.0, t.get("duration", 0) + delay)
    sm.B = State(sm.B.schedule, sm.B.start_date, sm.B.use_super)

sm.B.run_simulation(iters)

# --- Metrics Visualization ---
p90_ref = np.percentile(sm.A.sim_results, 90) if sm.A.sim_results else 0
p90_curr = np.percentile(sm.B.sim_results, 90) if sm.B.sim_results else 0
exposure = (p90_curr - p90_ref) * ld_rate

st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("P90 Finish (Days)", f"{p90_curr:.1f}", delta=f"{p90_curr - p90_ref:+.1f}")
m2.metric("Mean Finish (Days)", f"{np.mean(sm.B.sim_results):.1f}")
with m3:
    st.markdown(f'<div class="{"metric-card-danger" if exposure > 0 else "metric-card"}"><b>Financial Risk: ${exposure:,.0f}</b></div>', unsafe_allow_html=True)

# --- HTML Topology Cleanup ---
st.subheader("Network Topology Analysis")
html_path = visualizetopology(sm.B.G, getcriticalpathnodes(sm.B.G))
try:
    with open(html_path, 'r') as f:
        components.html(f.read(), height=500)
finally:
    if os.path.exists(html_path): os.remove(html_path)

if st.button("🤖 Generate Flash Report") and delay != 0:
    st.info(f"AI ANALYSIS: Delaying {sel_task} by {delay} days created ${exposure:,.0f} in new financial exposure.")
