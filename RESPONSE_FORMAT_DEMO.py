z#!/usr/bin/env python3
"""
Demonstration of the new Triage API response format with:
- Simple language reasoning
- Doctor suggestions  
- Recommended specialty
"""

# EXAMPLE API RESPONSE with new fields:

example_response_stomach_pain = {
    "triage_level": "low",
    "summary": "Your symptoms suggest lower abdominal pain with possible appendicitis or ligament syndrome.",
    "simple_reasoning": "Your symptoms suggest lower abdominal pain with possible appendicitis or ligament syndrome.",
    "plain_language_explanation": "Based on your symptoms, you may have a gastroenterology-related condition. Your symptoms suggest lower abdominal pain with possible appendicitis or ligament syndrome.",
    "actions": [
        "Consider rest, hydration, and over-the-counter options if appropriate.",
        "Seek care if symptoms persist, worsen, or you are concerned."
    ],
    "recommended_specialty": "Gastroenterology",
    "suggested_doctors": [
        {
            "id": 5,
            "full_name": "Dr. Michael Chen",
            "specialty": "Gastroenterology",
            "clinic": "Digestive Health Institute"
        },
        {
            "id": 6,
            "full_name": "Dr. Lisa Anderson",
            "specialty": "Gastroenterology",
            "clinic": "Downtown Gastro Clinic"
        }
    ],
    "disclaimer": "This is not medical advice. If you think you may have a medical emergency, seek immediate care.",
    "history_used": True
}

example_response_chest_pain = {
    "triage_level": "high",
    "summary": "Your symptoms need urgent emergency care. Severe chest pain with difficulty breathing requires immediate medical attention.",
    "simple_reasoning": "Your symptoms need urgent emergency care. Severe chest pain with difficulty breathing requires immediate medical attention.",
    "plain_language_explanation": "Based on your symptoms, you may have a cardiology-related condition. Your symptoms need urgent emergency care. Severe chest pain with difficulty breathing requires immediate medical attention.",
    "actions": [
        "Seek emergency care now.",
        "Call local emergency services if symptoms are severe or worsening."
    ],
    "recommended_specialty": "Cardiology",
    "suggested_doctors": [
        {
            "id": 1,
            "full_name": "Dr. John Smith",
            "specialty": "Cardiology",
            "clinic": "Heart Care Center"
        },
        {
            "id": 2,
            "full_name": "Dr. Sarah Johnson",
            "specialty": "Cardiology",
            "clinic": "City Hospital Cardiology"
        }
    ],
    "disclaimer": "This is not medical advice. If you think you may have a medical emergency, seek immediate care.",
    "history_used": False
}

example_response_headache = {
    "triage_level": "low",
    "summary": "Your symptoms suggest a tension or migraine headache.",
    "simple_reasoning": "Your symptoms suggest a tension or migraine headache.",
    "plain_language_explanation": "Based on your symptoms, you may have a neurology-related condition. Your symptoms suggest a tension or migraine headache.",
    "actions": [
        "Consider rest, hydration, and over-the-counter options if appropriate.",
        "Seek care if symptoms persist, worsen, or you are concerned."
    ],
    "recommended_specialty": "Neurology",
    "suggested_doctors": [
        {
            "id": 7,
            "full_name": "Dr. James Wilson",
            "specialty": "Neurology",
            "clinic": "Brain & Nerve Center"
        },
        {
            "id": 8,
            "full_name": "Dr. Emma Thompson",
            "specialty": "Neurology",
            "clinic": "Neuroscience Institute"
        }
    ],
    "disclaimer": "This is not medical advice. If you think you may have a medical emergency, seek immediate care.",
    "history_used": False
}

if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("NEW TRIAGE API RESPONSE FORMAT")
    print("=" * 80)
    
    print("\n1. EXAMPLE: Stomach Pain (Low Urgency)")
    print("-" * 80)
    print(json.dumps(example_response_stomach_pain, indent=2))
    
    print("\n2. EXAMPLE: Chest Pain (HIGH URGENCY)")
    print("-" * 80)
    print(json.dumps(example_response_chest_pain, indent=2))
    
    print("\n3. EXAMPLE: Headache (Low Urgency)")
    print("-" * 80)
    print(json.dumps(example_response_headache, indent=2))
    
    print("\n" + "=" * 80)
    print("NEW FIELDS EXPLAINED:")
    print("=" * 80)
    print("""
✓ simple_reasoning: Medical explanation converted to simple language
  - Replaces medical jargon with everyday words
  - e.g., "cardiac" → "heart", "respiratory" → "breathing"

✓ plain_language_explanation: Patient-friendly summary combining specialty + reasoning
  - Starts with what type of doctor to see
  - Continues with simplified explanation

✓ recommended_specialty: The medical specialty that should handle this
  - Based on symptoms (Cardiology, Neurology, Gastroenterology, etc.)
  - Used to find doctors

✓ suggested_doctors: List of available doctors matching the specialty
  - Includes doctor name, specialty, and clinic
  - Limited to top 3 matches

✓ all_fields_in_response:
  - triage_level: Urgency level (high/medium/low)
  - summary: Original model output
  - simple_reasoning: Simplified summary
  - plain_language_explanation: Patient-friendly explanation
  - actions: Recommended next steps for patient
  - recommended_specialty: Type of doctor needed
  - suggested_doctors: List of available doctors
  - disclaimer: Legal disclaimer
  - history_used: Whether patient history was considered
    """)
