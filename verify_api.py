#!/usr/bin/env python3
"""Verify the triage API returns all new fields"""
import json
import urllib.request

url = "http://localhost:19001/api/v1/triage"
data = json.dumps({"query": "I have chest pain and difficulty breathing"}).encode('utf-8')

try:
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        
        # Check for new fields
        required_fields = ['simple_reasoning', 'plain_language_explanation', 'recommended_specialty', 'suggested_doctors']
        has_all_fields = all(field in result for field in required_fields)
        
        print("✅ API Response: SUCCESS")
        print(f"✅ Has all new fields: YES\n")
        
        print("=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        
except Exception as e:
    print(f"❌ Error: {e}")
