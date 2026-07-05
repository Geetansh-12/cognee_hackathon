import requests

def test_queries():
    q1 = "Where does Alice currently live?"
    q2 = "Where did Alice move to in 2025?"
    
    for q in [q1, q2]:
        print(f"\n--- Question: {q} ---")
        try:
            r1 = requests.post("http://localhost:8000/api/query/naive", json={"question": q}).json()
            print("Naive:", r1.get("answer"))
        except Exception as e:
            print("Naive Error:", e)
            
        try:
            r2 = requests.post("http://localhost:8000/api/query/cognee", json={"question": q}).json()
            print("Cognee:", r2.get("answer"))
        except Exception as e:
            print("Cognee Error:", e)

if __name__ == "__main__":
    test_queries()
