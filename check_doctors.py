#!/usr/bin/env python3
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

os.environ.setdefault("ENVIRONMENT", "development")

from app.db.session import SessionLocal
from app.db.models import DoctorProfile

def check_doctors():
    with SessionLocal() as db:
        count = db.query(DoctorProfile).count()
        print(f"[OK] Total doctors in database: {count}")
        
        if count > 0:
            print("\nSample doctors:")
            doctors = db.query(DoctorProfile).limit(5).all()
            for doc in doctors:
                print(f"  - {doc.full_name} ({doc.specialty}) at {doc.clinic}")
            return True
        else:
            print("[MISSING] No doctors found - will seed now...")
            return False

if __name__ == "__main__":
    if not check_doctors():
        print("\nSeeding doctors...")
        os.chdir(Path(__file__).parent)
        os.system("python scripts/seed_doctors.py")
        print("\nRechecking doctor count...")
        check_doctors()
