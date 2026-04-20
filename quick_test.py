#!/usr/bin/env python3
"""Quick test of the triage API"""
import json
import sys
import urllib.request

url = "http://localhost:19001/api/v1/triage"
data = json.dumps({"query": "I have chest pain"}).encode('utf-8')

try:
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=5) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("✅ SUCCESS!")
        print(json.dumps(result, indent=2)[:500])
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
