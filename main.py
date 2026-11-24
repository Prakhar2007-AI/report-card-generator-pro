"""Student Report Card Generator - pure Python WSGI app (no Flask/SQLAlchemy)."""
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs
from html import escape

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
# Local database is stored beside this file. Vercel's /tmp is writable but temporary.
DB_PATH = Path(os.environ.get("DB_PATH", "/tmp/students.db" if os.environ.get("VERCEL") else str(BASE_DIR / "students.db")))
SUBJECTS = [(f"subject{i}_name", f"subject{i}") for i in range(1, 6)]
DEFAULT_NAMES = [
    "Digital Logic Design", "AI Landscape and Tools",
    "Software Design and Development", "Linear Algebra",
    "Problem Solving and Python Programming",
]


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def create_table():
    with connect_db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, roll_no INTEGER NOT NULL, class_name TEXT NOT NULL,
            subject1 REAL, subject2 REAL, subject3 REAL, subject4 REAL, subject5 REAL,
            total REAL, percentage REAL, grade TEXT,
            subject1_name TEXT, subject2_name TEXT, subject3_name TEXT,
            subject4_name TEXT, subject5_name TEXT
        )""")
        existing = {r[1] for r in con.execute("PRAGMA table_info(students)")}
        for i, col in enumerate((f"subject{x}_name" for x in range(1, 6))):
            if col not in existing:
                con.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")
                con.execute(f"UPDATE students SET {col}=? WHERE {col} IS NULL", (DEFAULT_NAMES[i],))


def grade_for(value):
    if value >= 90: return "A+"
    if value >= 80: return "A"
    if value >= 70: return "B"
    if value >= 60: return "C"
    if value >= 40: return "D"
    return "Fail"


def remark_for(grade):
    return {
        "A+": "Outstanding performance", "A": "Excellent work",
        "B": "Very good performance", "C": "Good effort; keep improving",
        "D": "Needs more practice", "Fail": "Needs focused improvement",
    }[grade]


def read_json(environ):
    try:
        size = int(environ.get("CONTENT_LENGTH") or 0)
        return json.loads(environ["wsgi.input"].read(size).decode("utf-8")) if size else {}
    except (ValueError, json.JSONDecodeError):
        raise ValueError("Invalid request data.")


def prepare(data):
    name = str(data.get("name", "")).strip()
    class_name = str(data.get("class_name", "")).strip()
    roll_text = str(data.get("roll_no", "")).strip()
    if not name or not class_name or not roll_text:
        raise ValueError("Enter student name, roll number and class.")
    roll = int(roll_text)
    if roll < 0:
        raise ValueError("Roll number cannot be negative.")
    names, marks = [], []
    for name_key, mark_key in SUBJECTS:
        subject_name = str(data.get(name_key, "")).strip()
        mark_text = str(data.get(mark_key, "")).strip()
        if not subject_name or not mark_text:
            raise ValueError("Enter all five subject names and marks.")
        mark = float(mark_text)
        if not 0 <= mark <= 100:
            raise ValueError("Marks must be between 0 and 100.")
        names.append(subject_name)
        marks.append(mark)
    total = sum(marks)
    percentage = total / 5
    return name, roll, class_name, names, marks, total, percentage, grade_for(percentage)


def response(start_response, body, status="200 OK", content_type="text/html; charset=utf-8"):
    if isinstance(body, str): body = body.encode("utf-8")
    start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")])
    return [body]


def json_response(start_response, data, status="200 OK"):
    return response(start_response, json.dumps(data), status, "application/json; charset=utf-8")


def app(environ, start_response):
    """WSGI application loaded directly by Vercel's Python runtime."""
    try:
        create_table()
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()

        if method == "GET" and path == "/":
            return response(start_response, (PUBLIC_DIR / "index.html").read_text(encoding="utf-8"))
        if method == "GET" and path == "/style.css":
            return response(start_response, (PUBLIC_DIR / "style.css").read_bytes(), content_type="text/css; charset=utf-8")

        if method == "GET" and path == "/students":
            with connect_db() as con:
                rows = con.execute("SELECT id,name,roll_no,class_name,total,percentage,grade FROM students ORDER BY id DESC").fetchall()
            data = [{"id": r["id"], "name": r["name"], "roll_no": r["roll_no"], "class_name": r["class_name"], "total": r["total"], "percentage": round(r["percentage"] or 0, 2), "grade": r["grade"]} for r in rows]
            return json_response(start_response, data)

        if method == "GET" and path == "/student":
            student_id = parse_qs(environ.get("QUERY_STRING", "")).get("id", [""])[0]
            with connect_db() as con:
                row = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
            if not row: return json_response(start_response, {"success": False, "message": "Student not found."}, "404 Not Found")
            data = {"id": row["id"], "name": row["name"], "roll_no": row["roll_no"], "class_name": row["class_name"]}
            for i in range(1, 6):
                data[f"subject{i}_name"] = row[f"subject{i}_name"]
                data[f"subject{i}"] = row[f"subject{i}"]
            return json_response(start_response, {"success": True, "data": data})

        if method == "GET" and path == "/report":
            student_id = parse_qs(environ.get("QUERY_STRING", "")).get("id", [""])[0]
            with connect_db() as con:
                row = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
            if not row: return response(start_response, "Student record not found.", "404 Not Found")
            rows = "".join(
                f"<tr><td>{escape(str(row[f'subject{i}_name'] or ''))}</td><td>{row[f'subject{i}']:g} / 100</td><td>{grade_for(row[f'subject{i}'])}</td><td>{escape(remark_for(grade_for(row[f'subject{i}'])))}</td></tr>"
                for i in range(1, 6)
            )
            page = f'''<!DOCTYPE html><html><head><title>Student Report</title><link rel="stylesheet" href="/style.css"></head><body><div class="report"><h1>STUDENT REPORT CARD</h1><h2>{escape(row['name'])}</h2><p>Roll Number: {row['roll_no']}</p><p>Class: {escape(row['class_name'])}</p><table><tr><th>Subject</th><th>Marks</th><th>Grade</th><th>Remarks</th></tr>{rows}<tr><th>Total</th><th>{row['total']:g} / 500</th><th colspan="2"></th></tr></table><h2>Percentage: {row['percentage']:.2f}%</h2><h2>Overall Grade: {escape(row['grade'])}</h2><button onclick="window.print()">Print Report</button><p><a href="/">Go Back</a></p></div></body></html>'''
            return response(start_response, page)

        if method == "POST" and path in ("/add", "/update"):
            data = read_json(environ)
            name, roll, class_name, names, marks, total, percentage, grade = prepare(data)
            fields = [name, roll, class_name] + marks + [total, percentage, grade] + names
            with connect_db() as con:
                if path == "/add":
                    cols = "name,roll_no,class_name,subject1,subject2,subject3,subject4,subject5,total,percentage,grade,subject1_name,subject2_name,subject3_name,subject4_name,subject5_name"
                    con.execute(f"INSERT INTO students ({cols}) VALUES ({','.join(['?'] * 16)})", fields)
                    message = "Report card created successfully!"
                else:
                    student_id = int(data.get("id", 0))
                    cursor = con.execute("UPDATE students SET name=?,roll_no=?,class_name=?,subject1=?,subject2=?,subject3=?,subject4=?,subject5=?,total=?,percentage=?,grade=?,subject1_name=?,subject2_name=?,subject3_name=?,subject4_name=?,subject5_name=? WHERE id=?", fields + [student_id])
                    if not cursor.rowcount: return json_response(start_response, {"success": False, "message": "Student record not found."}, "404 Not Found")
                    message = "Student record updated successfully!"
            return json_response(start_response, {"success": True, "message": message})

        if method == "POST" and path == "/delete":
            data = read_json(environ)
            with connect_db() as con:
                cursor = con.execute("DELETE FROM students WHERE id=?", (int(data.get("id", 0)),))
            ok = cursor.rowcount > 0
            return json_response(start_response, {"success": ok, "message": "Record deleted." if ok else "Record not found."})

        return response(start_response, "Page not found.", "404 Not Found")
    except ValueError as error:
        return json_response(start_response, {"success": False, "message": str(error)}, "400 Bad Request")
    except Exception:
        import traceback
        traceback.print_exc()
        return json_response(start_response, {"success": False, "message": "Server error. Check the Vercel function logs."}, "500 Internal Server Error")


if __name__ == "__main__":
    # Local test runner; Vercel imports the WSGI app above.
    from wsgiref.simple_server import make_server
    create_table()
    print("Open http://127.0.0.1:8000")
    make_server("127.0.0.1", 8000, app).serve_forever()
