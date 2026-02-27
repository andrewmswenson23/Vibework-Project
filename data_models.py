# data_models.py

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
    {"id": "Foundation_Pour", "duration": 10, "predecessors": ["Structural_Drafting", "Zoning_Review"]},
    {"id": "Superstructure", "duration": 25, "predecessors": ["Foundation_Pour"]},
    {"id": "Interior_Fitout", "duration": 20, "predecessors": ["Superstructure"]},
    {"id": "Final_Handover", "duration": 0, "predecessors": ["Interior_Fitout"]}
]

schedule_complex = [
    {"id": "Permitting", "duration": 30, "predecessors": []},
    {"id": "Site_Survey", "duration": 10, "predecessors": ["Permitting"]},
    {"id": "Steel_Procurement", "duration": 45, "predecessors": ["Permitting"]},
    {"id": "Excavation", "duration": 20, "predecessors": ["Site_Survey"]},
    {"id": "Concrete_Pour", "duration": 10, "predecessors": ["Excavation"]},
    {"id": "Steel_Erection", "duration": 25, "predecessors": ["Steel_Procurement", "Concrete_Pour"]},
    {"id": "Interior_Walls", "duration": 12, "predecessors": ["Steel_Erection"]},
    {"id": "Project_Closeout", "duration": 2, "predecessors": ["Interior_Walls"]}
]

schedulesdb = {
    "schedulehealthy": schedule_healthy,
    "scheduletoxic": schedule_toxic,
    "schedulebroken": schedule_broken,
    "schedulecomplex": schedule_complex
}
