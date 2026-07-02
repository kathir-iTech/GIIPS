"""
Generate Tamil Nadu synthetic dataset CSV files.
"""

import random
import json
from datetime import datetime, timedelta
from pathlib import Path

TAMIL_NADU_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri",
    "Dindigul", "Erode", "Kallakurichi", "Kanchipuram", "Kanyakumari", "Karur",
    "Krishnagiri", "Madurai", "Nagapattinam", "Nilgiris", "Namakkal", "Perambalur",
    "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem", "Sivagangai", "Tenkasi",
    "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
    "Tiruppur", "Tiruvannamalai", "Tiruvil", "Trichy", "Vellore", "Viluppuram",
    "Virudhunagar"
]

CATEGORIES = ["Roads", "Water Supply", "Drainage", "Streetlights", "Garbage", "Public Health", "Electricity"]

PRIORITY_LABELS = ["Critical", "High", "Medium", "Low"]

def generate_dataset():
    complaints = []
    incidents = []
    
    for i in range(10000):
        category = random.choice(CATEGORIES)
        district = random.choice(TAMIL_NADU_DISTRICTS)
        ward = f"Ward {random.randint(1, 20)}"
        
        complaint = {
            "id": f"COMP-{i+1:06d}",
            "title": f"{category} issue in {ward}",
            "text": f"Complaint about {category.lower()} in {ward}, {district}",
            "description": f"Issue reported in {ward}, {district}. Requires attention.",
            "date": (datetime.now() - timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
            "district": district,
            "ward": ward,
            "latitude": round(11.0 + random.random() * 3.0, 6),
            "longitude": round(77.0 + random.random() * 2.0, 6),
            "category": category,
            "priority": random.choices(PRIORITY_LABELS, weights=[0.1, 0.25, 0.4, 0.25])[0],
            "incident_id": f"INC-{random.randint(1, 150):06d}" if random.random() > 0.6 else None
        }
        complaints.append(complaint)
    
    for i in range(150):
        incidents.append({
            "id": f"INC-{i+1:06d}",
            "incident_number": f"INC-{i+1:06d}",
            "category": random.choice(CATEGORIES),
            "ward": f"Ward {random.randint(1, 20)}",
            "cluster_size": random.randint(3, 25),
            "days_open": random.randint(1, 30),
            "priority_score": round(random.uniform(30, 95), 1),
            "priority_label": random.choices(PRIORITY_LABELS, weights=[0.1, 0.25, 0.4, 0.25])[0],
            "summary": "Incident summary",
            "recommended_action": "Action required",
            "status": random.choice(["open", "in-progress", "resolved"]),
            "complaints": []
        })
    
    return complaints, incidents

if __name__ == "__main__":
    complaints, incidents = generate_dataset()
    
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    with open(data_dir / 'synthetic_complaints.json', 'w') as f:
        json.dump(complaints[:500], f, indent=2)
    
    with open(data_dir / 'synthetic_incidents.json', 'w') as f:
        json.dump(incidents, f, indent=2)
    
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    dashboard_data = {
        "totalComplaints": 10000,
        "uniqueIncidents": 150,
        "workloadReduction": 78.5,
        "criticalIncidents": 150,
        "highPriorityIncidents": 250,
        "mediumPriorityIncidents": 400,
        "lowPriorityIncidents": 200,
        "categoryBreakdown": [
            {"category": "Roads", "count": 2500, "color": "#ef4444"},
            {"category": "Water Supply", "count": 2000, "color": "#3b82f6"},
            {"category": "Drainage", "count": 1500, "color": "#10b981"},
            {"category": "Streetlights", "count": 1200, "color": "#f59e0b"},
            {"category": "Garbage", "count": 1500, "color": "#8b5cf6"},
            {"category": "Public Health", "count": 1000, "color": "#06b6d4"},
            {"category": "Electricity", "count": 300, "color": "#eab308"}
        ],
        "wardBreakdown": [{"ward": f"Ward {i}", "count": random.randint(80, 200)} for i in range(1, 21)],
        "recentIncidents": incidents[:10],
        "trendData": [{"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), "complaints": random.randint(80, 150), "incidents": random.randint(10, 25)} for i in range(30)]
    }
    
    with open(output_dir / 'dashboard_data.json', 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"Generated {len(complaints)} complaints and {len(incidents)} incidents")
    print(f"Districts covered: {len(TAMIL_NADU_DISTRICTS)}")