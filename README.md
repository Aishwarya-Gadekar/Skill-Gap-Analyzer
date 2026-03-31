# Skill-Gap-Analyzer — Setup & Run

Short guide for team members to get the project running locally (macOS / zsh). This repository contains a Streamlit app that analyzes resumes vs job descriptions and logs searches to a small SQLite database.

## Prerequisites
- Python 3.8+ installed (python3 command available)
- Git

## Quick setup (recommended)
Run these commands from the project root (`/Users/aishwaryagadekar/Desktop/Skill-Gap-Analyzer`):

```bash
# create & activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Database: initialize and import CSVs (optional)
The app falls back to CSVs if the DB is empty, but you can import CSVs into the local SQLite DB once so the app reads tables directly.

```bash
# create DB tables and import CSVs into skillgap.db
python3 -c "from db import import_csvs; import_csvs()"

# confirm DB created
ls -l skillgap.db
sqlite3 skillgap.db ".tables"
```

Notes:
- The DB defaults to SQLite file `skillgap.db` in the project root. To use a remote DB, set `DATABASE_URL` environment variable before running the app, e.g.:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

## Run the Streamlit app

```bash
streamlit run app.py
```

Open the URL printed by Streamlit (usually http://localhost:8501).

## ERP-style login (how credentials are stored)
- Users have `erp_id` and a password. Passwords are hashed with bcrypt via `passlib` and stored in the DB as `password_hash`.

To create a test user from the command line:

```python
from db import Session, init_db, create_user
init_db()
s = Session()
u = create_user(s, erp_id='XYZ', password='ABC', name='Student Name', email='student@example.com')
print('created user id=', u.id)
```

To verify credentials programmatically:

```python
from db import Session, verify_user
s = Session()
user = verify_user(s, 'XYZ', 'ABC')
print('verified' if user else 'invalid')
```

## Where logs are stored
- Analyses are written to the `search_logs` table (timestamp, matched/missing skills, similarity, ATS score, final score). You can inspect it with sqlite3 or add an admin page to Streamlit.

## Files of interest
- `app.py` — Streamlit UI and analysis flow (now logs to DB)
- `db.py` — SQLAlchemy models & helpers (`init_db`, `import_csvs`, `log_search`, `create_user`, `verify_user`)
- `courses.csv`, `job_title_des.csv` — source CSVs used to seed DB
- `requirements.txt` — Python dependencies

## Troubleshooting
- ModuleNotFoundError or ImportError: ensure virtualenv is active and `pip install -r requirements.txt` completed.
- Streamlit not opening / blank page: check terminal where you ran `streamlit run app.py` for Python exceptions.
- DB not populated: run `python3 -c "from db import import_csvs; import_csvs()"` to seed tables.

## Suggested next steps
- Add a small login page in `app.py` to tie `user_id` to logs.
- Persist uploaded resume files into the `resumes` table and attach their `resume_id` to `search_logs`.
- Add an admin Streamlit page to query `search_logs` and export reports.

If you want, I can implement the login UI and resume persistence next and open a PR with those changes.
