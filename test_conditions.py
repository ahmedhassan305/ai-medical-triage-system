import requests
import json
import time

BASE_URL = "http://localhost:19001"

# First register and login
email = f"test_cond_{int(time.time())}@example.com"
password = "TestPassword123"

# Register
register_resp = requests.post(
    f"{BASE_URL}/api/v1/auth/register",
    json={
        "email": email,
        "password": password,
        "role": "patient"
    }
)
print(f"Register: {register_resp.status_code}")

# Login
login_resp = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={
        "email": email,
        "password": password
    }
)
print(f"Login: {login_resp.status_code}")
token = login_resp.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Test cases for condition detection
test_cases = [
    {
        "query": "I have chest pain that radiates to my left arm and jaw, shortness of breath, and nausea",
        "name": "CARDIAC: Chest Pain/MI"
    },
    {
        "query": "I have severe headache, stiff neck, high fever 104F, and sensitivity to light",
        "name": "NEURO: Meningitis"
    },
    {
        "query": "I have persistent dry cough for 3 weeks, blood in sputum, and weight loss",
        "name": "RESPIRATORY: TB/Pneumonia"
    },
    {
        "query": "I broke my leg and cannot bear weight on it",
        "name": "ORTHO: Fracture"
    },
    {
        "query": "I have severe panic attacks and intense anxiety with shortness of breath",
        "name": "PSYCH: Panic Disorder"
    },
    {
        "query": "I have severe abdominal pain, vomiting, and fever for 2 days",
        "name": "GI: Appendicitis"
    }
]

results = []

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"Testing: {test['name']}")
    print(f"Query: {test['query'][:80]}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/triage",
            headers=headers,
            json={"query": test["query"]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            result_entry = {
                "test": test['name'],
                "query": test['query'][:60],
                "suspected_condition": data.get('suspected_condition', 'NOT FOUND'),
                "specialty": data.get('recommended_specialty', 'NOT FOUND'),
                "urgency": data.get('triage_level', 'NOT FOUND'),
                "status": "✓ SUCCESS"
            }
            
            results.append(result_entry)
            
            print(f"Suspected Condition: {data.get('suspected_condition', 'NOT DETECTED')}")
            print(f"Recommended Specialty: {data.get('recommended_specialty', 'NOT FOUND')}")
            print(f"Triage Level: {data.get('triage_level', 'NOT FOUND')}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            results.append({
                "test": test['name'],
                "status": f"ERROR {response.status_code}",
                "error": response.text[:200]
            })
    except Exception as e:
        print(f"Exception: {str(e)}")
        results.append({
            "test": test['name'],
            "status": f"EXCEPTION",
            "error": str(e)
        })
    
    time.sleep(1)

print(f"\n{'='*60}")
print("SUMMARY RESULTS:")
print(json.dumps(results, indent=2))
