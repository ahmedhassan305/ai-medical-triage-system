"""Verify symptom-to-disease mapping logic without needing Ollama."""

# Define the disease keyword mappings (from triage_service.py)
disease_keywords = [
    # CARDIAC CONDITIONS (high priority for chest pain cases)
    ("chest pain", "Myocardial infarction/Coronary artery disease"),
    ("heart attack", "Myocardial infarction"),
    ("acute coronary", "Acute coronary syndrome"),
    ("arrhythmia", "Cardiac arrhythmia"),
    ("palpitations", "Cardiac palpitations/Arrhythmia"),
    ("heart failure", "Heart failure"),
    ("hypertension", "Hypertension"),
    ("high blood pressure", "Hypertension"),
    
    # RESPIRATORY CONDITIONS
    ("blood in sputum", "Tuberculosis/Pneumonia/Lung cancer"),
    ("persistent cough", "Pneumonia/Bronchitis/Tuberculosis"),
    ("fever and cough", "Pneumonia/Bronchitis"),
    ("wheezing", "Asthma/COPD"),
    ("pneumonia", "Pneumonia"),
    ("bronchitis", "Bronchitis"),
    ("tuberculosis", "Tuberculosis"),
    ("difficulty breathing", "Dyspnea/Asthma"),
    ("shortness of breath", "Dyspnea/Asthma/COPD"),
    ("cough", "Common cold/Bronchitis"),
    
    # NEUROLOGICAL CONDITIONS
    ("severe headache", "Migraine/Tension headache"),
    ("high fever headache", "Meningitis"),
    ("neck stiffness", "Meningitis/Cervical strain"),
    ("sensitivity to light", "Migraine/Photophobia"),
    ("seizure", "Epilepsy/Seizure disorder"),
    ("stroke", "Acute ischemic stroke"),
    ("numbness tingling", "Neuropathy/Neurological disorder"),
    ("migraine", "Migraine headache"),
    
    # GASTROINTESTINAL CONDITIONS
    ("severe abdominal pain", "Appendicitis/Peritonitis/Bowel obstruction"),
    ("severe vomiting", "Gastroenteritis/Appendicitis"),
    ("abdominal pain", "Gastritis/GERD/IBS"),
    ("vomiting", "Gastroenteritis/GERD"),
    ("diarrhea", "Gastroenteritis/IBS"),
    ("appendicitis", "Appendicitis"),
    ("peritonitis", "Peritonitis"),
    ("bloating", "Irritable bowel syndrome/Gastritis"),
    ("constipation", "Constipation/IBS"),
    
    # DERMATOLOGICAL CONDITIONS
    ("severe rash", "Allergic reaction/Eczema/Contact dermatitis"),
    ("blistering", "Herpes zoster/Chickenpox/Eczema"),
    ("red rash", "Eczema/Dermatitis/Rosacea"),
    ("itching rash", "Eczema/Allergic reaction/Scabies"),
    ("skin rash", "Dermatitis/Eczema/Allergic reaction"),
    ("eczema", "Eczema"),
    ("psoriasis", "Psoriasis"),
    
    # MUSCULOSKELETAL CONDITIONS
    ("severe knee swelling", "ACL tear/Meniscus tear/Knee injury"),
    ("severe back pain", "Herniated disc/Sciatica"),
    ("back pain", "Back strain/Sciatica/Herniated disc"),
    ("severe knee pain", "Knee injury/Osteoarthritis"),
    ("knee pain", "Knee injury/Osteoarthritis"),
    ("neck pain", "Cervical strain/Whiplash"),
    ("broke", "Fracture"),
    ("break", "Fracture"),
    ("fracture", "Fracture"),
    ("sprain", "Ligament sprain"),
    ("strain", "Muscle strain"),
    ("dislocation", "Joint dislocation"),
    ("arthritis", "Osteoarthritis/Rheumatoid arthritis"),
    ("joint pain", "Arthritis/Joint inflammation"),
    
    # PSYCHIATRIC CONDITIONS (specific diagnosis keywords)
    ("panic attack", "Panic disorder"),
    ("severe panic", "Panic disorder"),
    ("panic", "Panic disorder"),
    ("severe anxiety", "Anxiety disorder"),
    ("anxiety", "Anxiety disorder"),
    ("depression", "Major depressive disorder"),
    ("suicidal", "Suicidal ideation/Depression"),
    
    # INFECTIOUS DISEASES
    ("high fever", "Serious infection/Meningitis"),
    ("infection", "Bacterial/Viral infection"),
    ("flu", "Influenza"),
    ("fever", "Infection/Flu/Common cold"),
    ("cold", "Common cold"),
    ("sick", "Viral infection"),
    
    # ENDOCRINE CONDITIONS
    ("diabetes", "Diabetes mellitus"),
    ("high blood sugar", "Diabetes/Hyperglycemia"),
    ("thyroid", "Thyroid disorder"),
    
    # ALLERGIC CONDITIONS
    ("anaphylaxis", "Anaphylactic shock"),
    ("allergic", "Allergic reaction"),
    ("allergy", "Allergic reaction"),
    
    # OTHER
    ("kidney", "Kidney disease/Nephrolithiasis"),
    ("liver", "Liver disease"),
    ("poison", "Poisoning/Toxin exposure"),
    ("overdose", "Drug overdose"),
    ("severe bleeding", "Hemorrhagic shock"),
    ("bleeding", "Hemorrhage/Bleeding disorder"),
]

def get_suspected_condition(query: str) -> tuple[str, str]:
    """Detect the underlying medical condition from query."""
    combined_text = query.lower()
    
    # Priority 1: High-priority symptom combinations (most specific patterns)
    priority_combinations = [
        # Cardiac with multiple symptoms
        (["chest pain", "left arm"], "Myocardial infarction/Coronary artery disease"),
        (["chest pain", "jaw pain"], "Myocardial infarction/Coronary artery disease"),
        (["chest pain", "radiates"], "Myocardial infarction/Coronary artery disease"),
        
        # Meningitis combination
        (["severe headache", "stiff neck"], "Meningitis"),
        (["high fever", "stiff neck"], "Meningitis"),
        (["stiff neck", "fever"], "Meningitis"),
        
        # Panic disorder indicators
        (["panic", "anxiety"], "Panic disorder"),
        (["panic attack"], "Panic disorder"),
        (["severe panic"], "Panic disorder"),
    ]
    
    # Check priority combinations first
    for symptoms, condition in priority_combinations:
        if all(symptom in combined_text for symptom in symptoms):
            return f"combination: {symptoms}", condition
    
    # Priority 2: Single keywords
    sorted_keywords = sorted(disease_keywords, key=lambda x: len(x[0]), reverse=True)
    
    for keyword, condition in sorted_keywords:
        if keyword in combined_text:
            return keyword, condition
    
    return "No match", "Unknown condition"

# Test cases
test_cases = [
    {
        "query": "I have chest pain that radiates to my left arm and jaw, shortness of breath, and nausea",
        "name": "CARDIAC: Chest Pain/MI",
        "expected_keywords": ["chest pain", "shortness of breath"],
        "expected_condition": "Myocardial infarction/Coronary artery disease"
    },
    {
        "query": "I have severe headache, stiff neck, high fever 104F, and sensitivity to light",
        "name": "NEURO: Meningitis",
        "expected_keywords": ["severe headache", "high fever", "neck stiffness", "sensitivity to light"],
        "expected_condition": "Meningitis"
    },
    {
        "query": "I have persistent dry cough for 3 weeks, blood in sputum, and weight loss",
        "name": "RESPIRATORY: TB/Pneumonia",
        "expected_keywords": ["blood in sputum", "persistent cough"],
        "expected_condition": "Tuberculosis/Pneumonia/Lung cancer"
    },
    {
        "query": "I broke my leg and cannot bear weight on it",
        "name": "ORTHO: Fracture",
        "expected_keywords": ["broke"],
        "expected_condition": "Fracture"
    },
    {
        "query": "I have severe panic attacks and intense anxiety with shortness of breath",
        "name": "PSYCH: Panic Disorder",
        "expected_keywords": ["panic", "anxiety", "shortness of breath"],
        "expected_condition": "Panic disorder"
    },
    {
        "query": "I have severe abdominal pain, vomiting, and fever for 2 days",
        "name": "GI: Appendicitis",
        "expected_keywords": ["severe abdominal pain"],
        "expected_condition": "Appendicitis/Peritonitis/Bowel obstruction"
    }
]

print("=" * 80)
print("SYMPTOM-TO-DISEASE MAPPING VERIFICATION")
print("=" * 80)

results = []
for test in test_cases:
    matched_keyword, predicted_condition = get_suspected_condition(test["query"])
    
    status = "✓" if predicted_condition != "Unknown condition" else "✗"
    expected = test["expected_condition"]
    match = "✓ MATCH" if predicted_condition == expected else "✗ MISMATCH"
    
    result = {
        "test": test["name"],
        "query": test["query"][:60] + "...",
        "matched_keyword": matched_keyword,
        "predicted_condition": predicted_condition,
        "expected_condition": expected,
        "status": match
    }
    results.append(result)
    
    print(f"\n{status} {test['name']}")
    print(f"   Query: {test['query'][:70]}...")
    print(f"   Matched keyword: '{matched_keyword}'")
    print(f"   Predicted: {predicted_condition}")
    print(f"   Expected:  {expected}")
    print(f"   {match}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY:")
matches = sum(1 for r in results if r["status"] == "✓ MATCH")
total = len(results)
print(f"Symptom matching: {matches}/{total} correct ({100*matches//total}%)")
print("=" * 80)

# Print detailed results
print("\nDETAILED RESULTS:")
import json
print(json.dumps(results, indent=2))
