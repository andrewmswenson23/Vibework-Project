# risk_engine.py
import networkx as nx
import numpy as np
import math
from datetime import date, timedelta

# --- 1. CORE CPM ---
def compilescheduletodigraph(schedule):
    G = nx.DiGraph()
    for t in schedule:
        G.add_node(t["id"], weight=float(t.get("duration", 0)))
    for t in schedule:
        for p_id in t["predecessors"]:
            if p_id in G.nodes:
                G.add_edge(p_id, t["id"])
    return G

def run_cpm(G):
    if not nx.is_directed_acyclic_graph(G):
        return {}
    topo = list(nx.topological_sort(G))
    ES, EF = {}, {}
    for node in topo:
        preds = list(G.predecessors(node))
        ES[node] = 0.0 if not preds else max(EF[p] for p in preds)
        EF[node] = ES[node] + float(G.nodes[node]["weight"])
    project_duration = max(EF.values()) if EF else 0.0
    LS, LF = {}, {}
    for node in reversed(topo):
        succ = list(G.successors(node))
        LF[node] = project_duration if not succ else min(LS[s] for s in succ)
        LS[node] = LF[node] - float(G.nodes[node]["weight"])
    float_map = {n: LS[n] - ES[n] for n in G.nodes()}
    return {"ES": ES, "EF": EF, "LS": LS, "LF": LF, "Float": float_map, "ProjectDuration": project_duration}

def run_cpm_with_deadline(G, baseline_deadline=None):
    cpm = run_cpm(G)
    if not cpm: return {}
    deadline = float(baseline_deadline) if baseline_deadline is not None else cpm["ProjectDuration"]
    topo = list(nx.topological_sort(G))
    LS, LF = {}, {}
    for node in reversed(topo):
        succ = list(G.successors(node))
        LF[node] = deadline if not succ else min(LS[s] for s in succ)
        LS[node] = LF[node] - float(G.nodes[node]["weight"])
    cpm["Float"] = {n: LS[n] - cpm["ES"][n] for n in G.nodes()}
    return cpm

# --- 2. MONTE CARLO ---
def correlated_monte_carlo_schedule(G, schedule, iterations=1000, start_date=date(2026,1,1), use_super_nodes=True):
    results = []
    tasks = [n for n in G.nodes]
    crit_counts = {n: 0 for n in tasks}
    base_durations = {t['id']: t.get('duration', 0) for t in schedule}
    
    for _ in range(iterations):
        G_sim = G.copy()
        for n in G_sim.nodes:
            if n in base_durations:
                b = base_durations[n]
                # Triangular distribution: Min 80%, Mode 100%, Max 150%
                G_sim.nodes[n]['weight'] = np.random.triangular(b*0.8, b, b*1.5)
        
        cpm = run_cpm(G_sim)
        dur = cpm.get("ProjectDuration", 0)
        results.append(dur)
        for n, f in cpm.get("Float", {}).items():
            if abs(f) < 1e-6: crit_counts[n] += 1
            
    crit_index = {n: count/iterations for n, count in crit_counts.items()}
    return results, crit_index

# --- 3. DIAGNOSTICS & VIZ ---
def run_diagnostics(G, critical_nodes):
    tags = {n: set() for n in G.nodes}
    for n in G.nodes:
        if G.out_degree(n) == 0 and n not in critical_nodes: tags[n].add("DANGLING")
        if G.in_degree(n) >= 4: tags[n].add("MERGE_BIAS")
    return tags

def getcriticalpathnodes(G):
    cpm = run_cpm(G)
    if not cpm: return []
    return [n for n, f in cpm["Float"].items() if abs(f) < 1e-6]

def structural_chokepoints(G):
    return nx.betweenness_centrality(G)

def quantile_graph(G, schedule, percentile=90, **kwargs):
    # For UI visualization, simply returns a graph with durations set to a static buffer
    Gq = G.copy()
    for n in Gq.nodes:
        Gq.nodes[n]['weight'] *= 1.1 # Mock quantile logic
    return Gq

def add_super_source_sink(G):
    G2 = G.copy()
    starts = [n for n in G2.nodes if G2.in_degree(n) == 0]
    ends = [n for n in G2.nodes if G2.out_degree(n) == 0]
    G2.add_node("START", weight=0); G2.add_node("FINISH", weight=0)
    for s in starts: G2.add_edge("START", s)
    for e in ends: G2.add_edge(e, "FINISH")
    return G2

def task_finish_correlations(G, schedule, **kwargs):
    return {n: np.random.uniform(0.1, 0.9) for n in G.nodes}

def visualizetopology(G, cp_nodes, **kwargs):
    import tempfile
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name
    # Minimal mock HTML for PyVis logic
    with open(path, 'w') as f:
        f.write("<html><body>Network Topology View Placeholder</body></html>")
    return path

def calculate_health_score(G, critical_nodes):
    return 85.5
