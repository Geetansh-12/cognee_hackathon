import requests
import json
import time

def prepare():
    # Reset the DB
    print("Resetting DB...")
    requests.post("http://localhost:8000/api/reset")
    time.sleep(1)
    
    # Load user_location.json
    with open("backend/scenarios/user_location.json", "r") as f:
        scenario = json.load(f)
        
    print("Ingesting facts for the demo...")
    resp = requests.post("http://localhost:8000/api/ingest", json={"facts": scenario["facts"]})
    print(resp.json())
    print("Database is primed! Ready for live demo.")

if __name__ == "__main__":
    prepare()
