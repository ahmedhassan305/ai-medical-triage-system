import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
os.environ["USE_TF"] = "0"
os.environ["DATABASE_URL"] = "postgresql+psycopg2://triage:triage@localhost:5437/triage"

from app.services.triage_service import triage
from app.db.session import SessionLocal

db = SessionLocal()

TESTS = [
    ("my 3 year old has been coughing for a week and has a fever", "medium", "Pediatrics"),
    ("my baby is breathing fast and making a whistling sound", "high", "Pediatrics"),
    ("my child woke up with a barking cough and can barely breathe", "high", "Pediatrics"),
    ("my 5 year old has been wheezing and using his chest muscles to breathe", "high", "Pediatrics"),
    ("my toddler has a runny nose fever and is not eating for 3 days", "low", "Pediatrics"),
    ("my 2 year old has blue lips and is struggling to breathe", "high", "Pediatrics"),
    ("my 8 year old has had a cough for 3 weeks with night sweats", "medium", "Pediatrics"),
    ("my baby keeps stopping breathing for a few seconds while sleeping", "high", "Pediatrics"),
    ("my 4 year old has a fever of 40 degrees and is very lethargic", "high", "Pediatrics"),
    ("my child has been sick with a cold for 2 days", "low", "Pediatrics"),
    ("my 6 year old is coughing at night and has trouble sleeping", "low", "Pediatrics"),
    ("my baby has a high fever and a stiff neck", "high", "Pediatrics"),
    ("my toddler swallowed a small toy and is coughing", "high", "Pediatrics"),
    ("my 7 year old has asthma and his inhaler is not helping", "high", "Pediatrics"),
    ("my child has a mild cough and no fever", "low", "Pediatrics"),
    ("i feel my heart beating really fast and i am dizzy", "medium", "Cardiology"),
    ("i have chest pain that spreads to my left arm", "high", "Cardiology"),
    ("i feel my heart skipping beats sometimes", "medium", "Cardiology"),
    ("i get short of breath when i climb stairs and my ankles are swollen", "medium", "Cardiology"),
    ("i fainted suddenly with no warning", "high", "Cardiology"),
    ("i have chest tightness when i exercise that goes away when i rest", "medium", "Cardiology"),
    ("i have been having chest pain for 3 hours that is not going away", "high", "Cardiology"),
    ("my heart races when i stand up quickly", "low", "Cardiology"),
    ("i have high blood pressure and a severe headache", "high", "Cardiology"),
    ("i feel a fluttering feeling in my chest occasionally", "low", "Cardiology"),
    ("i suddenly cannot move my right arm and my face is drooping", "high", "Neurology"),
    ("i have been having severe headaches every day for 2 weeks", "medium", "Neurology"),
    ("i had a seizure for the first time in my life", "high", "Neurology"),
    ("i have been getting migraines with flashing lights", "medium", "Neurology"),
    ("i feel dizzy and the room is spinning when i move my head", "medium", "Neurology"),
    ("i have numbness and tingling in both hands and feet", "medium", "Neurology"),
    ("i suddenly have the worst headache of my life", "high", "Neurology"),
    ("i have been having memory problems and forgetting things frequently", "medium", "Neurology"),
    ("i have a mild headache after staring at screens all day", "low", "Neurology"),
    ("i have weakness in my legs that has been getting worse over weeks", "medium", "Neurology"),
    ("i have been feeling sad and not wanting to do anything for months", "low", "Psychiatry"),
    ("i am having thoughts of hurting myself", "high", "Psychiatry"),
    ("i have not slept in 3 days and feel like i have superpowers", "high", "Psychiatry"),
    ("i feel very anxious and panicky in public places", "low", "Psychiatry"),
    ("i hear voices telling me to do things", "high", "Psychiatry"),
    ("i have been feeling stressed and overwhelmed at work", "low", "Psychiatry"),
    ("i have been washing my hands hundreds of times a day", "medium", "Psychiatry"),
    ("i have a sharp pain in my stomach that gets worse after eating", "medium", "Gastroenterology"),
    ("i have been vomiting blood", "high", "Gastroenterology"),
    ("i have had diarrhea for 5 days and feel very weak", "medium", "Gastroenterology"),
    ("my skin and eyes have turned yellow", "medium", "Gastroenterology"),
    ("i have severe pain in my right lower abdomen", "high", "Gastroenterology"),
    ("i have mild indigestion after eating spicy food", "low", "Gastroenterology"),
    ("i have been constipated for 2 weeks and have blood in my stool", "medium", "Gastroenterology"),
    ("i have a burning feeling in my chest after meals", "low", "Gastroenterology"),
    ("my back hurts and my left arm feels numb again", "medium", "Orthopedics"),
    ("i fell and my wrist is swollen and i cannot move it", "medium", "Orthopedics"),
    ("i have had lower back pain for 3 months", "low", "Orthopedics"),
    ("my knee swelled up suddenly after playing football", "medium", "Orthopedics"),
    ("i have pain in my neck that goes down to my fingers", "medium", "Orthopedics"),
    ("i fell from a height and cannot feel my legs", "high", "Orthopedics"),
    ("i have mild joint pain in my fingers in the morning", "low", "Orthopedics"),
    ("my shoulder has been dislocated", "medium", "Orthopedics"),
    ("my eye is red and watery and i have a discharge", "low", "Ophthalmology"),
    ("i suddenly lost vision in one eye", "high", "Ophthalmology"),
    ("i have been having double vision for 2 days", "medium", "Ophthalmology"),
    ("my eye hurts and is very sensitive to light", "medium", "Ophthalmology"),
    ("i have mild eye strain from reading", "low", "Ophthalmology"),
    ("i have had a sore throat for 2 weeks and it is getting worse", "medium", "ENT"),
    ("my throat is closing and i cannot swallow", "high", "ENT"),
    ("i have been losing my hearing gradually over months", "medium", "ENT"),
    ("i have ringing in my ears that wont go away", "low", "ENT"),
    ("i have a nosebleed that wont stop after 20 minutes", "medium", "ENT"),
    ("i have a mild earache and blocked ear", "low", "ENT"),
    ("i have a rash on my face that spreads to my neck", "low", "Dermatology"),
    ("i have a mole that has changed color and shape", "medium", "Dermatology"),
    ("i have widespread hives and my throat is itchy", "high", "Dermatology"),
    ("i have been having severe itching all over my body", "low", "Dermatology"),
    ("i have a wound that is not healing and smells bad", "medium", "Dermatology"),
    ("i have mild dry skin on my hands", "low", "Dermatology"),
    ("i burned my hand on the stove pretty badly", "medium", "Internal Medicine"),
    ("i have been losing weight without trying and feel tired all the time", "medium", "Internal Medicine"),
    ("i have a fever of 39 degrees for 4 days", "medium", "Internal Medicine"),
    ("i feel extremely thirsty all the time and urinate frequently", "medium", "Internal Medicine"),
    ("i have been very tired for months and look pale", "medium", "Internal Medicine"),
    ("i have a mild cold with runny nose", "low", "Internal Medicine"),
    ("i have swollen lymph nodes in my neck for 3 weeks", "medium", "Internal Medicine"),
    ("i have a small cut that is bleeding", "low", "Internal Medicine"),
    ("i feel generally unwell with body aches and no energy", "low", "Internal Medicine"),
    ("i took too many pills on purpose", "high", "Psychiatry"),
    ("i hit my head hard and now have a severe headache and am vomiting", "high", "Neurology"),
    ("i have back pain with numbness in both legs and cannot control my bladder", "high", "Neurology"),
    ("i had a car accident and have neck pain and tingling in my arms", "high", "Neurology"),
    ("i have a headache after a minor bump on the head yesterday", "low", "Neurology"),
    ("i have increasing weakness in my arms and legs over 2 weeks", "medium", "Neurology"),
    ("i have not had my period for 3 months and feel nauseous in the morning", "low", "Internal Medicine"),
    ("i have a urinary burning sensation and frequent urination", "low", "Internal Medicine"),
    ("i have been sneezing and have itchy eyes every spring", "low", "Internal Medicine"),
    ("my child has a temperature of 38 and is playful", "low", "Pediatrics"),
    ("i have pain when swallowing and a white coating on my tongue", "low", "Internal Medicine"),
    ("i have severe chest pain shortness of breath and sweating", "high", "Cardiology"),
    ("i have sudden vision loss and severe headache", "high", "Neurology"),
    ("i have a painless lump in my neck for 2 months", "medium", "Internal Medicine"),
    ("i feel faint and sweaty and my vision is blurry", "medium", "Internal Medicine"),
    ("i have mild lower back pain after sitting at a desk all day", "low", "Orthopedics"),
]

CATEGORIES = {
    "Pediatric Respiratory": range(1, 16),
    "Cardiology": range(16, 26),
    "Neurology": range(26, 36),
    "Psychiatry": range(36, 43),
    "Gastroenterology": range(43, 51),
    "Orthopedics": range(51, 59),
    "Ophthalmology": range(59, 64),
    "ENT": range(64, 70),
    "Dermatology": range(70, 76),
    "Internal Medicine": range(76, 86),
    "Neuro/Trauma": range(86, 91),
    "Mixed/Family": range(91, 101),
}

print(f"\n{'#':<4} {'Query':<50} {'Got':>7} {'Exp':>7} {'Specialty':<22} {'ExpSp':<18} U S")
print("-" * 120)

urgency_correct = 0
specialty_correct = 0
errors = 0
results = []

for i, (query, exp_u, exp_s) in enumerate(TESTS, 1):
    try:
        t0 = time.time()
        result = triage(query, patient_id=None, db=db)
        elapsed = time.time() - t0
        got_u = result.triage_level
        got_s = result.recommended_specialty or "None"
        u_ok = "✓" if got_u == exp_u else "✗"
        s_ok = "✓" if exp_s.lower() in got_s.lower() else "✗"
        if u_ok == "✓": urgency_correct += 1
        if s_ok == "✓": specialty_correct += 1
        results.append((i, got_u, exp_u, got_s, exp_s, u_ok, s_ok))
        print(f"{i:<4} {query[:49]:<50} {got_u:>7} {exp_u:>7} {got_s:<22} {exp_s:<18} {u_ok} {s_ok} ({elapsed:.0f}s)")
    except Exception as e:
        errors += 1
        print(f"{i:<4} {query[:49]:<50} ERROR: {str(e)[:50]}")

total = len(TESTS) - errors
print("-" * 120)
print(f"\nURGENCY ACCURACY:   {urgency_correct}/{total} = {urgency_correct/total*100:.1f}%")
print(f"SPECIALTY ACCURACY: {specialty_correct}/{total} = {specialty_correct/total*100:.1f}%")
print(f"OVERALL:            {(urgency_correct+specialty_correct)/(2*total)*100:.1f}%")
print(f"\n{'Category':<25} {'Urgency':>12} {'Specialty':>12}")
print("-" * 52)
for cat, rng in CATEGORIES.items():
    cr = [r for r in results if r[0] in rng]
    if not cr: continue
    u = sum(1 for r in cr if r[5]=="✓")
    s = sum(1 for r in cr if r[6]=="✓")
    n = len(cr)
    print(f"{cat:<25} {u}/{n} ({u/n*100:.0f}%){'':>5} {s}/{n} ({s/n*100:.0f}%)")
db.close()
