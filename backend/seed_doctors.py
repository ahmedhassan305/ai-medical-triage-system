import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal, engine
from app.db.models import Base, DoctorProfile

SEED_FILE = os.path.join(os.path.dirname(__file__), "data", "doctors", "alexandria_public_directory_seed.json")

def t(s, n=200):
    """Truncate string to n characters."""
    return (s or "")[:n]

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(DoctorProfile).count()
        if existing > 0:
            print(f"Already have {existing} doctors — skipping. Use --force to re-seed.")
            if "--force" not in sys.argv:
                return
            print("Force flag — clearing existing doctors...")
            db.query(DoctorProfile).delete()
            db.commit()

        with open(SEED_FILE) as f:
            data = json.load(f)

        inserted = 0
        for d in data["doctors"]:
            profile = DoctorProfile(
                full_name=t(d["full_name"], 100),
                specialty=t(d["specialty"], 100),
                clinic=t(d.get("clinic", ""), 500),
                area=t(d.get("area", ""), 100),
                city=t(d.get("city", "Alexandria"), 100),
                source_name=t(d.get("source_name", ""), 200),
                source_url=t(d.get("source_url", ""), 500),
                booking_url=t(d.get("booking_url", ""), 500),
            )
            db.add(profile)
            inserted += 1

        db.commit()
        print(f"Seeded {inserted} doctors successfully.")

        from sqlalchemy import func
        results = db.query(DoctorProfile.specialty, func.count()).group_by(DoctorProfile.specialty).order_by(DoctorProfile.specialty).all()
        print("\nDoctor count by specialty:")
        for specialty, count in results:
            print(f"  {specialty}: {count}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
