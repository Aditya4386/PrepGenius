"""
Utility script to view all records in the PrepGenius MySQL database.
Run with:
    .\.venv\Scripts\python.exe app/scripts/view_db.py
"""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.modules.profile.models import Student, StudentProfile

engine = create_engine(settings.get_database_url())
Session = sessionmaker(bind=engine)
db = Session()


def print_divider(title: str):
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def view_all():
    print_divider("DATABASE: prepgenius (MySQL 8.0)")

    # 1. Students Table
    students = db.query(Student).all()
    print(f"\n[TABLE: students] ({len(students)} records found)")
    print("-" * 80)
    print(f"{'Student ID':<24} | {'Full Name':<20} | {'Email':<30}")
    print("-" * 80)
    for s in students:
        s_id = s.id or ""
        name = s.full_name or "—"
        email = s.email or "—"
        print(f"{s_id:<24} | {name:<20} | {email:<30}")

    # 2. Profiles Table
    profiles = db.query(StudentProfile).all()
    print_divider(f"TABLE: student_profiles ({len(profiles)} records found)")

    for idx, p in enumerate(profiles, start=1):
        # Find associated student
        student = db.query(Student).filter(Student.id == p.student_id).first()
        student_label = f"{student.full_name} ({student.email})" if student and student.full_name else p.student_id

        print(f"\n--- [{idx}] Student: {student_label} ---")
        print(f"  • Student ID         : {p.student_id}")
        print(f"  • Target Role        : {p.target_role or 'Not Selected'}")
        print(f"  • Company Category   : {p.company_type or 'Not Selected'}")
        print(f"  • Weekly Study Hours : {p.weekly_study_hours} hrs/week")
        print(f"  • Target Deadline    : {p.preparation_deadline or 'Unspecified (12 weeks default)'}")
        print(f"  • Target Companies   : {', '.join(p.target_companies) if p.target_companies else 'None'}")
        print(f"  • Career Goal        : {p.career_goal or 'None'}")

        # Skills
        if p.skills:
            skills_str = ", ".join([f"{s.get('name')} ({s.get('level')})" for s in p.skills])
            print(f"  • Skills ({len(p.skills)})       : {skills_str}")
        else:
            print("  • Skills             : No skills added yet")

        # Education
        if p.education:
            print(f"  • Education History  : {len(p.education)} record(s)")
            for e in p.education:
                deg = e.get("degree") or "Degree"
                inst = e.get("institution") or "College"
                yr = e.get("year_of_completion") or ""
                cgpa = e.get("cgpa")
                cgpa_str = f" | CGPA: {cgpa}" if cgpa else ""
                print(f"      - {deg} at {inst} ({yr}){cgpa_str}")
        else:
            print("  • Education History  : No records added yet")

    print("\n" + "=" * 80 + "\n")
    db.close()


if __name__ == "__main__":
    view_all()
