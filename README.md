# DBES Teacher Performance Appraisal System (TPAS) - Student Evaluation

Students scan a QR code (or open a link) for a teacher + grade level + subject and fill in TPAS Form 6.
HR sees averages per category, an overall score with its interpretation, comments, and responses per section.

## Run locally (no Turso needed for a first test)
    python -m venv .venv
    .venv\Scripts\activate          (Windows)
    pip install -r requirements.txt
    streamlit run Home.py
Without Turso secrets the app uses a local SQLite file (testing only).

## Logic tests
    python tests/test_core.py
    python tests/test_import.py

## Deploy
1. Create a NEW Turso database for this app and copy its URL and token.
2. Push this folder to a new GitHub repository.
3. On Streamlit Community Cloud: New app -> pick the repo -> main file `Home.py`.
4. Paste the contents of `.streamlit/secrets.toml.example` (with your real values) into the app's Secrets.
   Set APP_BASE_URL to the app's address, then reboot the app.
5. Open the app and create the HR account immediately.
6. Settings: set the school year (and the student email domain if you use school emails).
7. Bulk Import (sections, teachers, subjects) or add them by hand, then print the QR codes.

## Pages
Dashboard, Bulk Import, Sections & Enrollment, Teachers & Assignments, QR Codes & Links, Results, Settings,
and the public Evaluation Form (`/evaluate?t=CODE`).
