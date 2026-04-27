# Triage Evaluation Dataset - Quick Reference

## Dataset Overview
- **File Location:** `backend/app/rag/eval/triage_test_cases.json`
- **Total Cases:** 70
- **Format:** JSON array with structured test case objects

## Test Case Structure

```json
{
  "id": 1,
  "name": "Acute MI - Professional",
  "query": "acute myocardial infarction with chest pain radiating to left arm",
  "age": 55,
  "expected_urgency": "HIGH",
  "expected_specialty": "Cardiology",
  "expected_condition": "Myocardial infarction/Coronary artery disease",
  "language_type": "professional",
  "category": "chest_disease"
}
```

### Field Descriptions

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `id` | Integer | 1-70 | Unique test case identifier |
| `name` | String | Descriptive name | Human-readable test case name |
| `query` | String | Patient symptom description | The input to the triage system |
| `age` | Integer | 0.5-82 | Patient age in years (allows decimals for infants) |
| `expected_urgency` | String | HIGH / MEDIUM / LOW | Ground truth urgency classification |
| `expected_specialty` | String | Medical specialty name | Ground truth specialty recommendation |
| `expected_condition` | String | Condition name(s) | Ground truth suspected condition(s) |
| `language_type` | String | professional / colloquial | Query language complexity |
| `category` | String | 4 categories (see below) | Test case category |

## Categories

### 1. Chest Disease (8 cases)
High-risk cardiopulmonary conditions requiring urgent evaluation
- Acute MI (professional + colloquial)
- Pneumonia (professional + colloquial)
- Asthma Attack (professional + colloquial)
- Tuberculosis (professional + colloquial)

**Sample Cases:**
- Case 1: "acute myocardial infarction with chest pain radiating to left arm" (Professional, Age 55)
- Case 2: "my chest is killing me and my left arm hurts really bad" (Colloquial, Age 58)
- Case 3: "pneumonia with fever and productive cough" (Professional, Age 72)
- Case 4: "i cant stop coughing and i'm coughing up blood" (Colloquial, Age 45)

### 2. Emergency Red Flags (14 cases)
Life-threatening conditions that must be detected as HIGH urgency
- Meningitis (professional + colloquial)
- Stroke (professional + colloquial)
- Appendicitis (professional + colloquial)
- Sepsis, Hypertensive Crisis, DKA, Cholecystitis, Severe Burns, Drug Overdose

**Sample Cases:**
- Case 5: "severe headache with stiff neck and high fever" (Professional, Age 28)
- Case 6: "worst headache of my life and my neck is super stiff" (Colloquial, Age 31)
- Case 7: "sudden facial droop with slurred speech and arm weakness" (Professional, Age 67)
- Case 8: "my face is drooping and i cant talk right and my arm is weak" (Colloquial, Age 69)

### 3. Pediatrics (10 cases)
Age-specific conditions for children (typically under 13)
- Croup (professional + colloquial)
- Epiglottitis
- Fever in infant
- Asthma in children
- Pneumonia in children
- Dehydration
- Otitis Media (professional + colloquial)

**Sample Cases:**
- Case 21: "croup in 3-year-old with barky cough and stridor" (Professional, Age 3)
- Case 22: "my toddler has a barky cough and sounds like a seal" (Colloquial, Age 2)
- Case 24: "my 6 month old has a fever and im really worried" (Colloquial, Age 0.5)
- Case 25: "acute asthma exacerbation in 8-year-old with wheezing" (Professional, Age 8)

### 4. Routine Low-Risk (38 cases)
Common, self-limited conditions not requiring emergency care
- GERD, Cold, Influenza, Migraine
- Anxiety, Depression, Panic Attacks
- UTI, Kidney Stones
- Bronchitis, Sinusitis, Pharyngitis
- Dermatitis, Fractures, Sprains
- COVID-19, Dengue, Malaria

**Sample Cases:**
- Case 10: "bad stomach pain and i'm throwing up everything" (Colloquial, Age 42)
- Case 12: "i got heartburn and my throat is burning" (Colloquial, Age 55)
- Case 26: "i got a runny nose and a sore throat" (Colloquial, Age 28)
- Case 31: "benign paroxysmal positional vertigo with dizziness" (Professional, Age 68)

## Language Types

### Professional (38 cases)
Medical terminology as used by healthcare professionals
- Uses exact medical condition names
- Clear clinical presentation
- Standard medical vocabulary
- Examples:
  - "acute myocardial infarction with chest pain"
  - "pneumonia with fever and productive cough"
  - "acute appendicitis with right lower quadrant pain and fever"

### Colloquial (32 cases)
Everyday language as real patients speak when describing symptoms
- Colloquial terminology for symptoms
- Natural speech patterns
- Real-world patient language variations
- Examples:
  - "my chest is killing me and my left arm hurts really bad"
  - "i cant stop coughing and i'm coughing up blood"
  - "my belly hurts really bad on the right side and im running a fever"

**Important:** Colloquial cases test the system's ability to understand real patients, not medical professionals. This is critical for triage systems that serve the general public.

## Urgency Distribution

### HIGH (28 cases - 40%)
Life-threatening or immediately dangerous conditions
- All emergency red flag cases
- Acute cardiac events
- Severe respiratory distress
- Neurological emergencies
- Severe infections
- Target detection rate: 80%+ (safety-critical)

### MEDIUM (17 cases - 24%)
Conditions needing same-day or urgent care
- Moderate respiratory symptoms with fever
- Severe pain conditions
- Significant infections
- Conditions requiring specialist same-day evaluation
- Target detection rate: 70%+

### LOW (25 cases - 36%)
Chronic conditions or self-limited illnesses
- Common cold and flu
- GERD and heartburn
- Routine urinary issues
- Anxiety and depression (outpatient management)
- Target detection rate: 70%+ (minimize false alarms)

## Medical Specialties Covered (15+)

| Specialty | Cases | Examples |
|-----------|-------|----------|
| Cardiology | 4 | MI, hypertensive crisis, unstable angina |
| Pulmonology | 6 | Pneumonia, asthma, COPD, tuberculosis, bronchitis |
| Neurology | 6 | Stroke, meningitis, migraine, vertigo, neuropathy |
| Gastroenterology | 5 | GERD, gastritis, appendicitis, pancreatitis, cholecystitis |
| Psychiatry | 4 | Panic disorder, anxiety, depression |
| Pediatrics | 10 | Croup, epiglottitis, fever, pneumonia, dehydration |
| Orthopedics | 3 | Fractures, sprains |
| Surgery | 3 | Appendicitis, severe burns, cholecystitis |
| Urology | 3 | UTI, kidney stones |
| Otolaryngology | 4 | Sinusitis, pharyngitis, otitis media |
| Dermatology | 2 | Dermatitis, contact dermatitis |
| Internal Medicine | 4 | Influenza, COVID-19, dengue, malaria, DKA |
| General Practice | 2 | Common cold, routine follow-ups |
| Emergency Medicine | 1 | Drug overdose |

## Age Distribution

| Age Range | Count | Cases | Considerations |
|-----------|-------|-------|-----------------|
| Neonate (0-1) | 1 | Case 24: Infant fever | Fever is emergency in <3mo |
| Toddler (1-5) | 5 | Cases 21-22: Croup | Airway concerns critical |
| Child (5-13) | 4 | Cases 25, 63-64: Pediatric asthma, otitis | Different vital sign norms |
| Adolescent (13-18) | 2 | Case 16: Asthma (age 22 ~adult) | Psychosocial factors |
| Adult (18-65) | 48 | Most cases | Standard adult presentations |
| Geriatric (65+) | 10 | Cases 3, 5, 31, 45, etc. | Higher risk, atypical presentations |

## Condition Diversity (30+ Conditions)

### Cardiovascular
- Myocardial infarction / Coronary artery disease
- Hypertensive crisis

### Respiratory
- Pneumonia
- Asthma
- COPD
- Tuberculosis
- Croup
- Epiglottitis
- Acute bronchitis

### Neurological
- Stroke
- Meningitis
- Migraine
- Vertigo
- Neuropathy

### Gastrointestinal
- GERD / Gastritis
- Appendicitis
- Pancreatitis
- Cholecystitis

### Infectious
- COVID-19
- Influenza
- Dengue fever
- Malaria

### Psychiatric
- Panic disorder
- Anxiety disorder
- Major depressive disorder

### Urological
- Urinary tract infection
- Kidney stones

### Other
- Fever
- Dehydration
- Drug overdose
- Severe burns
- Fractures
- Sinusitis
- Pharyngitis
- Otitis media
- Dermatitis
- Diabetic ketoacidosis
- Sepsis

## Key Testing Scenarios

### Must Always Be HIGH Urgency (Safety-Critical)
1. Meningitis (cases 5-6)
2. Stroke (cases 7-8)
3. Acute MI (cases 1-2)
4. Epiglottitis in children (case 23)
5. Sepsis (case 9)
6. Appendicitis (cases 19-20)
7. Cholecystitis (cases 35-36)
8. Pancreatitis (case 56)
9. Severe burns (case 69)
10. Drug overdose (case 70)
11. DKA (case 29)
12. Hypertensive crisis (case 28)
13. Asthma/COPD exacerbation (cases 15-16, 25)
14. Infant fever (case 24)

### Colloquial Language Challenge Cases (Test Real Patient Understanding)
- Case 2: "my chest is killing me and my left arm hurts really bad" (should detect MI)
- Case 4: "i cant stop coughing and i'm coughing up blood" (should detect pneumonia/TB)
- Case 6: "worst headache of my life and my neck is super stiff" (should detect meningitis)
- Case 8: "my face is drooping and i cant talk right and my arm is weak" (should detect stroke)
- Case 10: "bad stomach pain and i'm throwing up everything" (should detect gastroenteritis)
- Case 12: "i got heartburn and my throat is burning" (should detect GERD)
- Case 14: "im freaking out and i cant breathe and my heart is racing" (should detect panic)
- Case 30: "i see flashing lights and then my head starts hurting" (should detect migraine with aura)

### Professional Language Test Cases (Baseline Accuracy)
- Case 1: "acute myocardial infarction with chest pain radiating to left arm"
- Case 3: "pneumonia with fever and productive cough"
- Case 5: "severe headache with stiff neck and high fever"
- Case 7: "sudden facial droop with slurred speech and arm weakness"
- Case 21: "croup in 3-year-old with barky cough and stridor"
- Case 28: "hypertension crisis with severe headache and chest pain"

## Evaluation Success Metrics

| Metric | Target | Importance |
|--------|--------|-----------|
| Emergency red flag detection (HIGH) | 100% | Patient safety - non-negotiable |
| Overall pass rate | 70%+ | System baseline competence |
| HIGH urgency accuracy | 80%+ | Safety margin for critical cases |
| Professional language | 85%+ | Establishes baseline with medical terminology |
| Colloquial language | 70%+ | Real-world patient understanding |
| Pediatric accuracy | 70%+ | Age-aware logic should enable this |
| Specialty matching | 75%+ | RAG + reasoner quality |
| Condition detection | 70%+ | LLM reasoning capability |

## Running Evaluations

### Quick Check (First 10 Cases)
```python
from backend.app.services.triage_service import triage

test_query = "my chest is killing me and my left arm hurts really bad"
result = triage(query=test_query, age=58)

print(f"Urgency: {result.urgency}")  # Expected: HIGH
print(f"Specialty: {result.specialty}")  # Expected: Cardiology
print(f"Condition: {result.suspected_condition}")  # Expected: MI/CAD
```

### Full Evaluation
```bash
cd backend
python eval_triage.py  # Generates evaluation_report.json
```

### With pytest
```bash
pytest tests/test_triage_prioritization.py -v
```

## Expected Output Format

```json
{
  "id": 2,
  "name": "Heart Attack - Colloquial",
  "query": "my chest is killing me and my left arm hurts really bad",
  "age": 58,
  "expected_urgency": "HIGH",
  "expected_specialty": "Cardiology",
  "expected_condition": "Myocardial infarction/Coronary artery disease",
  "language_type": "colloquial",
  "category": "chest_disease",
  "passed": true,
  "urgency_match": true,
  "specialty_match": true,
  "condition_match": true
}
```

## Notes for System Developers

1. **Colloquial Language:** Real patients don't say "acute myocardial infarction." They say "my chest hurts," "my heart is racing," "crushing pain." Train on real patient language.

2. **Age Matters:** A 6-month-old with fever is HIGH urgency. A 40-year-old with fever is probably MEDIUM or LOW. The `age` parameter enables context-specific triage.

3. **Safety First:** Emergency red flags must ALWAYS be HIGH urgency. If the system misses a meningitis, stroke, or MI case as not HIGH urgency, that's a failure.

4. **Professional Baseline:** Professional language cases establish baseline accuracy. If the system fails on professional medical terminology, colloquial language won't work.

5. **RAG Quality:** The evaluation is only as good as the RAG system's retrieved articles. Better articles = better LLM reasoning = better condition detection.

6. **Reasoner Quality:** The LLM's ability to reason about medical conditions determines condition accuracy. The prompt must encourage explicit condition naming.

---
*Last Updated: RAG Evaluation Framework v1.0*
*70 Test Cases Ready for Quality Assessment*
