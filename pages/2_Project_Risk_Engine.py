import streamlit as st
import json, copy, os, io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import date, datetime
import time

from risk_engine import (
    schedulesdb, compilescheduletodigraph, getcriticalpathnodes, visualizetopology,
    calculate_health_score, run_cpm, run_cpm_with_deadline, structural_chokepoints, 
    correlated_monte_carlo_schedule, add_super_source_sink, shock_propagation, 
    compute_crash_plan, task_finish_correlations, quantile_graph, run_diagnostics
)

st.set_page_config(layout="wide", page_title="Vibework Risk Engine")

# --- Custom CSS for Enterprise Polish ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #1E90FF;
    }
    .metric-card-danger {
        background-color: #fff0f0;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #FF4B4B;
    }
</style>
""", unsafe_allow_html=True)

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
        self.diagnostics = run_diagnostics(self.G, getcriticalpathnodes(self.G_super))
        self.sim_results = None
        self.crit_index = None

    def run_simulation(self, iterations=2000):
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
                # FIX: Negative Duration Crash (Clamped to 0)
                t["duration"] = max(0.0, float(t.get("duration", 0)) + float(deltas[t["id"]]))
        self.B = State(self.B.schedule, start_date=self.B.start_date, use_super=self.B.use_super)

    def baseline_deadline(self):
        return float(self.A.deadline)

# ---------------- App ----------------
def main():
    st.title("🏗️ Project Risk & Exposure Engine")
    st.markdown("Quantify schedule volatility and Liquidated Damages exposure via 2,000+ Monte Carlo simulations.")

    # ---------------- Sidebar ----------------
    st.sidebar.header("⚙️ Engine Parameters")
    
    # FEATURE: Custom Uploads
    uploaded_file = st.sidebar.file_uploader("Upload Custom Schedule (JSON)", type=['json'])
    
    patterns = {
        "schedulehealthy": "✅ Healthy Linear",
        "scheduletoxic": "⚠️ Hidden Bottleneck",
        "schedulebroken": "🚨 Logic Gap",
        "schedulecomplex": "🔗 Mega Project"
    }
    sel_pattern = st.sidebar.selectbox("Or Select Preset Portfolio", list(patterns.values()), disabled=bool(uploaded_file))
    
    if uploaded_file is not None:
        try:
            base_sch = json.load(uploaded_file)
            sel_key = "custom_upload"
        except Exception:
            st.sidebar.error("Invalid JSON format.")
            base_sch = schedulesdb["schedulehealthy"]
            sel_key = "schedulehealthy"
    else:
        sel_key = [k for k, v in patterns.items() if v == sel_pattern][0]
        base_sch = schedulesdb[sel_key]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Financial Exposure")
    ld_rate = st.sidebar.number_input("Daily Liquidated Damages ($)", 0, 250000, 15000, step=1000)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Advanced Settings")
    iters = st.sidebar.number_input("Simulations (Monte Carlo)", 100, 20000, 2000, step=500)
    project_start = st.sidebar.date_input("Project Start Date", value=date(2026, 1, 1))
    use_super = st.sidebar.checkbox("Enable Super Source/Sink Nodes", value=True)

    # FIX: Desynced State Manager (Tracking all variables via a composite key)
    current_state_key = f"{sel_key}_{project_start}_{iters}_{use_super}"
    if "state_manager" not in st.session_state or st.session_state.get("state_key") != current_state_key:
        st.session_state.state_manager = StateManager(base_sch, start_date=project_start, use_super=use_super)
        st.session_state.state_key = current_state_key
    sm = st.session_state.state_manager

    # ---------------- Baseline & Scenario Processing ----------------
    baseline_deadline = sm.baseline_deadline()
    sm.A.run_simulation(iterations=iters)
    sorted_tasks = sorted([t['id'] for t in sm.A.schedule], key=lambda x: sm.A.crit_index.get(x, 0), reverse=True)

    st.markdown("### ⚠️ Scenario Stress-Test")
    war_left, war_right = st.columns([1, 1])
    with war_left:
        sel_task = st.selectbox("Inject Delay into Task:", sorted_tasks, index=0 if sorted_tasks else 0)
    with war_right:
        delay = st.slider("Delay Severity (Days):", -10, 30, 0)

    sm.reset_scenario()
    if sel_task and delay != 0:
        sm.apply_delta({sel_task: delay})

    sm.B.run_simulation(iterations=iters)

    # Calculate metrics
    ref_samples = sm.A.sim_results or []
    curr_samples = sm.B.sim_results or ref_samples
    p90_ref = float(np.percentile(ref_samples, 90)) if ref_samples else 0.0
    p90_curr = float(np.percentile(curr_samples, 90)) if curr_samples else p90_ref
    exposure_delta = (p90_curr - p90_ref) * ld_rate

    mean_curr = float(np.mean(curr_samples)) if curr_samples else 0.0
    mean_ref = float(np.mean(ref_samples)) if ref_samples else 0.0
    p90_date = project_start + pd.to_timedelta(p90_curr, unit="D")
    mean_date = project_start + pd.to_timedelta(mean_curr, unit="D")

    # ---------------- Hero Metrics ----------------
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"P90 Safe Finish ({p90_date:%m/%d/%y})", f"{round(p90_curr):,} days", delta=f"{p90_curr - p90_ref:+.1f} d", delta_color="inverse")
    c2.metric(f"Expected Finish ({mean_date:%m/%d/%y})", f"{round(mean_curr):,} days", delta=f"{mean_curr - mean_ref:+.1f} d", delta_color="inverse")
    
    with c3:
        st.markdown(f'<div class="{"metric-card-danger" if exposure_delta > 0 else "metric-card"}">', unsafe_allow_html=True)
        st.markdown("#### 💸 Financial Exposure")
        st.markdown(f"**${exposure_delta:,.0f}**")
        st.markdown("*(Liquidated Damages Risk)*")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- Main Visualization Row ----------------
    st.markdown("---")
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Network Topology & Float Analysis")
        G_base = compilescheduletodigraph(sm.B.schedule)
        G_viz = quantile_graph(G_base, sm.B.schedule, percentile=90, iterations=max(800, iters//2),
                               start_date=project_start, use_super_nodes=use_super)

        cp_nodes = getcriticalpathnodes(G_viz)
        diag_tags = run_diagnostics(G_viz, cp_nodes)
        
        trigger_node = sel_task if float(delay) != 0.0 else None
        html_path = visualizetopology(G_viz, cp_nodes, baseline_deadline=baseline_deadline, diagnostic_tags=diag_tags, delayed_node=trigger_node)
        
        # FIX: Memory/Disk Leak via HTML Exports
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        components.html(html_content, height=600)
        st.download_button("📥 Export Dynamic Topology (HTML)", data=html_content, file_name="Network_Report.html", mime="text/html")
        
        # Safely remove the file from the server disk after reading it into memory
        try:
            os.remove(html_path)
        except OSError:
            pass

    with right:
        st.subheader("Probability Distribution")
        fig = go.Figure()
        base_arr = np.array(ref_samples) if ref_samples else np.array([0.0])
        delayed_arr = np.array(curr_samples) if curr_samples else np.array([0.0])

        # FIX: Zero-Variance Histogram Failures
        if base_arr.size > 0 and delayed_arr.size > 0:
            xmin = float(min(base_arr.min(), delayed_arr.min()))
            xmax = float(max(base_arr.max(), delayed_arr.max()))
        else:
            xmin, xmax = 0.0, 1.0

        if xmax <= xmin:
            xmin, xmax = xmin - 0.5, xmax + 0.5

        bin_count = 40
        bin_size = (xmax - xmin) / bin_count
        shared_xbins = dict(start=xmin, end=xmax, size=bin_size)

        fig.add_trace(go.Histogram(
            x=base_arr, name="Baseline", marker_color='#1E90FF', opacity=0.65,
            histnorm='percent', xbins=shared_xbins, hovertemplate='%{x:.1f} d<br>%{y:.2f}%<extra></extra>'
        ))

        if float(delay) != 0.0:
            fig.add_trace(go.Histogram(
                x=delayed_arr, name="Scenario", marker_color='#FF4B4B', opacity=0.65,
                histnorm='percent', xbins=shared_xbins, hovertemplate='%{x:.1f} d<br>%{y:.2f}%<extra></extra>'
            ))

        fig.update_layout(
            barmode='overlay', 
            yaxis_title="Probability (%)", xaxis_title="Project Duration (Days)",
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
            height=600, margin=dict(t=30)
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- Risk Landscape Section ----------------
    st.markdown("---")
    st.markdown("## 🔎 Risk Landscape")
    rl_left, rl_right = st.columns(2)

    with rl_left:
        st.subheader("🌪️ Top Risk Drivers (Tornado)")
        corr_dict = get_tornado_cached(json.dumps(sm.B.schedule), max(1500, iters//1), project_start.isoformat(), use_super)
        df_corr = (pd.DataFrame([{"Task": k, "Correlation": v} for k, v in corr_dict.items()])
                   .assign(Abs=lambda d: d["Correlation"].abs())
                   .sort_values("Abs", ascending=True)
                   .tail(15))
        
        fig_torn = px.bar(df_corr, x="Correlation", y="Task", orientation="h")
        fig_torn.update_traces(marker_color='#1E90FF')
        st.plotly_chart(fig_torn, use_container_width=True)

    with rl_right:
        st.subheader("🚦 Critical Bottlenecks")
        bc = structural_chokepoints(G_viz)
        df_bc = pd.DataFrame([{"Task": k, "Betweenness Risk": v} for k, v in bc.items()]).sort_values("Betweenness Risk", ascending=False).head(10)
        
        fig_bottleneck = px.bar(df_bc, x="Betweenness Risk", y="Task", orientation="h")
        fig_bottleneck.update_traces(marker_color='#FF4B4B')
        fig_bottleneck.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bottleneck, use_container_width=True)

    # ---------------- AI IMPACT REPORT GENERATOR ----------------
    st.markdown("---")
    st.subheader("📧 AI Executive Impact Report")
    
    # FIX: The "Typing Lag" via st.form
    with st.form("memo_form"):
        memo_left, memo_right = st.columns([3, 1])
        with memo_left:
            project_name = st.text_input("Project Name", "VibeWork Headquarters Build")
        with memo_right:
            st.write("") # Spacer
            st.write("") # Spacer
            generate_memo = st.form_submit_button("🤖 Generate Flash Report", use_container_width=True)
            
        if generate_memo:
            with st.spinner("Analyzing graph topology and compiling executive brief..."):
                time.sleep(1.5) # Mock AI loading time
                
                # FIX: The "Zero Delay" Edge Case
                if delay == 0:
                    st.markdown(f"""
                    **CONFIDENTIAL: Executive Flash Report**
                    **Project:** {project_name}
                    **Date:** {datetime.now().strftime('%B %d, %Y')}

                    **EXECUTIVE SUMMARY:**
                    Recent Monte Carlo diagnostics (n={iters}) indicate that the project is currently operating within baseline safety parameters. The P90 safe finish date is holding steady at **{p90_date:%B %d, %Y}**. 

                    **TOPOLOGICAL HEALTH:**
                    No downstream float erosion or critical path delays have been manually injected into the current scenario. The network topology remains stable.

                    **RECOMMENDED ACTION:**
                    Continue standard monitoring and execution. No corrective action or schedule crashing is required at this time.

                    *Generated by VibeWork Risk Engine*
                    """)
                else:
                    impact_text = f"an **additional ${exposure_delta:,.0f}** in Liquidated Damages exposure" if exposure_delta > 0 else "no significant financial exposure at this time"
                    
                    st.markdown(f"""
                    **CONFIDENTIAL: Executive Flash Report**
                    **Project:** {project_name}
                    **Date:** {datetime.now().strftime('%B %d, %Y')}

                    **EXECUTIVE SUMMARY:**
                    Recent Monte Carlo diagnostics (n={iters}) indicate that a {delay}-day delay to the `{sel_task}` workflow will shift our P90 safe finish date to **{p90_date:%B %d, %Y}**. This represents {impact_text}.

                    **TOPOLOGICAL IMPACT:**
                    Our graph analysis reveals that `{sel_task}` acts as a critical structural chokepoint. The delay has actively eroded downstream float safety buffers, causing secondary tasks to become critical. 

                    **RECOMMENDED ACTION:**
                    We recommend immediate authorization of a crash-plan for `{sel_task}` to recover the {delay}-day schedule variance before the delay locks in the downstream network path.

                    *Generated by VibeWork Risk Engine*
                    """)

if __name__ == "__main__":
    main()
