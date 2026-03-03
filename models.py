"""
models.py – Modèles SQLAlchemy pour le SGA
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, Boolean, Text, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ─────────────────────────────────────────────────────────────────────────────
#  Utilisateurs / Authentification
# ─────────────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True)
    username   = Column(String(64),  unique=True, nullable=False)
    email      = Column(String(128), unique=True, nullable=False)
    password   = Column(String(256), nullable=False)          # bcrypt hash
    role       = Column(String(16),  nullable=False, default="teacher")   # admin | teacher
    full_name  = Column(String(128))
    avatar_url = Column(String(256))
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    __table_args__ = (
        CheckConstraint("role IN ('admin','teacher')", name="ck_user_role"),
    )

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ─────────────────────────────────────────────────────────────────────────────
#  Étudiants
# ─────────────────────────────────────────────────────────────────────────────
class Student(Base):
    __tablename__ = "students"

    id            = Column(Integer, primary_key=True)
    student_code  = Column(String(20), unique=True, nullable=False)   # ex: ETU-2024-001
    first_name    = Column(String(64), nullable=False)
    last_name     = Column(String(64), nullable=False)
    email         = Column(String(128), unique=True, nullable=False)
    birth_date    = Column(Date)
    phone         = Column(String(20))
    address       = Column(Text)
    photo_url     = Column(String(256))
    is_active     = Column(Boolean, default=True)
    enrolled_at   = Column(DateTime, default=datetime.utcnow)

    # Relations
    grades      = relationship("Grade",      back_populates="student", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Student {self.full_name}>"


# ─────────────────────────────────────────────────────────────────────────────
#  Cours
# ─────────────────────────────────────────────────────────────────────────────
class Course(Base):
    __tablename__ = "courses"

    id            = Column(Integer, primary_key=True)
    code          = Column(String(20), unique=True, nullable=False)   # ex: MATH101
    label         = Column(String(128), nullable=False)
    description   = Column(Text)
    total_hours   = Column(Float, nullable=False, default=0)
    teacher       = Column(String(128))
    teacher_email = Column(String(128))
    color         = Column(String(7), default="#6C63FF")              # hex color for UI
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relations
    sessions = relationship("Session", back_populates="course", cascade="all, delete-orphan")
    grades   = relationship("Grade",   back_populates="course", cascade="all, delete-orphan")

    @property
    def hours_done(self):
        return sum(s.duration for s in self.sessions if s.duration)

    @property
    def progress_pct(self):
        if self.total_hours == 0:
            return 0
        return min(round(self.hours_done / self.total_hours * 100, 1), 100)

    def __repr__(self):
        return f"<Course {self.code} – {self.label}>"


# ─────────────────────────────────────────────────────────────────────────────
#  Séances
# ─────────────────────────────────────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    id          = Column(Integer, primary_key=True)
    course_id   = Column(Integer, ForeignKey("courses.id"), nullable=False)
    date        = Column(Date,    nullable=False)
    duration    = Column(Float,   nullable=False, default=2)   # heures
    theme       = Column(String(256))
    notes       = Column(Text)
    room        = Column(String(64))
    created_at  = Column(DateTime, default=datetime.utcnow)

    # Relations
    course      = relationship("Course",     back_populates="sessions")
    attendances = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session {self.course.code} – {self.date}>"


# ─────────────────────────────────────────────────────────────────────────────
#  Présences / Absences
# ─────────────────────────────────────────────────────────────────────────────
class Attendance(Base):
    __tablename__ = "attendances"

    id          = Column(Integer, primary_key=True)
    session_id  = Column(Integer, ForeignKey("sessions.id"),  nullable=False)
    student_id  = Column(Integer, ForeignKey("students.id"),  nullable=False)
    is_absent   = Column(Boolean, default=False)
    is_late     = Column(Boolean, default=False)
    justified   = Column(Boolean, default=False)
    comment     = Column(String(256))
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    session = relationship("Session", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance"),
    )

    def __repr__(self):
        status = "absent" if self.is_absent else "présent"
        return f"<Attendance {self.student_id} @ session {self.session_id} – {status}>"


# ─────────────────────────────────────────────────────────────────────────────
#  Notes
# ─────────────────────────────────────────────────────────────────────────────
class Grade(Base):
    __tablename__ = "grades"

    id          = Column(Integer, primary_key=True)
    student_id  = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id   = Column(Integer, ForeignKey("courses.id"),  nullable=False)
    score       = Column(Float,   nullable=False)
    coefficient = Column(Float,   default=1.0)
    label       = Column(String(128))          # ex: "Examen Final", "TP1"
    graded_at   = Column(DateTime, default=datetime.utcnow)

    # Relations
    student = relationship("Student", back_populates="grades")
    course  = relationship("Course",  back_populates="grades")

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 20", name="ck_score_range"),
        CheckConstraint("coefficient > 0",            name="ck_coeff_positive"),
    )

    def __repr__(self):
        return f"<Grade {self.student_id} in {self.course_id}: {self.score}/20>"


# ─────────────────────────────────────────────────────────────────────────────
#  Notifications
# ─────────────────────────────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    title      = Column(String(128), nullable=False)
    message    = Column(Text)
    type       = Column(String(16), default="info")   # info | warning | danger | success
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

    def __repr__(self):
        return f"<Notification {self.title} → user {self.user_id}>"