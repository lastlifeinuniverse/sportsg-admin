from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import get_db, init_db
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = "sportsg-secret-2026"

AGE_GROUPS = ["Children (6-12)", "Youth (13-17)", "Adults (18-49)", "Seniors (50+)"]
CATEGORIES = ["Children", "Youth", "Adults", "Seniors", "All Ages", "Persons with Disabilities"]
STATUSES = ["Active", "Completed", "On Hold", "Cancelled"]
FREQUENCIES = ["Weekly", "Twice Weekly", "Fortnightly", "Monthly", "Ad-hoc"]


@app.route("/")
def dashboard():
    db = get_db()

    active_programmes = db.execute(
        "SELECT COUNT(*) as cnt FROM programmes WHERE status = 'Active'"
    ).fetchone()["cnt"]

    total_coaches = db.execute("SELECT COUNT(*) as cnt FROM coaches").fetchone()["cnt"]

    month_start = date.today().replace(day=1).isoformat()
    sessions_this_month = db.execute(
        "SELECT COUNT(*) as cnt FROM sessions WHERE session_date >= ?", (month_start,)
    ).fetchone()["cnt"]

    beneficiaries_this_month = db.execute(
        """SELECT COALESCE(SUM(a.count), 0) as total
           FROM attendance a
           JOIN sessions s ON a.session_id = s.id
           WHERE s.session_date >= ?""",
        (month_start,),
    ).fetchone()["total"]

    recent_sessions = db.execute(
        """SELECT s.id, s.session_date, s.duration_hours, p.name as programme_name,
                  c.name as coach_name,
                  COALESCE(SUM(a.count), 0) as total_attendees
           FROM sessions s
           JOIN programmes p ON s.programme_id = p.id
           LEFT JOIN coaches c ON p.coach_id = c.id
           LEFT JOIN attendance a ON a.session_id = s.id
           GROUP BY s.id
           ORDER BY s.session_date DESC
           LIMIT 8"""
    ).fetchall()

    age_group_totals = db.execute(
        """SELECT a.age_group, SUM(a.count) as total
           FROM attendance a
           JOIN sessions s ON a.session_id = s.id
           WHERE s.session_date >= ?
           GROUP BY a.age_group
           ORDER BY a.age_group""",
        (month_start,),
    ).fetchall()

    programme_summary = db.execute(
        """SELECT p.name, p.status, p.category, c.name as coach_name,
                  COUNT(DISTINCT s.id) as session_count,
                  COALESCE(SUM(a.count), 0) as total_beneficiaries
           FROM programmes p
           LEFT JOIN coaches c ON p.coach_id = c.id
           LEFT JOIN sessions s ON s.programme_id = p.id
           LEFT JOIN attendance a ON a.session_id = s.id
           GROUP BY p.id
           ORDER BY p.status, p.name"""
    ).fetchall()

    db.close()
    return render_template(
        "dashboard.html",
        active_programmes=active_programmes,
        total_coaches=total_coaches,
        sessions_this_month=sessions_this_month,
        beneficiaries_this_month=beneficiaries_this_month,
        recent_sessions=recent_sessions,
        age_group_totals=age_group_totals,
        programme_summary=programme_summary,
    )


# ── Coaches ──────────────────────────────────────────────────────────────────

@app.route("/coaches")
def coaches():
    db = get_db()
    rows = db.execute(
        """SELECT c.*, COUNT(p.id) as programme_count
           FROM coaches c
           LEFT JOIN programmes p ON p.coach_id = c.id
           GROUP BY c.id ORDER BY c.name"""
    ).fetchall()
    db.close()
    return render_template("coaches.html", coaches=rows)


@app.route("/coaches/add", methods=["GET", "POST"])
def add_coach():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO coaches (name, email, phone, specialization) VALUES (?,?,?,?)",
            (request.form["name"], request.form["email"],
             request.form["phone"], request.form["specialization"]),
        )
        db.commit()
        db.close()
        flash("Coach added successfully.", "success")
        return redirect(url_for("coaches"))
    return render_template("coach_form.html", coach=None, title="Add Coach")


@app.route("/coaches/<int:coach_id>/edit", methods=["GET", "POST"])
def edit_coach(coach_id):
    db = get_db()
    coach = db.execute("SELECT * FROM coaches WHERE id=?", (coach_id,)).fetchone()
    if request.method == "POST":
        db.execute(
            "UPDATE coaches SET name=?, email=?, phone=?, specialization=? WHERE id=?",
            (request.form["name"], request.form["email"],
             request.form["phone"], request.form["specialization"], coach_id),
        )
        db.commit()
        db.close()
        flash("Coach updated.", "success")
        return redirect(url_for("coaches"))
    db.close()
    return render_template("coach_form.html", coach=coach, title="Edit Coach")


@app.route("/coaches/<int:coach_id>/delete", methods=["POST"])
def delete_coach(coach_id):
    db = get_db()
    db.execute("DELETE FROM coaches WHERE id=?", (coach_id,))
    db.commit()
    db.close()
    flash("Coach removed.", "info")
    return redirect(url_for("coaches"))


# ── Programmes ────────────────────────────────────────────────────────────────

@app.route("/programmes")
def programmes():
    db = get_db()
    rows = db.execute(
        """SELECT p.*, c.name as coach_name,
                  COUNT(DISTINCT s.id) as session_count,
                  COALESCE(SUM(a.count), 0) as total_beneficiaries
           FROM programmes p
           LEFT JOIN coaches c ON p.coach_id = c.id
           LEFT JOIN sessions s ON s.programme_id = p.id
           LEFT JOIN attendance a ON a.session_id = s.id
           GROUP BY p.id ORDER BY p.status, p.name"""
    ).fetchall()
    db.close()
    return render_template("programmes.html", programmes=rows, statuses=STATUSES)


@app.route("/programmes/add", methods=["GET", "POST"])
def add_programme():
    db = get_db()
    coaches = db.execute("SELECT * FROM coaches ORDER BY name").fetchall()
    if request.method == "POST":
        db.execute(
            """INSERT INTO programmes
               (name, description, coach_id, category, status, location, frequency, start_date, end_date)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                request.form["name"], request.form["description"],
                request.form["coach_id"] or None, request.form["category"],
                request.form["status"], request.form["location"],
                request.form["frequency"], request.form["start_date"] or None,
                request.form["end_date"] or None,
            ),
        )
        db.commit()
        db.close()
        flash("Programme added successfully.", "success")
        return redirect(url_for("programmes"))
    db.close()
    return render_template(
        "programme_form.html", programme=None, coaches=coaches,
        categories=CATEGORIES, statuses=STATUSES, frequencies=FREQUENCIES,
        title="Add Programme",
    )


@app.route("/programmes/<int:prog_id>/edit", methods=["GET", "POST"])
def edit_programme(prog_id):
    db = get_db()
    prog = db.execute("SELECT * FROM programmes WHERE id=?", (prog_id,)).fetchone()
    coaches = db.execute("SELECT * FROM coaches ORDER BY name").fetchall()
    if request.method == "POST":
        db.execute(
            """UPDATE programmes SET name=?, description=?, coach_id=?, category=?,
               status=?, location=?, frequency=?, start_date=?, end_date=? WHERE id=?""",
            (
                request.form["name"], request.form["description"],
                request.form["coach_id"] or None, request.form["category"],
                request.form["status"], request.form["location"],
                request.form["frequency"], request.form["start_date"] or None,
                request.form["end_date"] or None, prog_id,
            ),
        )
        db.commit()
        db.close()
        flash("Programme updated.", "success")
        return redirect(url_for("programmes"))
    db.close()
    return render_template(
        "programme_form.html", programme=prog, coaches=coaches,
        categories=CATEGORIES, statuses=STATUSES, frequencies=FREQUENCIES,
        title="Edit Programme",
    )


@app.route("/programmes/<int:prog_id>/delete", methods=["POST"])
def delete_programme(prog_id):
    db = get_db()
    db.execute("DELETE FROM programmes WHERE id=?", (prog_id,))
    db.commit()
    db.close()
    flash("Programme removed.", "info")
    return redirect(url_for("programmes"))


# ── Sessions ──────────────────────────────────────────────────────────────────

@app.route("/sessions")
def sessions():
    db = get_db()
    rows = db.execute(
        """SELECT s.id, s.session_date, s.duration_hours, s.notes,
                  p.name as programme_name, c.name as coach_name,
                  COALESCE(SUM(a.count), 0) as total_attendees
           FROM sessions s
           JOIN programmes p ON s.programme_id = p.id
           LEFT JOIN coaches c ON p.coach_id = c.id
           LEFT JOIN attendance a ON a.session_id = s.id
           GROUP BY s.id ORDER BY s.session_date DESC"""
    ).fetchall()
    db.close()
    return render_template("sessions.html", sessions=rows)


@app.route("/sessions/log", methods=["GET", "POST"])
def log_session():
    db = get_db()
    programmes = db.execute(
        "SELECT p.id, p.name, c.name as coach_name FROM programmes p LEFT JOIN coaches c ON p.coach_id = c.id WHERE p.status='Active' ORDER BY p.name"
    ).fetchall()

    if request.method == "POST":
        cur = db.cursor()
        cur.execute(
            "INSERT INTO sessions (programme_id, session_date, duration_hours, notes) VALUES (?,?,?,?)",
            (
                request.form["programme_id"],
                request.form["session_date"],
                request.form["duration_hours"] or 1.0,
                request.form["notes"],
            ),
        )
        session_id = cur.lastrowid
        for ag in AGE_GROUPS:
            count = int(request.form.get(f"count_{ag}", 0) or 0)
            db.execute(
                "INSERT INTO attendance (session_id, age_group, count) VALUES (?,?,?)",
                (session_id, ag, count),
            )
        db.commit()
        db.close()
        flash("Session logged successfully.", "success")
        return redirect(url_for("sessions"))

    db.close()
    return render_template(
        "session_form.html", programmes=programmes, age_groups=AGE_GROUPS,
        today=date.today().isoformat(),
    )


@app.route("/sessions/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    db = get_db()
    db.execute("DELETE FROM attendance WHERE session_id=?", (session_id,))
    db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    db.commit()
    db.close()
    flash("Session deleted.", "info")
    return redirect(url_for("sessions"))


# ── Reports ───────────────────────────────────────────────────────────────────

@app.route("/reports", methods=["GET"])
def reports():
    report_type = request.args.get("type", "weekly")
    today = date.today()

    if report_type == "weekly":
        start = today - timedelta(days=today.weekday())  # Monday
        end = start + timedelta(days=6)
        period_label = f"Week of {start.strftime('%d %b %Y')}"
    else:  # quarterly
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        if q < 3:
            end = date(today.year, q * 3 + 4, 1) - timedelta(days=1)
        else:
            end = date(today.year, 12, 31)
        quarter_names = ["Q1", "Q2", "Q3", "Q4"]
        period_label = f"{quarter_names[q]} {today.year} ({start.strftime('%d %b')} – {end.strftime('%d %b %Y')})"

    # Allow custom date override
    custom_start = request.args.get("start_date")
    custom_end = request.args.get("end_date")
    if custom_start and custom_end:
        start = date.fromisoformat(custom_start)
        end = date.fromisoformat(custom_end)
        period_label = f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"

    db = get_db()

    programme_breakdown = db.execute(
        """SELECT p.name as programme, c.name as coach, p.category,
                  COUNT(DISTINCT s.id) as sessions,
                  COALESCE(SUM(a.count), 0) as total,
                  COALESCE(SUM(CASE WHEN a.age_group='Children (6-12)' THEN a.count ELSE 0 END), 0) as children,
                  COALESCE(SUM(CASE WHEN a.age_group='Youth (13-17)' THEN a.count ELSE 0 END), 0) as youth,
                  COALESCE(SUM(CASE WHEN a.age_group='Adults (18-49)' THEN a.count ELSE 0 END), 0) as adults,
                  COALESCE(SUM(CASE WHEN a.age_group='Seniors (50+)' THEN a.count ELSE 0 END), 0) as seniors
           FROM programmes p
           LEFT JOIN coaches c ON p.coach_id = c.id
           LEFT JOIN sessions s ON s.programme_id = p.id AND s.session_date BETWEEN ? AND ?
           LEFT JOIN attendance a ON a.session_id = s.id
           GROUP BY p.id ORDER BY total DESC""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    age_group_totals = db.execute(
        """SELECT a.age_group, SUM(a.count) as total
           FROM attendance a
           JOIN sessions s ON a.session_id = s.id
           WHERE s.session_date BETWEEN ? AND ?
           GROUP BY a.age_group ORDER BY a.age_group""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    coach_summary = db.execute(
        """SELECT c.name as coach, COUNT(DISTINCT p.id) as programmes,
                  COUNT(DISTINCT s.id) as sessions,
                  COALESCE(SUM(a.count), 0) as beneficiaries
           FROM coaches c
           LEFT JOIN programmes p ON p.coach_id = c.id
           LEFT JOIN sessions s ON s.programme_id = p.id AND s.session_date BETWEEN ? AND ?
           LEFT JOIN attendance a ON a.session_id = s.id
           GROUP BY c.id ORDER BY beneficiaries DESC""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    totals = {
        "sessions": sum(r["sessions"] for r in programme_breakdown),
        "beneficiaries": sum(r["total"] for r in programme_breakdown),
        "children": sum(r["children"] for r in programme_breakdown),
        "youth": sum(r["youth"] for r in programme_breakdown),
        "adults": sum(r["adults"] for r in programme_breakdown),
        "seniors": sum(r["seniors"] for r in programme_breakdown),
    }

    db.close()
    return render_template(
        "reports.html",
        report_type=report_type,
        period_label=period_label,
        start=start.isoformat(),
        end=end.isoformat(),
        programme_breakdown=programme_breakdown,
        age_group_totals=age_group_totals,
        coach_summary=coach_summary,
        totals=totals,
        today=today.isoformat(),
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
