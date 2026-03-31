import pandas as pd
import re
import streamlit as st
import PyPDF2
import matplotlib.pyplot as plt
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from db import init_db, Session, import_csvs, log_search

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="SkillGap AI", layout="wide")

st.markdown("""
<h1 style='text-align: center; color: #4CAF50;'>
🧠 SkillGap AI – AI Career & Recruiter System
</h1>
""", unsafe_allow_html=True)

# ---------------- LOAD DATA ---------------- #
# initialize DB and session
init_db()
db_session = Session()

# prefer DB tables if present, otherwise fall back to CSVs (import_csvs can be run once)
try:
    jobs = pd.read_sql('SELECT title AS "Job Title", description AS "Job Description" FROM jobs', db_session.bind)
    courses = pd.read_sql('SELECT * FROM courses', db_session.bind)
    if jobs.empty:
        raise Exception("empty")
except Exception:
    jobs = pd.read_csv("job_title_des.csv")
    jobs = jobs[['Job Title', 'Job Description']]
    jobs.dropna(inplace=True)
    courses = pd.read_csv("courses.csv")

# ---------------- CLEAN TEXT ---------------- #
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text

# ---------------- TRAIN MODEL ---------------- #
jobs['cleaned'] = jobs['Job Description'].apply(clean_text)

vectorizer = TfidfVectorizer(stop_words='english', max_features=3000)
tfidf_matrix = vectorizer.fit_transform(jobs['cleaned'])

# ---------------- SKILLS ---------------- #
skills_list = [
    "python", "sql", "machine learning", "deep learning",
    "data analysis", "nlp", "computer vision",
    "java", "c++", "react", "nodejs",
    "html", "css", "javascript"
]

# ---------------- PDF ---------------- #
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

# ---------------- CORE FUNCTIONS ---------------- #

def extract_skills(text):
    text = text.lower()
    return list(set([skill for skill in skills_list if skill in text]))

def calculate_similarity(resume_text, job_text):
    texts = [clean_text(resume_text), clean_text(job_text)]
    vectors = vectorizer.transform(texts)
    return cosine_similarity(vectors[0], vectors[1])[0][0]

def calculate_gap(student_skills, job_skills):
    student_set = set(student_skills)
    job_set = set(job_skills)
    return student_set & job_set, job_set - student_set

def selection_probability(similarity, matched, missing):
    score = similarity * 60
    skill_score = (len(matched) / (len(matched) + len(missing))) * 40 if (matched or missing) else 0
    return round(score + skill_score, 2)

def ats_score(resume_text, job_text):
    resume_words = set(clean_text(resume_text).split())
    job_words = set(clean_text(job_text).split())
    match = resume_words & job_words
    return round((len(match) / len(job_words)) * 100, 2) if job_words else 0

def analyze_profile(matched, missing):
    return [f"Strong in {s}" for s in matched], [f"Lacking {s}" for s in missing]

def recommend_courses(missing_skills):
    recommendations = {}
    for skill in missing_skills:
        matches = courses[courses['skill'].str.lower() == skill]
        if not matches.empty:
            recommendations[skill] = matches['resource'].tolist()
    return recommendations

def generate_questions(missing_skills):
    q = []
    for skill in missing_skills:
        q.append(f"Explain your understanding of {skill}.")
        q.append(f"Have you worked on any project using {skill}?")
    return q[:5]

def final_score(prob, ats):
    return round((prob * 0.6 + ats * 0.4), 2)

def insights(score):
    if score > 75:
        return "High chance of selection. Strong profile."
    elif score > 50:
        return "Moderate chance. Improve key skills."
    else:
        return "Low chance. Significant skill gaps detected."

def predict_role_from_resume(resume_text):
    vec = vectorizer.transform([clean_text(resume_text)])
    sim = cosine_similarity(vec, tfidf_matrix)
    return jobs.iloc[sim.argmax()]['Job Title']

# ---------------- FRAUD DETECTION ---------------- #

def detect_fraud(job_text):
    job_text = clean_text(job_text)

    fraud_keywords = [
        "earn money fast", "no experience required", "work from home",
        "urgent hiring", "pay registration fee", "limited seats",
        "guaranteed job", "easy money", "click here", "whatsapp only"
    ]

    score = sum(1 for word in fraud_keywords if word in job_text)

    if len(job_text.split()) < 30:
        score += 2

    if score >= 3:
        return "Fraudulent"
    elif score == 2:
        return "Suspicious"
    else:
        return "Safe"

# ---------------- VISUAL ---------------- #

def radar_chart(matched, missing):
    labels = ["Matched", "Missing"]
    values = [len(matched), len(missing)]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    values = np.concatenate((values,[values[0]]))
    angles = np.concatenate((angles,[angles[0]]))

    fig, ax = plt.subplots(subplot_kw={'polar': True})
    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.25)

    ax.set_thetagrids(angles[:-1] * 180/np.pi, labels)
    st.pyplot(fig)

# ---------------- UI ---------------- #

uploaded_file = st.file_uploader("📄 Upload Resume", type=["pdf"])
resume_text = st.text_area("OR paste resume text")

job_input = st.text_area("📄 Paste Job Description (optional)")

if st.button("🚀 Analyze"):

    resume = extract_text_from_pdf(uploaded_file) if uploaded_file else resume_text

    # ---------------- RESUME ONLY ---------------- #
    if resume.strip() and not job_input.strip():

        role = predict_role_from_resume(resume)
        skills = extract_skills(resume)

        st.subheader("🎯 Best Fit Role")
        st.success(role)

        st.subheader("🧠 Detected Skills")
        st.write(skills)

        st.info("Upload a job description to analyze selection chances.")

    # ---------------- FULL MODE ---------------- #
    elif resume.strip() and job_input.strip():

        st.subheader("🛡️ Job Safety Check")
        fraud = detect_fraud(job_input)

        if fraud == "Fraudulent":
            st.error("⚠️ This job looks FRAUDULENT")
        elif fraud == "Suspicious":
            st.warning("⚠️ This job looks SUSPICIOUS")
        else:
            st.success("✅ Job looks SAFE")

        student_skills = extract_skills(resume)
        job_skills = extract_skills(job_input)

        sim = calculate_similarity(resume, job_input)
        matched, missing = calculate_gap(student_skills, job_skills)

        prob = selection_probability(sim, matched, missing)
        ats = ats_score(resume, job_input)
        final = final_score(prob, ats)

        strengths, weaknesses = analyze_profile(matched, missing)

        st.subheader("📊 Scores")
        st.write(f"Selection Probability: {prob}%")
        st.write(f"ATS Score: {ats}%")
        st.write(f"Final Score: {final}%")

        st.write(insights(final))

        st.subheader("💪 Strengths")
        for s in strengths:
            st.write("✅", s)

        st.subheader("⚠️ Weaknesses")
        for w in weaknesses:
            st.write("❌", w)

        radar_chart(matched, missing)

        st.subheader("📚 Recommendations")
        rec = recommend_courses(missing)
        for skill, r in rec.items():
            st.write(skill, "→", r)

        st.subheader("🎤 Interview Questions")
        for q in generate_questions(missing):
            st.write("👉", q)

        # ---------------- LOG TO DB ---------------- #
        try:
            log_search(
                db_session,
                user_id=None,
                resume_id=None,
                query_text=resume,
                job_text=job_input,
                fraud_flag=fraud,
                similarity=sim,
                matched_skills=list(matched),
                missing_skills=list(missing),
                prob=prob,
                ats=ats,
                final_score=final
            )
        except Exception as e:
            st.warning(f"Failed to write log to DB: {e}")

    else:
        st.warning("Please upload resume or enter text!")