import pandas as pd
import re
import streamlit as st
import PyPDF2
import matplotlib.pyplot as plt
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="SkillGap AI", layout="wide")

st.markdown("""
<h1 style='text-align: center; color: #4CAF50;'>
🧠 SkillGap AI – AI Recruiter System
</h1>
""", unsafe_allow_html=True)

# ---------------- LOAD DATA ---------------- #
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

# ---------------- PDF READER ---------------- #
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

# ---------------- FUNCTIONS ---------------- #

def extract_skills(text):
    text = text.lower()
    return list(set([skill for skill in skills_list if skill in text]))

def calculate_similarity(resume_text, job_text):
    texts = [clean_text(resume_text), clean_text(job_text)]
    vectors = vectorizer.transform(texts)
    similarity = cosine_similarity(vectors[0], vectors[1])
    return similarity[0][0]

def calculate_gap(student_skills, job_skills):
    student_set = set(student_skills)
    job_set = set(job_skills)
    
    matched = student_set & job_set
    missing = job_set - student_set
    
    return matched, missing

def selection_probability(similarity, matched, missing):
    score = similarity * 60
    skill_score = (len(matched) / (len(matched) + len(missing))) * 40 if (matched or missing) else 0
    return round(score + skill_score, 2)

def ats_score(resume_text, job_text):
    resume_words = set(clean_text(resume_text).split())
    job_words = set(clean_text(job_text).split())
    
    match = resume_words & job_words
    score = (len(match) / len(job_words)) * 100 if job_words else 0
    
    return round(score, 2)

def analyze_profile(matched, missing):
    strengths = [f"Strong in {skill}" for skill in matched]
    weaknesses = [f"Lacking {skill}" for skill in missing]
    return strengths, weaknesses

def recommend_courses(missing_skills):
    recommendations = {}
    
    for skill in missing_skills:
        matches = courses[courses['skill'].str.lower() == skill]
        
        if not matches.empty:
            recommendations[skill] = matches['resource'].tolist()
    
    return recommendations

def generate_questions(missing_skills):
    questions = []
    
    for skill in missing_skills:
        questions.append(f"Explain your understanding of {skill}.")
        questions.append(f"Have you worked on any project using {skill}?")
    
    return questions[:5]

def final_score(prob, ats):
    return round((prob * 0.6 + ats * 0.4), 2)

def insights(score):
    if score > 75:
        return "High chance of selection. Strong profile."
    elif score > 50:
        return "Moderate chance. Improve key skills."
    else:
        return "Low chance. Significant skill gaps detected."

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

st.subheader("📄 Upload Resume or Enter Skills")

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
resume_text = st.text_area("OR paste resume text")

job_input = st.text_area("📄 Paste Job Description")

if st.button("🚀 Analyze"):
    
    if uploaded_file:
        resume = extract_text_from_pdf(uploaded_file)
    else:
        resume = resume_text
    
    if not resume.strip() or not job_input.strip():
        st.warning("Please provide both resume and job description!")
    
    else:
        # Processing
        student_skills = extract_skills(resume)
        job_skills = extract_skills(job_input)
        
        similarity = calculate_similarity(resume, job_input)
        matched, missing = calculate_gap(student_skills, job_skills)
        
        prob = selection_probability(similarity, matched, missing)
        ats = ats_score(resume, job_input)
        final = final_score(prob, ats)
        
        strengths, weaknesses = analyze_profile(matched, missing)
        recommendations = recommend_courses(missing)
        questions = generate_questions(missing)
        
        # ---------------- OUTPUT ---------------- #
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🎯 Selection Probability")
            st.success(f"{prob}%")
        
        with col2:
            st.subheader("📄 ATS Score")
            st.info(f"{ats}%")
        
        with col3:
            st.subheader("🏆 Final Score")
            st.success(f"{final}%")
        
        st.subheader("💡 Insight")
        st.write(insights(final))
        
        st.divider()
        
        st.subheader("💪 Strengths")
        for s in strengths:
            st.write(f"✅ {s}")
        
        st.subheader("⚠️ Weaknesses")
        for w in weaknesses:
            st.write(f"❌ {w}")
        
        st.divider()
        
        st.subheader("📊 Skill Analysis")
        radar_chart(matched, missing)
        
        st.divider()
        
        st.subheader("📚 Recommended Resources")
        for skill, res in recommendations.items():
            st.write(f"🔹 {skill}")
            for r in res:
                st.write(f"   → {r}")
        
        st.divider()
        
        st.subheader("🎤 Interview Questions")
        for q in questions:
            st.write(f"👉 {q}")