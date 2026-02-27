# app.py
import streamlit as st
import json, copy, os, hashlib, tempfile
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import date, datetime

from data_models import schedulesdb
import risk_engine as re

st.set_page_config(layout="wide", page_title="Vibework Risk Engine")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border-left: 4px solid #1E90FF; }
    .metric-card-danger { background-color: #fff0f0; padding: 20px; border-radius: 10px; text-align: center; border-left: 4px solid #FF4B4B; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("⚙️ Engine Parameters")
sel_pattern = st.sidebar.selectbox("Project Portfolio", list(schedulesdb.keys()))
ld_rate = st.sidebar.number_input("LD Rate ($/Day)", 0, 100000, 15000)
iters = st.sidebar.number_input("Simulations", 100, 5000, 1000)
project_start = st.sidebar.date_input("Start Date", date(2026, 1, 1))
use_super = st.sidebar.checkbox("Enable Super Nodes", value=True)

# --- STATE MANAGEMENT ---
base_sch = schedulesdb[sel_pattern]
base_hash = hashlib.md5(json.dumps(base_sch).encode()).hexdigest()
state_key = (sel_pattern, iters, project_start.isoformat(), use_super, base_hash)

if "sm_key" not in st.session_state or st.session_state.sm_key != state_key:
    # Initialize baseline graph
    G_base = re.compilescheduletodigraph(base_sch)
    if use_super: G_base = re.add_super_source_sink(G_base)
    
    # Run Baseline Simulation
    results, crit_idx, task_samples = re.correlated_monte_carlo_schedule(G_base, base_sch, iterations=iters)
    
    st.session_state.G = G_base
    st.session_state.baseline_results = results
    st.session_state.crit_index = crit_idx
    st.session_state.sm_key = state_key

# --- UI LOGIC ---
st.title("🏗️ Project Risk & Exposure Engine")
sorted_tasks = sorted(list(st.session_state.G.nodes), key=lambda x: st.session_state.crit_index.get(x, 0), reverse=True)

st.markdown("### ⚠️ Scenario Stress-Test")
c1, c2 = st.columns(2)
with c1:
    sel_task = st.selectbox("Inject Delay into Task:", sorted_tasks)
with c2:
    delay = st.slider("Delay Severity (Days):", -10, 30, 0)

# Run Scenario Simulation
G_scenario = st.session_state.G.copy()
if delay != 0 and sel_task in G_scenario.nodes:
    G_scenario.nodes[sel_task]['weight'] = max(0, G_scenario.nodes[sel_task]['weight'] + delay)

scen_results, scen_crit, _ = re.correlated_monte_carlo_schedule(G_scenario, base_sch, iterations=iters)

# --- METRICS ---
p90_base = np.percentile(st.session_state.baseline_results, 90)
p90_scen = np.percentile(scen_results, 90)
exposure = (p90_scen - p90_base) * ld_rate

st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("P90 Safe Finish (Days)", f"{p90_scen:.1f}", delta=f"{p90_scen - p90_base:+.1f} d", delta_color="inverse")
m2.metric("Mean Expected Finish", f"{np.mean(scen_results):.1f} Days")
with m3:
    card_style = "metric-card-danger" if exposure > 0 else "metric-card"
    st.markdown(f'<div class="{card_style}"><b>💸 Financial Exposure: ${exposure:,.0f}</b></div>', unsafe_allow_html=True)

# --- VISUALIZATIONS ---
st.markdown("---")
left, right = st.columns([3, 2])

with left:
    st.subheader("Network Topology")
    cp_nodes = re.getcriticalpathnodes(G_scenario)
    html_path = re.visualizetopology(G_scenario, cp_nodes, delayed_node=sel_task)
    with open(html_path, 'r') as f:
        components.html(f.read(), height=550)
    os.remove(html_path)

with right:
    st.subheader("Probability Distribution")
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=st.session_state.baseline_results, name="Baseline", marker_color='#3498DB', opacity=0.6))
    fig.add_trace(go.Histogram(x=scen_results, name="Scenario", marker_color='#E74C3C', opacity=0.6))
    fig.update_layout(barmode='overlay', height=550)
    st.plotly_chart(fig, use_container_width=True)

# --- RISK LANDSCAPE (TORNADO) ---
st.markdown("---")
st.subheader("🔎 Risk Landscape")
t1, t2 = st.columns(2)

with t1:
    st.markdown("#### 🌪️ Top Risk Drivers (Correlation)")
    corrs = re.task_finish_correlations(G_scenario, base_sch, iterations=iters//2)
    df_corr = pd.DataFrame([{"Task": k, "Corr": v} for k, v in corrs.items()]).sort_values("Corr", ascending=True).tail(10)
    st.plotly_chart(px.bar(df_corr, x="Corr", y="Task", orientation='h', color_discrete_sequence=['#3498DB']))

with t2:
    st.markdown("#### 🚦 Structural Bottlenecks")
    bc = re.structural_chokepoints(G_scenario)
    df_bc = pd.DataFrame([{"Task": k, "Risk": v} for k, v in bc.items()]).sort_values("Risk", ascending=False).head(10)
    st.plotly_chart(px.bar(df_bc, x="Risk", y="Task", orientation='h', color_discrete_sequence=['#E74C3C']))
