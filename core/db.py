"""SQLite persistence (shared by student & admin sessions, so both see the same ticket state)."""
import os, sqlite3
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "support.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets(tid TEXT PRIMARY KEY, student_id TEXT, student_name TEXT, category TEXT,
 request_type TEXT, department TEXT, subject TEXT, description TEXT, priority TEXT, status TEXT, assigned_to TEXT,
 created_at TEXT, updated_at TEXT, sla_hours INT, sla_due_at TEXT, paused_at TEXT, escalated INT DEFAULT 0,
 escalated_to TEXT, resolution TEXT, pending_action TEXT, resolved_at TEXT, closed_at TEXT);
CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT, tid TEXT, actor TEXT, action TEXT, detail TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT, audience TEXT, tid TEXT, message TEXT, ts TEXT, is_read INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY AUTOINCREMENT, tid TEXT, filename TEXT, uploaded_by TEXT, ts TEXT, data BLOB);
"""
def _c():
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    c = sqlite3.connect(PATH); c.row_factory = sqlite3.Row; return c
def init():
    c = _c(); c.executescript(SCHEMA); c.commit(); c.close()
def q(sql, args=()):
    c = _c(); r = [dict(x) for x in c.execute(sql, args).fetchall()]; c.close(); return r
def one(sql, args=()):
    r = q(sql, args); return r[0] if r else None
def run(sql, args=()):
    c = _c(); c.execute(sql, args); c.commit(); c.close()
