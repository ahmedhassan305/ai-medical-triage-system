#!/usr/bin/env python3
"""Test the triage API endpoint"""
import json
import urllib.request
import sys

def test_triage(query):
    """Test the triage endpoint"""
    url = "http://localhost:19001/api/v1/triage"
    data = json.dumps({"query": query}).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    query = "stomach severe pain in lower abdomen"
    print(f"Testing query: {query}\n")
    
    result = test_triage(query)
    
    if result:
        print("="*80)
        print("TRIAGE RESPONSE:")
        print("="*80)
        print(json.dumps(result, indent=2))
        
        # Check for new fields
        print("\n" + "="*80)
        print("NEW FIELDS CHECK:")
        print("="*80)
        
        new_fields = [
            "simple_reasoning",
            "plain_language_explanation", 
            "recommended_specialty",
            "suggested_doctors"
        ]
        
        for field in new_fields:
            if field in result:
                print(f"✓ {field}: YES")
            else:
                print(f"✗ {field}: MISSING")
    else:
        print("Failed to get response from API")
        sys.exit(1)
