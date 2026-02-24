import networkx as nx
import numpy as np
import random
import math
from datetime import date, timedelta


# Try optional deps (graceful fallback)
try:
   from scipy.stats import norm, beta as beta_dist
   SCIPY_AVAILABLE = True
except Exception:
   SCIPY_AVAILABLE = False


# --- 1. DATA PATTERNS ---
schedule_healthy = [
   {"id": "A", "duration": 10, "predecessors": []},
   {"id": "B", "duration": 15, "predecessors": ["A"]},
   {"id": "C", "duration": 12, "predecessors": ["B"]},
   {"id": "D", "duration": 20, "predecessors": ["C"]}
]
schedule_toxic = [
   {"id": "T1", "duration": 5, "predecessors": []},
   {"id": "T2", "duration": 10, "predecessors": ["T1"]},
   {"id": "T3", "duration": 5, "predecessors": ["T1"]},
   {"id": "T4", "duration": 2, "predecessors": ["T2"]},
   {"id": "T5", "duration": 1, "predecessors": ["T3"]}
]
schedule_broken = [
   {"id": "Project_Kickoff", "duration": 2, "predecessors": []},
   {"id": "Geotech_Testing", "duration": 10, "predecessors": ["Project_Kickoff"]},
   {"id": "Structural_Drafting", "duration": 15, "predecessors": ["Geotech_Testing"]},
   {"id": "Zoning_Review", "duration": 20, "predecessors": ["Project_Kickoff"]},
   {"id": "Alt_Design_Phase_1", "duration": 12, "predecessors": ["Project_Kickoff"]},
   {"id": "Alt_Design_Phase_2", "duration": 8, "predecessors": ["Alt_Design_Phase_1"]},
   {"id": "Fiber_Optic_Sublet", "duration": 14, "predecessors": ["Zoning_Review"]},
   {"id": "Foundation_Pour", "duration": 10, "predecessors": ["Structural_Drafting", "Zoning_Review"]},
   {"id": "Superstructure", "duration": 25, "predecessors": ["Foundation_Pour"]},
   {"id": "Preliminary_Grading", "duration": 5, "predecessors": ["Geotech_Testing"]},
   {"id": "Site_Drainage_Mockup", "duration": 7, "predecessors": ["Preliminary_Grading"]},
   {"id": "Enclosure", "duration": 15, "predecessors": ["Superstructure"]},
   {"id": "Interior_Fitout", "duration": 20, "predecessors": ["Enclosure"]},
   {"id": "Commissioning", "duration": 10, "predecessors": ["Interior_Fitout"]},
   {"id": "Final_Handover", "duration": 0, "predecessors": ["Commissioning"]}
]
schedule_complex = [
   {"id": "Permitting", "duration": 30, "predecessors": []},
   {"id": "Site_Survey", "duration": 10, "predecessors": ["Permitting"]},
   {"id": "Foundation_Design", "duration": 15, "predecessors": ["Site_Survey"]},
   {"id": "Utility_Mapping", "duration": 12, "predecessors": ["Site_Survey"]},
   {"id": "Excavation", "duration": 20, "predecessors": ["Foundation_Design"]},
   {"id": "Concrete_Pour", "duration": 10, "predecessors": ["Excavation"]},
   {"id": "Steel_Procurement", "duration": 45, "predecessors": ["Permitting"]},
   {"id": "Steel_Erection", "duration": 25, "predecessors": ["Steel_Procurement", "Concrete_Pour"]},
   {"id": "Roofing", "duration": 15, "predecessors": ["Steel_Erection"]},
   {"id": "HVAC_Rough_In", "duration": 20, "predecessors": ["Steel_Erection"]},
   {"id": "Electrical_Main", "duration": 18, "predecessors": ["Utility_Mapping", "Steel_Erection"]},
   {"id": "Plumbing_Main", "duration": 15, "predecessors": ["Excavation"]},
   {"id": "Interior_Walls", "duration": 12, "predecessors": ["HVAC_Rough_In", "Electrical_Main", "Plumbing_Main"]},
   {"id": "Windows_Install", "duration": 10, "predecessors": ["Roofing"]},
   {"id": "Ext_Finishes", "duration": 20, "predecessors": ["Windows_Install"]},
   {"id": "Painting", "duration": 8, "predecessors": ["Interior_Walls"]},
   {"id": "Flooring", "duration": 10, "predecessors": ["Painting"]},
   {"id": "IT_Cabling", "duration": 12, "predecessors": ["Interior_Walls"]},
   {"id": "Server_Install", "duration": 15, "predecessors": ["IT_Cabling", "Electrical_Main"]},
   {"id": "Fire_Alarm", "duration": 10, "predecessors": ["Interior_Walls"]},
   {"id": "Landscaping", "duration": 14, "predecessors": ["Ext_Finishes"]},
   {"id": "Paving", "duration": 7, "predecessors": ["Ext_Finishes"]},
   {"id": "Security_Check", "duration": 5, "predecessors": ["Server_Install", "Fire_Alarm"]},
   {"id": "Furniture_Fittings", "duration": 10, "predecessors": ["Flooring"]},
   {"id": "Final_Cleanup", "duration": 5, "predecessors": ["Furniture_Fittings", "Painting"]},
   {"id": "Comm_Testing", "duration": 12, "predecessors": ["Final_Cleanup", "Security_Check"]},
   {"id": "Owner_Walkthrough", "duration": 3, "predecessors": ["Comm_Testing", "Landscaping", "Paving"]},
   {"id": "Punch_List", "duration": 10, "predecessors": ["Owner_Walkthrough"]},
   {"id": "Cert_Occupancy", "duration": 5, "predecessors": ["Punch_List"]},
   {"id": "Project_Closeout", "duration": 2, "predecessors": ["Cert_Occupancy"]}
]


schedulesdb = {
   "schedulehealthy": schedule_healthy,
   "scheduletoxic": schedule_toxic,
   "schedulebroken": schedule_broken,
   "schedulecomplex": schedule_complex
}


# --- 2. CORE CPM FUNCTIONS ---
def compilescheduletodigraph(schedule):
   G = nx.DiGraph()
   id_to_task = {t["id"]: t for t in schedule}
   for t in schedule:
       G.add_node(t["id"], weight=float(t.get("duration", 0)))
   for t in schedule:
       for p_id in t["predecessors"]:
           if p_id in id_to_task:
               G.add_edge(p_id, t["id"])
   return G


def check_for_cycles(G):
   if not nx.is_directed_acyclic_graph(G):
       try:
           return nx.find_cycle(G, orientation="original")
       except Exception:
           return True
   return None


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
   if not nx.is_directed_acyclic_graph(G):
       return {}
   topo = list(nx.topological_sort(G))
   ES, EF = {}, {}
   for node in topo:
       preds = list(G.predecessors(node))
       ES[node] = 0.0 if not preds else max(EF[p] for p in preds)
       EF[node] = ES[node] + float(G.nodes[node]["weight"])
   project_duration = max(EF.values()) if EF else 0.0


   deadline = float(baseline_deadline) if baseline_deadline is not None else project_duration


   LS, LF = {}, {}
   for node in reversed(topo):
       succ = list(G.successors(node))
       LF[node] = deadline if not succ else min(LS[s] for s in succ)
       LS[node] = LF[node] - float(G.nodes[node]["weight"])


   float_map = {n: LS[n] - ES[n] for n in G.nodes()}
   return {"ES": ES, "EF": EF, "LS": LS, "LF": LF, "Float": float_map, "ProjectDuration": project_duration}


def criticalpathlength(G):
   cpm = run_cpm(G)
   return cpm.get("ProjectDuration", 0.0)


def getcriticalpathnodes(G):
   cpm = run_cpm(G)
   if not cpm:
       return []
   finish_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
   if not finish_nodes:
       return []
   end = max(finish_nodes, key=lambda n: cpm["EF"].get(n, 0.0))
   path = [end]
   cur = end
   EPS = 1e-6
   while True:
       preds = list(G.predecessors(cur))
       candidates = [
           p for p in preds
           if abs(cpm["EF"].get(p, -1) - cpm["ES"].get(cur, -2)) <= EPS
           and abs(cpm["Float"].get(p, 1)) <= EPS
       ]
       if not candidates:
           break
       cur = max(candidates, key=lambda n: cpm["EF"].get(n, 0.0))
       path.append(cur)
   return list(reversed(path))


# --- 3. HEALTH / RISK METRICS ---
def calculate_health_score(G, critical_nodes):
   N = G.number_of_nodes()
   if N == 0:
       return 0.0
   terminal_node = critical_nodes[-1] if critical_nodes else None
   dangling_count = len([n for n in G.nodes() if G.out_degree(n) == 0 and n != terminal_node])
   R_D = dangling_count / N
   P_D = 1.0 - math.exp(-15.0 * R_D)
   rho = sum(dict(G.in_degree()).values()) / N
   if rho < 1.0:
       P_rho = (1.0 - rho)
   elif rho > 1.5:
       P_rho = 1.0 - math.exp(-(rho - 1.5))
   else:
       P_rho = 0.0
   score = 100.0 * (1.0 - P_D) * (1.0 - P_rho ** 2)
   return max(0.0, min(100.0, score))


def calculate_risk_index(G, cpm):
   if not cpm:
       return 0.0
   total_nodes = G.number_of_nodes() or 1
   critical_nodes = [n for n, f in cpm["Float"].items() if abs(f) <= 1e-6]
   critical_ratio = len(critical_nodes) / total_nodes
   density = nx.density(G)
   high_dependency_nodes = [n for n in G.nodes() if G.out_degree(n) >= 3]
   fragility = len(high_dependency_nodes) / total_nodes
   risk = 100.0 * (0.5 * critical_ratio + 0.3 * density + 0.2 * fragility)
   return float(min(100.0, risk))


# --- 4. STRUCTURAL INTELLIGENCE ---
def structural_diagnostics(G):
   starts = [n for n in G.nodes() if G.in_degree(n) == 0]
   finishes = [n for n in G.nodes() if G.out_degree(n) == 0]
   components = list(nx.weakly_connected_components(G))
   disconnected = len(components) > 1
   orphans = [n for n in G.nodes() if G.in_degree(n) == 0 and n in finishes and G.out_degree(n) == 0]
   return {"StartNodes": starts, "FinishNodes": finishes, "Disconnected": disconnected, "Orphans": orphans}


def structural_chokepoints(G):
   try:
       bc = nx.betweenness_centrality(G, normalized=True)
   except Exception:
       bc = {n: 0.0 for n in G.nodes()}
   return bc


def merge_bias(G, threshold=3):
   fanin = {n: G.in_degree(n) for n in G.nodes()}
   bias = {n: d for n, d in fanin.items() if d >= threshold}
   return bias, fanin


def add_super_source_sink(G):
   G2 = G.copy()
   start_nodes = [n for n in G2.nodes() if G2.in_degree(n) == 0]
   finish_nodes = [n for n in G2.nodes() if G2.out_degree(n) == 0]
   if "SUPER_START" not in G2:
       G2.add_node("SUPER_START", weight=0.0)
   if "SUPER_FINISH" not in G2:
       G2.add_node("SUPER_FINISH", weight=0.0)
   for s in start_nodes:
       if s != "SUPER_START":
           G2.add_edge("SUPER_START", s)
   for f in finish_nodes:
       if f != "SUPER_FINISH":
           G2.add_edge(f, "SUPER_FINISH")
   return G2


# --- 4b. DIAGNOSTIC ENGINE (Semantic Tags) ---
def run_diagnostics(G, critical_nodes=None):
   tags = {n: set() for n in G.nodes()}
   finish_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
   terminal = critical_nodes[-1] if critical_nodes else (finish_nodes[0] if finish_nodes else None)


   for n in G.nodes():
       if G.out_degree(n) == 0 and n != terminal:
           tags[n].add("DANGLING_NODE")
       if G.in_degree(n) >= 4:
           tags[n].add("HIGH_RISK_MERGE")
       if G.in_degree(n) == 0 and G.out_degree(n) == 0:
           tags[n].add("ORPHAN")


   comps = list(nx.weakly_connected_components(G))
   if len(comps) > 1:
       main = max(comps, key=len)
       for comp in comps:
           if comp is not main:
               for n in comp:
                   tags[n].add("LOGIC_GAP")
   return tags


# --- 5. VISUALIZATION ---
def visualizetopology(G, critical_nodes=None, output_file="topology.html", baseline_deadline=None, diagnostic_tags=None, delayed_node=None):
   from pyvis.network import Network
   G2 = add_super_source_sink(G)
  
   cpm = run_cpm_with_deadline(G2, baseline_deadline) if baseline_deadline is not None else run_cpm(G2)
   float_map = cpm.get("Float", {})
   bc = structural_chokepoints(G2)


   net = Network(height="700px", width="100%", directed=True)


   # Force left-to-right hierarchical PERT layout, disable bouncy physics
   net.set_options("""
   var options = {
     "layout": { "hierarchical": { "enabled": true, "direction": "LR", "sortMethod": "directed", "nodeSpacing": 150, "levelSeparation": 250 } },
     "physics": { "enabled": false }
   }
   """)


   if diagnostic_tags is None:
       diagnostic_tags = run_diagnostics(G, critical_nodes)


   for n in G2.nodes():
       if n in ("SUPER_START", "SUPER_FINISH"):
           continue
          
       w = float(G2.nodes[n]["weight"])
       f = float_map.get(n, 0.0)
       bc_val = bc.get(n, 0.0)
       node_tags = diagnostic_tags.get(n, set())
      
       is_trigger = (n == delayed_node)
      
       # 1. ULTRA-MINIMALIST COLORS
       if is_trigger:
           bg_color = "#E74C3C" # Bold Red (The task you are delaying)
           border_color = "#C0392B"
           font_color = "white"
       else:
           bg_color = "#3498DB" # Clean Corporate Blue (Everything else)
           border_color = "#2980B9"
           font_color = "white"


       # 2. DIAGNOSTIC SHAPES (Kept for structural warnings)
       shape = 'dot'
       if "DANGLING_NODE" in node_tags: shape = 'triangle'
       elif "HIGH_RISK_MERGE" in node_tags: shape = 'hexagon'
       elif "LOGIC_GAP" in node_tags: shape = 'square'


       tooltip = (
           f"<b>{n}</b><br>"
           f"Duration: {w:.1f}d<br>"
           f"Float: {f:.1f}<br>"
           f"Tags: {', '.join(sorted(node_tags)) if node_tags else 'None'}"
       )
      
       size = 24 + 10 * bc_val
       if is_trigger: size *= 1.5 # Make the delayed task slightly bigger
      
       net.add_node(
           n, label=n, title=tooltip, shape=shape, size=size, borderWidth=2,
           color={"background": bg_color, "border": border_color, "highlight": {"background": bg_color, "border": "#2C3E50"}},
           font={"color": font_color, "size": 14, "face": "sans-serif", "bold": is_trigger}
       )


   for u, v in G2.edges():
       if u in ("SUPER_START", "SUPER_FINISH") or v in ("SUPER_START", "SUPER_FINISH"):
           continue
       net.add_edge(u, v, color="#BDC3C7") # Light gray, clean lines


   net.save_graph(output_file)
  
   # Clean, minimal legend
   health = calculate_health_score(G2, [n for n, f in float_map.items() if abs(f) <= 1e-6])
   risk = calculate_risk_index(G2, cpm)
   legend = f"""
   <div style="position: absolute; top: 15px; left: 15px; padding: 12px;
   background: white; border: 2px solid #ECF0F1; z-index: 999;
   font-family: sans-serif; font-size: 13px; border-radius: 8px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
   <div style="margin-bottom: 5px;"><b>Health Score:</b> {health:.1f}/100</div>
   <div style="margin-bottom: 10px;"><b>Risk Index:</b> {risk:.1f}/100</div>
   <hr style="margin: 5px 0; border-top: 1px solid #ECF0F1;">
   <div style="color:#E74C3C; font-weight: bold;">● Delayed Task</div>
   <div style="color:#3498DB;">● Standard Task</div>
   <hr style="margin: 5px 0; border-top: 1px solid #ECF0F1;">
   <div style="color:#555555;">▲ Dangling Node</div>
   <div style="color:#555555;">⬢ High Risk Merge</div>
   <div style="color:#555555;">■ Logic Gap</div>
   </div>
   """
   with open(output_file, 'r', encoding='utf-8') as f:
       html = f.read().replace('<body>', f'<body>{legend}')
   with open(output_file, 'w', encoding='utf-8') as f:
       f.write(html)
   return output_file


# --- 6. PROBABILISTIC CORE ---
def days_to_date(start_date, days):
   return start_date + timedelta(days=int(round(days)))


def apply_seasonality(task_id, start_dt, modifiers):
   if not modifiers: return 1.0
   for mod in modifiers:
       if "task_ids" in mod and task_id not in mod["task_ids"]: continue
       mstart = date(start_dt.year, mod["window"]["start"][0], mod["window"]["start"][1])
       mend = date(start_dt.year, mod["window"]["end"][0], mod["window"]["end"][1])
       if mend >= mstart: in_window = (mstart <= start_dt <= mend)
       else: in_window = (start_dt >= mstart or start_dt <= mend)
       if in_window: return float(mod.get("multiplier", 1.0))
   return 1.0


def sample_lognormal_from_z(mu, sigma, z):
   return float(np.exp(mu + sigma * z))


def triangular_ppf(u, a, c, b):
   a, c, b = float(a), float(c), float(b)
   if not (a <= c <= b): c = min(max(c, a), b)
   Fc = (c - a) / (b - a) if b > a else 0.5
   if u < Fc: return a + math.sqrt(max(0.0, u) * (b - a) * (c - a))
   else: return b - math.sqrt(max(0.0, (1 - u)) * (b - a) * (b - c))


def pert_alpha_beta(a, m, b, lam=4.0):
   a, m, b = float(a), float(m), float(b)
   if not (a <= m <= b): m = min(max(m, a), b)
   mean = (a + lam * m + b) / (lam + 2)
   v = ((b - a) ** 2) / ((lam + 2) ** 2 * (lam + 3))
   if v <= 0: return 2.0, 2.0
   mu01 = (mean - a) / (b - a + 1e-12)
   t = mu01 * (1 - mu01) / (v / ((b - a) ** 2) + 1e-12) - 1
   alpha = max(mu01 * t, 1e-3)
   beta = max((1 - mu01) * t, 1e-3)
   return alpha, beta


def pert_ppf(u, a, m, b, lam=4.0):
   alpha, beta = pert_alpha_beta(a, m, b, lam)
   if SCIPY_AVAILABLE: return a + (b - a) * beta_dist.ppf(u, alpha, beta)
   else: return a + (b - a) * np.random.beta(alpha, beta)


def cholesky_from_corr(corr):
   A = np.array(corr, dtype=float)
   return np.linalg.cholesky(A + 1e-12 * np.eye(A.shape[0]))


def gaussian_copula_draw(L, rng, n):
   z = rng.standard_normal(size=n)
   cz = L @ z
   if SCIPY_AVAILABLE: u = norm.cdf(cz)
   else: u = 0.5 * (1.0 + (2.0 / math.sqrt(math.pi)) * np.vectorize(math.erf)(cz / math.sqrt(2)))
   return cz, np.clip(u, 1e-9, 1 - 1e-9)


def correlated_monte_carlo_schedule(
   G, schedule, iterations=1000, corr=None, dist_cfg=None, start_date=date(2026, 1, 1),
   seasonal=None, use_super_nodes=True, rng=None, return_task_samples=False
):
   rng = rng or np.random.default_rng()
   G_work = add_super_source_sink(G) if use_super_nodes else G.copy()
   tasks = [n for n in G_work.nodes() if n not in ("SUPER_START", "SUPER_FINISH")]
   n = len(tasks)
   if corr is None or np.array(corr).shape != (n, n): corr = np.eye(n)
   L = cholesky_from_corr(corr)
   idx = {t: i for i, t in enumerate(tasks)}
   base = {t["id"]: float(t.get("duration", 0)) for t in schedule}
   dist_cfg = dist_cfg or {}
   results = []
   critical_counts = {t: 0 for t in tasks}
   task_samples = {t: [] for t in tasks} if return_task_samples else None


   for _ in range(iterations):
       z, u = gaussian_copula_draw(L, rng, n)
       G_sim = G_work.copy()
       for node in tasks:
           cfg = dist_cfg.get(node, None)
           if cfg is None:
               b0 = base.get(node, float(G_sim.nodes[node]["weight"]))
               a, m, b = 0.8 * b0, b0, 1.5 * b0
               dur = triangular_ppf(float(u[idx[node]]), a, m, b)
           else:
               dist = cfg.get("dist", "triangular").lower()
               if dist == "lognormal":
                   dur = sample_lognormal_from_z(float(cfg["mu"]), float(cfg["sigma"]), z[idx[node]])
               elif dist == "pert":
                   dur = pert_ppf(float(u[idx[node]]), float(cfg["a"]), float(cfg["m"]), float(cfg["b"]), float(cfg.get("lam", 4.0)))
               elif dist == "triangular":
                   dur = triangular_ppf(float(u[idx[node]]), float(cfg["a"]), float(cfg["m"]), float(cfg["b"]))
               else:
                   b0 = base.get(node, float(G_sim.nodes[node]["weight"]))
                   dur = triangular_ppf(float(u[idx[node]]), 0.8 * b0, b0, 1.5 * b0)
           G_sim.nodes[node]["weight"] = max(0.0, float(dur))
           if return_task_samples: task_samples[node].append(float(dur))


       cpm = run_cpm(G_sim)
       if seasonal:
           for node in tasks:
               es = cpm["ES"].get(node, 0.0)
               G_sim.nodes[node]["weight"] *= float(apply_seasonality(node, days_to_date(start_date, es), seasonal))
           cpm = run_cpm(G_sim)


       results.append(float(cpm["ProjectDuration"]))
       for n2, f in cpm["Float"].items():
           if n2 in critical_counts and abs(f) <= 1e-6:
               critical_counts[n2] += 1


   crit_index = {n: critical_counts[n] / iterations for n in tasks}
   if return_task_samples: return results, crit_index, task_samples
   return results, crit_index


# --- 7. OTHER ANALYTICS ---
def shock_propagation(G, node_id, delta=1.0, baseline_deadline=None):
   base = run_cpm_with_deadline(G, baseline_deadline) if baseline_deadline is not None else run_cpm(G)
   base_float = base.get("Float", {})
   G2 = G.copy()
   if node_id in G2.nodes():
       G2.nodes[node_id]["weight"] += float(delta)
   new = run_cpm_with_deadline(G2, baseline_deadline) if baseline_deadline is not None else run_cpm(G2)
   erosion = {n: base_float.get(n, 0.0) - new["Float"].get(n, 0.0) for n in G.nodes()}
   return {
       "BaselineDuration": float(base.get("ProjectDuration", 0.0)),
       "NewDuration": float(new.get("ProjectDuration", 0.0)),
       "FloatErosion": erosion
   }


def task_finish_correlations(G, schedule, iterations=2000, start_date=date(2026, 1, 1), use_super_nodes=True):
   results, _, task_samples = correlated_monte_carlo_schedule(
       G, schedule, iterations=iterations, start_date=start_date, use_super_nodes=use_super_nodes, return_task_samples=True
   )
   y = np.array(results, dtype=float)
   out = {}
   for task, xs in task_samples.items():
       x = np.array(xs, dtype=float)
       if x.size > 1 and np.std(x) > 1e-9 and np.std(y) > 1e-9:
           out[task] = float(np.corrcoef(x, y)[0, 1])
       else:
           out[task] = 0.0
   return dict(sorted(out.items(), key=lambda kv: abs(kv[1]), reverse=True))


def quantile_graph(G, schedule, percentile=50, iterations=1500, start_date=date(2026, 1, 1), use_super_nodes=True):
   results, _, task_samples = correlated_monte_carlo_schedule(
       G, schedule, iterations=iterations, start_date=start_date, use_super_nodes=use_super_nodes, return_task_samples=True
   )
   qp = {t: float(np.percentile(np.array(xs, dtype=float), percentile)) if xs else float(G.nodes[t]["weight"]) for t, xs in task_samples.items()}
   Gq = G.copy()
   for n in Gq.nodes():
       if n in qp: Gq.nodes[n]["weight"] = qp[n]
   return Gq


def compute_crash_plan(G, target_duration, crash_bounds, crash_costs):
   try: from ortools.linear_solver import pywraplp
   except Exception: return "ORTOOLS_NOT_AVAILABLE", {}, None
   solver = pywraplp.Solver.CreateSolver('GLOP')
   if not solver: return "SOLVER_ERROR", {}, None
   nodes = list(G.nodes())
   S = {n: solver.NumVar(0.0, solver.infinity(), f"S_{n}") for n in nodes}
   X = {n: solver.NumVar(0.0, float(crash_bounds.get(n, 0.0)), f"X_{n}") for n in nodes}
   objective = solver.Objective()
   for n in nodes: objective.SetCoefficient(X[n], float(crash_costs.get(n, 0.0)))
   objective.SetMinimization()
   for u, v in G.edges():
       ct = solver.Constraint(float(G.nodes[u]["weight"]), solver.infinity(), f"prec_{u}_{v}")
       ct.SetCoefficient(S[v], 1.0); ct.SetCoefficient(S[u], -1.0); ct.SetCoefficient(X[u], 1.0)
   finish_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
   F = solver.NumVar(0.0, solver.infinity(), "F")
   for f in finish_nodes:
       ct = solver.Constraint(float(G.nodes[f]["weight"]), solver.infinity(), f"finish_{f}")
       ct.SetCoefficient(F, 1.0); ct.SetCoefficient(S[f], -1.0); ct.SetCoefficient(X[f], 1.0)
   solver.Add(F <= float(target_duration))
   status = solver.Solve()
   if status != pywraplp.Solver.OPTIMAL: return "INFEASIBLE", {}, None
   plan = {n: X[n].solution_value() for n in nodes if X[n].ub() > 0 and X[n].solution_value() > 1e-6}
   return "OPTIMAL", plan, F.solution_value()

