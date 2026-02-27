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

# ... add your other schedules (broken, complex) here ...

schedulesdb = {
    "schedulehealthy": schedule_healthy,
    "scheduletoxic": schedule_toxic,
}
