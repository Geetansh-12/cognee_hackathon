import json
import os

scenarios = [
    {
        "id": "job_search_google",
        "facts": [
            {"subject": "Google SWE Internship", "predicate": "status", "value": "Applied", "timestamp": "2026-05-01"},
            {"subject": "Google SWE Internship", "predicate": "status", "value": "OA invite received", "timestamp": "2026-05-05", "supersedes": "Applied"},
            {"subject": "Google SWE Internship", "predicate": "status", "value": "Interview completed", "timestamp": "2026-05-12", "supersedes": "OA invite received"},
            {"subject": "Google SWE Internship", "predicate": "status", "value": "Rejected", "timestamp": "2026-05-20", "supersedes": "Interview completed"}
        ],
        "eval_question": "What is the current status of the Google SWE Internship application?",
        "ground_truth_answer": "Rejected",
        "stale_values": ["Applied", "OA invite", "Interview completed"]
    },
    {
        "id": "user_location",
        "facts": [
            {"subject": "Alice", "predicate": "lives in", "value": "New York", "timestamp": "2023-01-01"},
            {"subject": "Alice", "predicate": "lives in", "value": "Chicago", "timestamp": "2024-06-15", "supersedes": "New York"},
            {"subject": "Alice", "predicate": "lives in", "value": "Seattle", "timestamp": "2025-09-20", "supersedes": "Chicago"}
        ],
        "eval_question": "Where does Alice currently live?",
        "ground_truth_answer": "Seattle",
        "stale_values": ["New York", "Chicago"]
    },
    {
        "id": "favorite_programming_language",
        "facts": [
            {"subject": "Bob", "predicate": "favorite programming language", "value": "Java", "timestamp": "2020-05-10"},
            {"subject": "Bob", "predicate": "favorite programming language", "value": "Python", "timestamp": "2022-11-22", "supersedes": "Java"},
            {"subject": "Bob", "predicate": "favorite programming language", "value": "Rust", "timestamp": "2026-02-14", "supersedes": "Python"}
        ],
        "eval_question": "What is Bob's current favorite programming language?",
        "ground_truth_answer": "Rust",
        "stale_values": ["Java", "Python"]
    },
    {
        "id": "project_deadline",
        "facts": [
            {"subject": "Project Apollo", "predicate": "deadline", "value": "Q3 2026", "timestamp": "2026-01-15"},
            {"subject": "Project Apollo", "predicate": "deadline", "value": "Q4 2026", "timestamp": "2026-04-10", "supersedes": "Q3 2026"},
            {"subject": "Project Apollo", "predicate": "deadline", "value": "Q1 2027", "timestamp": "2026-07-01", "supersedes": "Q4 2026"}
        ],
        "eval_question": "When is the deadline for Project Apollo?",
        "ground_truth_answer": "Q1 2027",
        "stale_values": ["Q3 2026", "Q4 2026"]
    },
    {
        "id": "ceo_of_company",
        "facts": [
            {"subject": "Acme Corp", "predicate": "CEO", "value": "John Doe", "timestamp": "2015-01-01"},
            {"subject": "Acme Corp", "predicate": "CEO", "value": "Jane Smith", "timestamp": "2020-05-10", "supersedes": "John Doe"},
            {"subject": "Acme Corp", "predicate": "CEO", "value": "Alan Turing", "timestamp": "2026-01-01", "supersedes": "Jane Smith"}
        ],
        "eval_question": "Who is the CEO of Acme Corp?",
        "ground_truth_answer": "Alan Turing",
        "stale_values": ["John Doe", "Jane Smith"]
    },
    {
        "id": "car_ownership",
        "facts": [
            {"subject": "Charlie", "predicate": "drives a", "value": "Honda Civic", "timestamp": "2018-06-01"},
            {"subject": "Charlie", "predicate": "drives a", "value": "Toyota Camry", "timestamp": "2021-08-15", "supersedes": "Honda Civic"},
            {"subject": "Charlie", "predicate": "drives a", "value": "Tesla Model 3", "timestamp": "2025-12-01", "supersedes": "Toyota Camry"}
        ],
        "eval_question": "What car does Charlie drive?",
        "ground_truth_answer": "Tesla Model 3",
        "stale_values": ["Honda Civic", "Toyota Camry"]
    },
    {
        "id": "relationship_status",
        "facts": [
            {"subject": "Diana", "predicate": "relationship status", "value": "Single", "timestamp": "2019-02-14"},
            {"subject": "Diana", "predicate": "relationship status", "value": "In a relationship", "timestamp": "2021-06-01", "supersedes": "Single"},
            {"subject": "Diana", "predicate": "relationship status", "value": "Engaged", "timestamp": "2024-12-25", "supersedes": "In a relationship"},
            {"subject": "Diana", "predicate": "relationship status", "value": "Married", "timestamp": "2026-05-10", "supersedes": "Engaged"}
        ],
        "eval_question": "What is Diana's relationship status?",
        "ground_truth_answer": "Married",
        "stale_values": ["Single", "In a relationship", "Engaged"]
    },
    {
        "id": "software_version",
        "facts": [
            {"subject": "My App", "predicate": "version", "value": "1.0.0", "timestamp": "2024-01-01"},
            {"subject": "My App", "predicate": "version", "value": "1.1.0", "timestamp": "2024-03-15", "supersedes": "1.0.0"},
            {"subject": "My App", "predicate": "version", "value": "2.0.0", "timestamp": "2025-01-10", "supersedes": "1.1.0"},
            {"subject": "My App", "predicate": "version", "value": "2.0.1", "timestamp": "2025-02-01", "supersedes": "2.0.0"}
        ],
        "eval_question": "What is the current version of My App?",
        "ground_truth_answer": "2.0.1",
        "stale_values": ["1.0.0", "1.1.0", "2.0.0"]
    },
    {
        "id": "capital_city",
        "facts": [
            {"subject": "Nation X", "predicate": "capital", "value": "Old City", "timestamp": "1900-01-01"},
            {"subject": "Nation X", "predicate": "capital", "value": "New City", "timestamp": "1950-01-01", "supersedes": "Old City"},
            {"subject": "Nation X", "predicate": "capital", "value": "Future City", "timestamp": "2050-01-01", "supersedes": "New City"}
        ],
        "eval_question": "What is the capital of Nation X?",
        "ground_truth_answer": "Future City",
        "stale_values": ["Old City", "New City"]
    },
    {
        "id": "medical_diagnosis",
        "facts": [
            {"subject": "Patient 404", "predicate": "diagnosis", "value": "Common Cold", "timestamp": "2026-01-01"},
            {"subject": "Patient 404", "predicate": "diagnosis", "value": "Flu", "timestamp": "2026-01-03", "supersedes": "Common Cold"},
            {"subject": "Patient 404", "predicate": "diagnosis", "value": "Pneumonia", "timestamp": "2026-01-10", "supersedes": "Flu"}
        ],
        "eval_question": "What is the diagnosis for Patient 404?",
        "ground_truth_answer": "Pneumonia",
        "stale_values": ["Common Cold", "Flu"]
    },
    {
        "id": "stock_price",
        "facts": [
            {"subject": "AAPL", "predicate": "stock price", "value": "$150", "timestamp": "2023-01-01"},
            {"subject": "AAPL", "predicate": "stock price", "value": "$170", "timestamp": "2023-06-01", "supersedes": "$150"},
            {"subject": "AAPL", "predicate": "stock price", "value": "$190", "timestamp": "2024-01-01", "supersedes": "$170"},
            {"subject": "AAPL", "predicate": "stock price", "value": "$185", "timestamp": "2024-03-01", "supersedes": "$190"}
        ],
        "eval_question": "What is the stock price of AAPL?",
        "ground_truth_answer": "$185",
        "stale_values": ["$150", "$170", "$190"]
    },
    {
        "id": "weather_forecast",
        "facts": [
            {"subject": "London", "predicate": "weather tomorrow", "value": "Sunny", "timestamp": "08:00"},
            {"subject": "London", "predicate": "weather tomorrow", "value": "Cloudy", "timestamp": "12:00", "supersedes": "Sunny"},
            {"subject": "London", "predicate": "weather tomorrow", "value": "Rainy", "timestamp": "18:00", "supersedes": "Cloudy"}
        ],
        "eval_question": "What is the weather forecast for London tomorrow?",
        "ground_truth_answer": "Rainy",
        "stale_values": ["Sunny", "Cloudy"]
    },
    {
        "id": "dietary_preference",
        "facts": [
            {"subject": "Eve", "predicate": "diet", "value": "Omnivore", "timestamp": "2010-01-01"},
            {"subject": "Eve", "predicate": "diet", "value": "Vegetarian", "timestamp": "2015-05-01", "supersedes": "Omnivore"},
            {"subject": "Eve", "predicate": "diet", "value": "Vegan", "timestamp": "2020-01-01", "supersedes": "Vegetarian"}
        ],
        "eval_question": "What is Eve's diet?",
        "ground_truth_answer": "Vegan",
        "stale_values": ["Omnivore", "Vegetarian"]
    },
    {
        "id": "subscription_plan",
        "facts": [
            {"subject": "User123", "predicate": "subscription plan", "value": "Free", "timestamp": "2026-01-01"},
            {"subject": "User123", "predicate": "subscription plan", "value": "Pro", "timestamp": "2026-02-01", "supersedes": "Free"},
            {"subject": "User123", "predicate": "subscription plan", "value": "Enterprise", "timestamp": "2026-03-01", "supersedes": "Pro"}
        ],
        "eval_question": "What subscription plan is User123 on?",
        "ground_truth_answer": "Enterprise",
        "stale_values": ["Free", "Pro"]
    },
    {
        "id": "flight_status",
        "facts": [
            {"subject": "Flight AA100", "predicate": "status", "value": "On Time", "timestamp": "09:00"},
            {"subject": "Flight AA100", "predicate": "status", "value": "Delayed 1h", "timestamp": "10:30", "supersedes": "On Time"},
            {"subject": "Flight AA100", "predicate": "status", "value": "Cancelled", "timestamp": "11:45", "supersedes": "Delayed 1h"}
        ],
        "eval_question": "What is the status of Flight AA100?",
        "ground_truth_answer": "Cancelled",
        "stale_values": ["On Time", "Delayed 1h"]
    }
]

def generate_scenarios():
    import os
    scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")
    os.makedirs(scenarios_dir, exist_ok=True)
    
    for s in scenarios:
        with open(os.path.join(scenarios_dir, f"{s['id']}.json"), "w") as f:
            json.dump(s, f, indent=4)
            
    print(f"Generated {len(scenarios)} scenarios.")

if __name__ == "__main__":
    generate_scenarios()
