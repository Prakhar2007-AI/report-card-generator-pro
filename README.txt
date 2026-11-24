STUDENT REPORT CARD GENERATOR - NO FLASK

This version uses only Python's standard library. HTML and CSS are copied unchanged.

LOCAL TEST
1. Open this folder in VS Code.
2. Run: python main.py
3. Open: http://127.0.0.1:8000

VERCEL
1. Upload the contents of this folder to the ROOT of your GitHub repository.
2. Import that repository into Vercel and deploy.
3. Vercel's Python runtime detects the WSGI callable named `app` in main.py.

IMPORTANT DATABASE NOTE
This version uses SQLite. Locally, records are saved in students.db beside main.py.
On Vercel, the database is placed in /tmp because the deployment filesystem is not
persistent. Records can be lost when the function is restarted. For permanent online
records, a hosted database is required; this cannot be solved by changing Python code
alone. The HTML and CSS are not changed in this version.

No Flask, SQLAlchemy, or other pip packages are needed.
