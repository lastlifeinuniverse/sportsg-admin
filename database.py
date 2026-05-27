import sqlite3
import os
from datetime import datetime

# Absolute path so it works regardless of where gunicorn is invoked from
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_sg.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            specialization TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS programmes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            coach_id INTEGER REFERENCES coaches(id),
            category TEXT,
            status TEXT DEFAULT 'Active',
            location TEXT,
            frequency TEXT,
            start_date DATE,
            end_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            programme_id INTEGER REFERENCES programmes(id),
            session_date DATE NOT NULL,
            duration_hours REAL DEFAULT 1.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER REFERENCES sessions(id),
            age_group TEXT NOT NULL,
            count INTEGER DEFAULT 0
        );
    """)

    # Seed sample data if empty
    if c.execute("SELECT COUNT(*) FROM coaches").fetchone()[0] == 0:
        c.executescript("""
            INSERT INTO coaches (name, email, phone, specialization) VALUES
                ('Ahmad Fauzi', 'ahmad@sportsg.gov.sg', '91234567', 'Athletics'),
                ('Priya Nair', 'priya@sportsg.gov.sg', '92345678', 'Swimming'),
                ('Jason Tan', 'jason@sportsg.gov.sg', '93456789', 'Basketball'),
                ('Lily Soh', 'lily@sportsg.gov.sg', '94567890', 'Yoga & Wellness');

            INSERT INTO programmes (name, description, coach_id, category, status, location, frequency, start_date, end_date) VALUES
                ('Active Seniors Fitness', 'Low-impact exercise programme for seniors', 4, 'Seniors', 'Active', 'Bishan CC', 'Weekly', '2026-01-06', '2026-06-27'),
                ('Youth Basketball Academy', 'Skills development for youth players', 3, 'Youth', 'Active', 'Kallang Basketball Court', 'Twice Weekly', '2026-01-05', '2026-06-26'),
                ('Community Swim Lessons', 'Learn-to-swim for all ages', 2, 'All Ages', 'Active', 'OCBC Aquatic Centre', 'Weekly', '2026-02-03', '2026-07-31'),
                ('Kids Athletics Club', 'Track and field fundamentals for children', 1, 'Children', 'Active', 'Queenstown Stadium', 'Weekly', '2026-01-10', '2026-06-27'),
                ('Silver Yoga', 'Gentle yoga for seniors and adults', 4, 'Seniors', 'Active', 'Tampines Hub', 'Weekly', '2026-03-01', '2026-08-31');

            INSERT INTO sessions (programme_id, session_date, duration_hours, notes) VALUES
                (1, '2026-05-20', 1.5, 'Good turnout, new participants joined'),
                (1, '2026-05-13', 1.5, 'Regular session'),
                (2, '2026-05-21', 2.0, 'Focused on dribbling drills'),
                (2, '2026-05-19', 2.0, 'Scrimmage game'),
                (3, '2026-05-22', 1.0, 'Beginner group started'),
                (4, '2026-05-17', 1.5, 'Sprint training'),
                (5, '2026-05-23', 1.0, 'Balance and flexibility focus'),
                (1, '2026-05-06', 1.5, 'Public holiday make-up session'),
                (2, '2026-05-14', 2.0, 'Shooting practice'),
                (3, '2026-05-15', 1.0, 'Intermediate group');

            INSERT INTO attendance (session_id, age_group, count) VALUES
                (1, 'Children (6-12)', 0), (1, 'Youth (13-17)', 2), (1, 'Adults (18-49)', 5), (1, 'Seniors (50+)', 18),
                (2, 'Children (6-12)', 0), (2, 'Youth (13-17)', 1), (2, 'Adults (18-49)', 4), (2, 'Seniors (50+)', 15),
                (3, 'Children (6-12)', 3), (3, 'Youth (13-17)', 22), (3, 'Adults (18-49)', 8), (3, 'Seniors (50+)', 0),
                (4, 'Children (6-12)', 2), (4, 'Youth (13-17)', 20), (4, 'Adults (18-49)', 6), (4, 'Seniors (50+)', 0),
                (5, 'Children (6-12)', 4), (5, 'Youth (13-17)', 8), (5, 'Adults (18-49)', 14), (5, 'Seniors (50+)', 6),
                (6, 'Children (6-12)', 18), (6, 'Youth (13-17)', 4), (6, 'Adults (18-49)', 0), (6, 'Seniors (50+)', 0),
                (7, 'Children (6-12)', 0), (7, 'Youth (13-17)', 3), (7, 'Adults (18-49)', 9), (7, 'Seniors (50+)', 14),
                (8, 'Children (6-12)', 0), (8, 'Youth (13-17)', 0), (8, 'Adults (18-49)', 6), (8, 'Seniors (50+)', 17),
                (9, 'Children (6-12)', 1), (9, 'Youth (13-17)', 19), (9, 'Adults (18-49)', 7), (9, 'Seniors (50+)', 0),
                (10, 'Children (6-12)', 2), (10, 'Youth (13-17)', 6), (10, 'Adults (18-49)', 11), (10, 'Seniors (50+)', 3);
        """)

    conn.commit()
    conn.close()
