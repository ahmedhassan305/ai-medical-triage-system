#!/usr/bin/env python3
import json
import urllib.request
import sys

print("Testing Triage API...")
sys.stdout.flush()

url = "http://localhost:19001/api/v1/triage"
data = json.dumps({"query": "I have chest pain"}).encode('utf-8')

try:
    print(f"POSTing to {url}...")
    sys.stdout.flush()
    
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    print("Waiting for response...")
    sys.stdout.flush()
    
    with urllib.request.urlopen(req, timeout=30) as response:
        print(f"Got response code: {response.status}")
        sys.stdout.flush()
        
        content = response.read().decode('utf-8')
        print(f"Response length: {len(content)} bytes")
        sys.stdout.flush()
        
        result = json.loads(content)
        print(f"✅ Success! Response has {len(result)} fields")
        print(json.dumps(result, indent=2)[:1000])
        
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error {e.code}: {e.reason}")
    print(f"Response: {e.read().decode()}")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
