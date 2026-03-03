import streamlit as st
import json, copy, os, io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import date

from risk_engine import (
    schedulesdb, compilescheduletodigraph, getcriticalpathnodes, visualizetopology,
    calculate_health_score, run_cpm, run_cpm_with_deadline, structural_chokepoints, 
    correlated_monte_carlo_schedule, add_super_source_sink, shock_propagation, 
    compute_crash_plan, task_finish_correlations, quantile_graph, run_diagnostics
)

st.set_page_config(layout="wide", page_title="Vibework Risk Engine")

# ---------------- Cached Helpers ----------------
@st.cache_data(ttl=300, show_spinner=False)
def run_simulation_advanced_cached(schedule_json, iterations, start_date_iso, use_super):
    schedule = json.loads(schedule_json)
    G = compilescheduletodigraph(schedule)
    samples, crit_index = correlated_monte_carlo_schedule(
        G, schedule, iterations=int(iterations),
        start_date=date.fromisoformat(start_date_iso), use_super_nodes=bool(use_super)
    )
    p90 = float(np.percentile(samples, 90)) if samples else 0.0
    return samples, p90, {n: v * 100 for n, v in crit_index.items()}

@st.cache_data(ttl=300, show_spinner=False)
def get_tornado_cached(schedule_json, iters, start_date_iso, use_super):
    sch = json.loads(schedule_json)
    G = compilescheduletodigraph(sch)
    return task_finish_correlations(G, sch, iterations=int(iters), start_date=date.fromisoformat(start_date_iso), use_super_nodes=use_super)

# ---------------- State Machine ----------------
class State:
    def __init__(self, schedule, start_date=date(2026, 1, 1), use_super=True):
        self.schedule = copy.deepcopy(schedule)
        self.start_date = start_date
        self.use_super = use_super
        self.G = compilescheduletodigraph(self.schedule)
        self.G_super = add_super_source_sink(self.G) if self.use_super else self.G
        self.cpm = run_cpm(self.G_super)
        self.deadline = float(self.cpm.get("ProjectDuration", 0.0))
        # Ensure diagnostics run on raw graph so dangling nodes are found
        self.diagnostics = run_diagnostics(self.G, getcriticalpathnodes(self.G_super))
        self.sim_results = None
        self.crit_index = None

    def run_simulation(self, iterations=2000):
        # Prevent freeze by utilizing the cached logic
        samples, p90, crit_index = run_simulation_advanced_cached(
            json.dumps(self.schedule), int(iterations), self.start_date.isoformat(), self.use_super
        )
        self.sim_results = samples
        self.crit_index = crit_index
        return samples, crit_index

class StateManager:
    def __init__(self, baseline_schedule, start_date=date(2026, 1, 1), use_super=True):
        self.A = State(baseline_schedule, start_date=start_date, use_super=use_super)
        self.B = State(baseline_schedule, start_date=start_date, use_super=use_super)

    def reset_scenario(self):
        self.B = State(self.A.schedule, start_date=self.A.start_date, use_super=self.A.use_super)

    def apply_delta(self, deltas):
        for t in self.B.schedule:
            if t["id"] in deltas:
                t["duration"] = float(t.get("duration", 0)) + float(deltas[t["id"]])
        self.B = State(self.B.schedule, start_date=self.B.start_date, use_super=self.B.use_super)

    def baseline_deadline(self):
        return float(self.A.deadline)

# ---------------- App ----------------
def main():
    st.title("🏗️ Project Risk & Exposure Engine")

    # ---------------- Sidebar ----------------
    st.sidebar.header("Settings")
    patterns = {
        "schedulehealthy": "✅ Healthy Linear",
        "scheduletoxic": "⚠️ Hidden Bottleneck",
        "schedulebroken": "🚨 Logic Gap",
        "schedulecomplex": "🔗 Mega Project"
    }
    sel_pattern = st.sidebar.selectbox("Pattern", list(patterns.values()))
    sel_key = [k for k, v in patterns.items() if v == sel_pattern][0]
    base_sch = schedulesdb[sel_key]

    iters = st.sidebar.number_input("Simulations", 100, 20000, 2000, step=500)
    ld_rate = st.sidebar.number_input("Daily LD ($)", 0, 250000, 15000, step=1000)
    project_start = st.sidebar.date_input("Project Start", value=date(2026, 1, 1))

    use_super = True

    # Initialize StateManager and track pattern changes so UI updates on dropdown select
    if "state_manager" not in st.session_state or st.session_state.get("current_pattern") != sel_pattern:
        st.session_state.state_manager = StateManager(base_sch, start_date=project_start, use_super=use_super)
        st.session_state.current_pattern = sel_pattern
    sm = st.session_state.state_manager

    # ---------------- Prepare baseline artifacts ----------------
    baseline_deadline = sm.baseline_deadline()
    sm.A.run_simulation(iterations=iters)
    sorted_tasks = sorted([t['id'] for t in sm.A.schedule], key=lambda x: sm.A.crit_index.get(x, 0), reverse=True)

    war_left, war_right = st.columns([1, 1])
    with war_left:
        sel_task = st.selectbox("Stress-Test Task", sorted_tasks, index=0 if sorted_tasks else 0)
    with war_right:
        delay = st.slider("Delay (Days)", -10, 30, 0)

    sm.reset_scenario()
    if sel_task and delay != 0:
        sm.apply_delta({sel_task: delay})

    sm.B.run_simulation(iterations=iters)

    ref_samples = sm.A.sim_results or []
    curr_samples = sm.B.sim_results or ref_samples
    p90_ref = float(np.percentile(ref_samples, 90)) if ref_samples else 0.0
    p90_curr = float(np.percentile(curr_samples, 90)) if curr_samples else p90_ref
    exposure_delta = (p90_curr - p90_ref) * ld_rate

    mean_curr = float(np.mean(curr_samples)) if curr_samples else 0.0
    mean_ref = float(np.mean(ref_samples)) if ref_samples else 0.0
    p90_date = project_start + pd.to_timedelta(p90_curr, unit="D")
    mean_date = project_start + pd.to_timedelta(mean_curr, unit="D")

    # ---------------- Hero metrics ----------------
    c1, c2, c3 = st.columns(3)
    c1.metric(f"P90 Finish ({p90_date:%m/%d/%y})", f"{round(p90_curr):,} days", delta=f"{p90_curr - p90_ref:+.1f} d")
    c2.metric(f"Expected Finish ({mean_date:%m/%d/%y})", f"{round(mean_curr):,} days", delta=f"{mean_curr - mean_ref:+.1f} d")
    c3.metric("Delay Cost (vs Base P90)", f"${exposure_delta:,.0f}", delta_color="inverse")

    # Health scores computed against baseline
    G_for_health_B = compilescheduletodigraph(sm.B.schedule)
    try:
        G_health_B = quantile_graph(G_for_health_B, sm.B.schedule, percentile=90, iterations=max(400, iters//4),
                                    start_date=project_start, use_super_nodes=use_super)
        cp_nodes_health_B = getcriticalpathnodes(G_health_B)
        health_B = calculate_health_score(G_health_B, cp_nodes_health_B)
    except Exception:
        cp_nodes_health_B = getcriticalpathnodes(G_for_health_B)
        health_B = calculate_health_score(G_for_health_B, cp_nodes_health_B)

    st.markdown(f"**Health Score (Scenario):** {health_B:.1f} / 100 • **Baseline Deadline:** {baseline_deadline:.1f} d")

    # ---------------- Main Visualization Row ----------------
    left, right = st.columns([3, 2])
    with left:
        G_base = compilescheduletodigraph(sm.B.schedule)
        # Hardcode 90th percentile to avoid radio button clutter
        G_viz = quantile_graph(G_base, sm.B.schedule, percentile=90, iterations=max(800, iters//2),
                               start_date=project_start, use_super_nodes=use_super)

        cp_nodes = getcriticalpathnodes(G_viz)
        
        # Compute diagnostic tags using the RAW graph so dangling nodes are correctly identified
        diag_tags = run_diagnostics(G_viz, cp_nodes)
        
        # Pass the delayed task to the visualizer so it can be highlighted
        trigger_node = sel_task if float(delay) != 0.0 else None
        html_path = visualizetopology(G_viz, cp_nodes, baseline_deadline=baseline_deadline, diagnostic_tags=diag_tags, delayed_node=trigger_node)
        
        with open(html_path, 'r', encoding='utf-8') as f:
            components.html(f.read(), height=650)
        st.download_button("📥 Export Topology", open(html_path, 'rb'), "Report.html", "text/html")

    with right:
        fig = go.Figure()
        base_arr = np.array(ref_samples) if ref_samples else np.array([0.0])
        delayed_arr = np.array(curr_samples) if curr_samples else np.array([0.0])

        xmin = float(min(base_arr.min(), delayed_arr.min()))
        xmax = float(max(base_arr.max(), delayed_arr.max()))
        if xmax <= xmin:
            xmin, xmax = xmin - 0.5, xmax + 0.5

        # Force identical bins so areas perfectly match
        bin_count = 40
        bin_size = (xmax - xmin) / bin_count
        shared_xbins = dict(start=xmin, end=xmax, size=bin_size)

        fig.add_trace(go.Histogram(
            x=base_arr, name="Base", marker_color='#1E90FF', opacity=0.65,
            histnorm='percent', xbins=shared_xbins, hovertemplate='%{x:.1f} d<br>%{y:.2f}%<extra></extra>'
        ))

        if float(delay) != 0.0:
            fig.add_trace(go.Histogram(
                x=delayed_arr, name="Delayed", marker_color='#FF4B4B', opacity=0.65,
                histnorm='percent', xbins=shared_xbins, hovertemplate='%{x:.1f} d<br>%{y:.2f}%<extra></extra>'
            ))

        fig.update_layout(
            barmode='overlay', title="Probability of Finish Dates",
            yaxis_title="Probability (%)", xaxis_title="Project Duration (Days)",
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- Risk Landscape Section ----------------
    st.markdown("## 🔎 Risk Landscape")
    rl_left, rl_right = st.columns(2)

    with rl_left:
        st.subheader("🌪️ Top Risk Drivers")
        corr_dict = get_tornado_cached(json.dumps(sm.B.schedule), max(1500, iters//1), project_start.isoformat(), use_super)
        df_corr = (pd.DataFrame([{"Task": k, "Correlation": v} for k, v in corr_dict.items()])
                   .assign(Abs=lambda d: d["Correlation"].abs())
                   .sort_values("Abs", ascending=True)
                   .tail(20))
        st.plotly_chart(px.bar(df_corr, x="Correlation", y="Task", orientation="h"), use_container_width=True)

    with rl_right:
        st.subheader("🚦 Traffic Bottlenecks")
        bc = structural_chokepoints(G_viz)
        df_bc = pd.DataFrame([{"Task": k, "Betweenness": v} for k, v in bc.items()]).sort_values("Betweenness", ascending=False).head(10)
        st.plotly_chart(px.bar(df_bc, x="Betweenness", y="Task", orientation="h"), use_container_width=True)

    # ---------------- War Room Impact Summary ----------------
    G_tmp = compilescheduletodigraph(sm.B.schedule)
    delta_sp = float(delay) if float(delay) > 0 else 0.0
    res = shock_propagation(G_tmp, sel_task, delta_sp, baseline_deadline=baseline_deadline) if delta_sp > 0 else {
        "BaselineDuration": sm.A.cpm.get("ProjectDuration", 0.0),
        "NewDuration": sm.B.cpm.get("ProjectDuration", 0.0),
        "FloatErosion": {}
    }

    wr_left, wr_right = st.columns([1, 1])
    with wr_left:
        st.subheader("Impact Summary")
        st.metric("P90 (New)", f"{round(p90_curr):,} days", delta=f"{p90_curr - p90_ref:+.1f} d")
        st.metric("Delay Cost", f"${exposure_delta:,.0f}")
        st.markdown(f"**Baseline Deadline:** {baseline_deadline:.1f} d  \n**New Simulated Duration:** {res.get('NewDuration', 0.0):.1f} d")

    with wr_right:
        st.subheader("Lost Safety Buffers (The Domino Effect)")
        eros = pd.DataFrame([{"Task": k, "Lost Buffer (Days)": v} for k, v in res.get("FloatErosion", {}).items()])
        if not eros.empty:
            st.plotly_chart(
                px.bar(eros.sort_values("Lost Buffer (Days)", ascending=False).head(12),
                       x="Lost Buffer (Days)", y="Task", orientation="h"),
                use_container_width=True
            )
        else:
            st.info("No downstream safety buffer was lost for this scenario.")

if __name__ == "__main__":
    main()
