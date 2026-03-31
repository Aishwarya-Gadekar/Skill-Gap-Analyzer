import os
import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, ForeignKey, DateTime, func
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from passlib.hash import bcrypt

# Configuration: use DATABASE_URL env var or fall back to local sqlite file
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///skillgap.db")

ENGINE = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=ENGINE)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    skill = Column(String)
    resource = Column(String)
    level = Column(String)
    type = Column(String)
    link = Column(String)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    # college-style login fields
    erp_id = Column(String, unique=True)
    password_hash = Column(String)


def create_user(session, erp_id, password, name=None, email=None):
    """Create a new user with hashed password. Returns user instance."""
    pw_hash = bcrypt.hash(password)
    user = User(name=name, email=email, erp_id=erp_id, password_hash=pw_hash)
    session.add(user)
    session.commit()
    return user


def verify_user(session, erp_id, password):
    """Verify a user's password. Returns user if ok, else None."""
    user = session.query(User).filter_by(erp_id=erp_id).first()
    if not user or not user.password_hash:
        return None
    if bcrypt.verify(password, user.password_hash):
        return user
    return None


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String)
    text = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class SearchLog(Base):
    __tablename__ = "search_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    query_text = Column(Text)
    job_text = Column(Text)
    fraud_flag = Column(String)
    similarity = Column(Float)
    matched_skills = Column(Text)
    missing_skills = Column(Text)
    prob = Column(Float)
    ats = Column(Float)
    final_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(ENGINE)


def import_csvs(jobs_csv="job_title_des.csv", courses_csv="courses.csv"):
    """Import existing CSVs into the database. Run once manually if needed."""
    init_db()
    session = Session()

    # import jobs
    if os.path.exists(jobs_csv):
        jobs_df = pd.read_csv(jobs_csv).dropna(subset=["Job Title", "Job Description"]) 
        for _, r in jobs_df.iterrows():
            session.add(Job(title=r["Job Title"], description=r["Job Description"]))

    # import courses
    if os.path.exists(courses_csv):
        courses_df = pd.read_csv(courses_csv)
        for _, r in courses_df.iterrows():
            session.add(Course(
                skill=r.get("skill", ""),
                resource=r.get("resource", ""),
                level=r.get("level", ""),
                type=r.get("type", ""),
                link=r.get("link", "")
            ))

    session.commit()
    session.close()


def log_search(session, user_id, resume_id, query_text, job_text, fraud_flag,
               similarity, matched_skills, missing_skills, prob, ats, final_score):
    """Record a search/analysis to the database.

    session: SQLAlchemy session (Session())
    matched_skills / missing_skills: list or comma string
    """
    matched = ",".join(matched_skills) if isinstance(matched_skills, (list, tuple)) else (matched_skills or "")
    missing = ",".join(missing_skills) if isinstance(missing_skills, (list, tuple)) else (missing_skills or "")

    rec = SearchLog(
        user_id=user_id,
        resume_id=resume_id,
        query_text=(query_text or "")[:20000],
        job_text=(job_text or "")[:20000],
        fraud_flag=fraud_flag,
        similarity=float(similarity) if similarity is not None else None,
        matched_skills=matched,
        missing_skills=missing,
        prob=float(prob) if prob is not None else None,
        ats=float(ats) if ats is not None else None,
        final_score=float(final_score) if final_score is not None else None,
    )
    session.add(rec)
    session.commit()
    return rec.id
