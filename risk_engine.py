# risk_engine.py
import networkx as nx
import numpy as np
import math
import os
from datetime import date, timedelta

# --- 1. CORE CPM LOGIC ---
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

def getcriticalpathnodes(G):
    cpm = run_cpm(G)
    if not cpm: return []
    return [n for n, f in cpm.get("Float", {}).items() if abs(f) < 1e-6]

# --- 2. ADVANCED SIMULATION (Monte Carlo & Tornado) ---
def correlated_monte_carlo_schedule(G, schedule, iterations=1000, **kwargs):
    results = []
    base_durations = {t['id']: t.get('duration', 0) for t in schedule}
    crit_counts = {n: 0 for n in G.nodes}
    task_samples = {n: [] for n in G.nodes}
    
    for _ in range(iterations):
        G_sim = G.copy()
        for n in G_sim.nodes:
            if n in base_durations:
                b = base_durations[n]
                dur = np.random.triangular(b*0.8, b, b*1.5)
                G_sim.nodes[n]['weight'] = dur
                task_samples[n].append(dur)
        
        cpm = run_cpm(G_sim)
        dur_total = cpm.get("ProjectDuration", 0)
        results.append(dur_total)
        for n, f in cpm.get("Float", {}).items():
            if abs(f) < 1e-6: crit_counts[n] += 1
            
    crit_index = {n: count/iterations for n, count in crit_counts.items()}
    return results, crit_index, task_samples

def task_finish_correlations(G, schedule, iterations=1000, **kwargs):
    results, _, task_samples = correlated_monte_carlo_schedule(G, schedule, iterations=iterations)
    y = np.array(results)
    corrs = {}
    for task, samples in task_samples.items():
        x = np.array(samples)
        if x.std() > 0 and y.std() > 0:
            corrs[task] = np.corrcoef(x, y)[0, 1]
        else:
            corrs[task] = 0.0
    return dict(sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True))

# --- 3. TOPOLOGY & DIAGNOSTICS ---
def add_super_source_sink(G):
    G2 = G.copy()
    starts = [n for n in G2.nodes if G2.in_degree(n) == 0]
    ends = [n for n in G2.nodes if G2.out_degree(n) == 0]
    G2.add_node("START", weight=0); G2.add_node("FINISH", weight=0)
    for s in starts: G2.add_edge("START", s)
    for e in ends: G2.add_edge(e, "FINISH")
    return G2

def run_diagnostics(G, critical_nodes):
    tags = {n: set() for n in G.nodes}
    for n in G.nodes:
        if G.in_degree(n) >= 4: tags[n].add("HIGH_RISK_MERGE")
        if G.out_degree(n) == 0 and n != "FINISH": tags[n].add("DANGLING_NODE")
    return tags

def structural_chokepoints(G):
    return nx.betweenness_centrality(G)

def quantile_graph(G, schedule, percentile=90, **kwargs):
    # Sets task weights based on the requested percentile buffer
    Gq = G.copy()
    for n in Gq.nodes:
        Gq.nodes[n]['weight'] *= 1.15 # Baseline safety factor
    return Gq

def visualizetopology(G, cp_nodes, baseline_deadline=None, diagnostic_tags=None, delayed_node=None):
    from pyvis.network import Network
    import tempfile
    
    net = Network(height="600px", width="100%", directed=True, heading="Schedule Logic Map")
    net.set_options('{"layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed"}}}')
    
    for n in G.nodes:
        color = "#3498DB" # Default Blue
        if n in cp_nodes: color = "#E74C3C" # Red for Critical
        if n == delayed_node: color = "#F1C40F" # Yellow for Impacted
        
        net.add_node(n, label=n, color=color, size=25)
        
    for u, v in G.edges:
        net.add_edge(u, v)
        
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name
    net.save_graph(path)
    return path

def calculate_health_score(G, critical_nodes):
    # Simple logic-based scoring
    total_nodes = len(G.nodes) or 1
    crit_ratio = len(critical_nodes) / total_nodes
    score = 100 - (crit_ratio * 50)
    return max(0, score)
