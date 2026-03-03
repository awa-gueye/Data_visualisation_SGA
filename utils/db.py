"""
utils/db.py – Helpers base de données
"""
import bcrypt
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as DBSession
from models import Base, User, Student, Course, Session, Attendance, Grade
from config import DATABASE_URL


# ─────────────────────────────────────────────────────────────────────────────
#  Engine & Session factory
# ─────────────────────────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> DBSession:
    """Retourne une nouvelle session DB (à fermer manuellement)."""
    return SessionFactory()


def init_db():
    """Crée toutes les tables si elles n'existent pas + seed data."""
    Base.metadata.create_all(engine)
    _seed_default_data()
    print("✅ Base de données initialisée.")


# ─────────────────────────────────────────────────────────────────────────────
#  Seed Data
# ─────────────────────────────────────────────────────────────────────────────
def _seed_default_data():
    db = get_db()
    try:
        # Admin par défaut
        if not db.query(User).filter_by(username="admin").first():
            hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            admin = User(
                username="admin",
                email="admin@sga.fr",
                password=hashed,
                role="admin",
                full_name="Administrateur SGA",
            )
            db.add(admin)

        # Données de démonstration
        if db.query(Course).count() == 0:
            _seed_demo_data(db)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Seed error: {e}")
    finally:
        db.close()


def _seed_demo_data(db):
    from datetime import date, timedelta
    import random

    # Cours
    courses_data = [
        ("MATH101", "Mathématiques", 60, "Prof. Martin",  "#6C63FF"),
        ("INFO201", "Informatique",  48, "Prof. Dupont",  "#FF6584"),
        ("PHYS101", "Physique",      54, "Prof. Bernard", "#43E97B"),
        ("CHIM101", "Chimie",        42, "Prof. Leroy",   "#F7B731"),
        ("ANGL101", "Anglais",       36, "Prof. Smith",   "#45AAF2"),
    ]
    courses = []
    for code, label, hours, teacher, color in courses_data:
        c = Course(code=code, label=label, total_hours=hours,
                   teacher=teacher, color=color)
        db.add(c)
        courses.append(c)

    db.flush()

    # Étudiants
    students_data = [
        ("Alice",  "Dubois",   "alice@etud.fr",   date(2002, 3, 15)),
        ("Bob",    "Martin",   "bob@etud.fr",     date(2001, 7, 22)),
        ("Clara",  "Petit",    "clara@etud.fr",   date(2003, 1, 8)),
        ("David",  "Leroy",    "david@etud.fr",   date(2002, 11, 30)),
        ("Emma",   "Bernard",  "emma@etud.fr",    date(2001, 5, 14)),
        ("Florian","Rousseau", "florian@etud.fr", date(2003, 9, 2)),
        ("Gaëlle", "Simon",    "gaelle@etud.fr",  date(2002, 6, 18)),
        ("Hugo",   "Michel",   "hugo@etud.fr",    date(2001, 12, 25)),
    ]
    students = []
    for i, (fn, ln, email, bd) in enumerate(students_data, 1):
        s = Student(
            student_code=f"ETU-2024-{i:03d}",
            first_name=fn, last_name=ln,
            email=email, birth_date=bd,
        )
        db.add(s)
        students.append(s)

    db.flush()

    # Séances + présences + notes
    today = date.today()
    for course in courses:
        for w in range(6):
            sess_date = today - timedelta(days=7 * (6 - w))
            sess = Session(
                course_id=course.id,
                date=sess_date,
                duration=2,
                theme=f"Séance {w+1} – {course.label}",
                room=f"Salle {random.choice(['A101','B202','C303'])}",
            )
            db.add(sess)
            db.flush()

            for student in students:
                absent = random.random() < 0.15
                att = Attendance(
                    session_id=sess.id,
                    student_id=student.id,
                    is_absent=absent,
                    justified=absent and random.random() < 0.4,
                )
                db.add(att)

        # Notes
        for student in students:
            for label, coeff in [("TP Noté", 1), ("Examen Final", 2)]:
                score = round(random.uniform(8, 19), 1)
                g = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    score=score,
                    coefficient=coeff,
                    label=label,
                )
                db.add(g)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers CRUD génériques
# ─────────────────────────────────────────────────────────────────────────────
def get_all(model, active_only=True):
    db = get_db()
    try:
        q = db.query(model)
        if active_only and hasattr(model, "is_active"):
            q = q.filter(model.is_active == True)
        return q.all()
    finally:
        db.close()


def get_by_id(model, record_id):
    db = get_db()
    try:
        return db.query(model).get(record_id)
    finally:
        db.close()


def safe_commit(db, obj=None):
    try:
        if obj:
            db.add(obj)
        db.commit()
        return True, None
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()