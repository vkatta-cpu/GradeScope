
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
import csv
import io
from pathlib import Path

app = Flask(__name__)
app.secret_key = "gradescope-secret-key"

DB_PATH = Path(__file__).with_name("students.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL,
                subject TEXT NOT NULL,
                marks REAL NOT NULL CHECK(marks >= 0 AND marks <= 100)
            )
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        if count == 0:
            demo = [
                ("Aarav Sharma", "CS101", "CSE", 3, "Python", 88),
                ("Diya Patel", "CS102", "CSE", 3, "Python", 94),
                ("Rohan Kumar", "EC201", "ECE", 3, "Python", 67),
                ("Meera Nair", "CS103", "CSE", 3, "DBMS", 79),
                ("Arjun Rao", "IT301", "IT", 5, "DBMS", 56),
                ("Sara Khan", "CS104", "CSE", 3, "DBMS", 91),
                ("Kabir Das", "EC202", "ECE", 3, "Networks", 72),
                ("Ananya Iyer", "IT302", "IT", 5, "Networks", 84),
                ("Ishaan Verma", "CS105", "CSE", 3, "Networks", 43),
                ("Tara Reddy", "EC203", "ECE", 3, "Mathematics", 96),
                ("Vivaan Joshi", "IT303", "IT", 5, "Mathematics", 61),
                ("Aditi Menon", "CS106", "CSE", 3, "Mathematics", 75)
            ]

            conn.executemany("""
                INSERT INTO students
                (name, roll_no, department, semester, subject, marks)
                VALUES (?, ?, ?, ?, ?, ?)
            """, demo)


@app.route("/")
def index():

    with get_db() as conn:

        students = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        avg = conn.execute(
            "SELECT ROUND(AVG(marks), 1) FROM students"
        ).fetchone()[0] or 0

        passed = conn.execute(
            "SELECT COUNT(*) FROM students WHERE marks >= 40"
        ).fetchone()[0]

        pass_rate = round(passed / total * 100, 1) if total else 0

        at_risk = conn.execute(
            "SELECT COUNT(*) FROM students WHERE marks < 40"
        ).fetchone()[0]

        subject_rows = conn.execute("""
            SELECT subject, ROUND(AVG(marks), 1) AS average
            FROM students
            GROUP BY subject
        """).fetchall()

        dept_rows = conn.execute("""
            SELECT department, ROUND(AVG(marks), 1) AS average
            FROM students
            GROUP BY department
        """).fetchall()

        distribution = conn.execute("""
            SELECT
                CASE
                    WHEN marks < 40 THEN 'Below 40'
                    WHEN marks < 60 THEN '40-59'
                    WHEN marks < 80 THEN '60-79'
                    ELSE '80-100'
                END AS band,
                COUNT(*) AS total
            FROM students
            GROUP BY band
        """).fetchall()

        top = conn.execute("""
            SELECT name, roll_no, subject, marks
            FROM students
            ORDER BY marks DESC
            LIMIT 5
        """).fetchall()

        # Convert SQLite Row objects into dictionaries
        # so they can be converted into JSON by Flask.
        subject_rows = [dict(row) for row in subject_rows]
        dept_rows = [dict(row) for row in dept_rows]
        distribution = [dict(row) for row in distribution]

    return render_template(
        "index.html",
        students=students,
        total=total,
        avg=avg,
        pass_rate=pass_rate,
        at_risk=at_risk,
        subject_rows=subject_rows,
        dept_rows=dept_rows,
        distribution=distribution,
        top=top
    )


@app.route("/add", methods=["POST"])
def add_student():

    try:
        name = request.form["name"].strip()
        roll = request.form["roll_no"].strip()
        dept = request.form["department"].strip().upper()
        semester = int(request.form["semester"])
        subject = request.form["subject"].strip()
        marks = float(request.form["marks"])

        if not all([name, roll, dept, subject]):
            raise ValueError()

        if not 1 <= semester <= 12:
            raise ValueError()

        if not 0 <= marks <= 100:
            raise ValueError()

        with get_db() as conn:
            conn.execute("""
                INSERT INTO students
                (name, roll_no, department, semester, subject, marks)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, roll, dept, semester, subject, marks))

        flash("Student added successfully!", "success")

    except sqlite3.IntegrityError:
        flash("Roll number already exists.", "error")

    except (ValueError, KeyError):
        flash("Please enter valid details.", "error")

    return redirect(url_for("index"))


@app.route("/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):

    with get_db() as conn:
        conn.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,)
        )

    flash("Student record deleted.", "success")
    return redirect(url_for("index"))


@app.route("/export")
def export_csv():

    with get_db() as conn:
        rows = conn.execute("""
            SELECT name, roll_no, department, semester,
                   subject, marks
            FROM students
            ORDER BY name
        """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Name", "Roll Number", "Department",
        "Semester", "Subject", "Marks"
    ])

    writer.writerows([tuple(row) for row in rows])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=student_performance.csv"
        }
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
