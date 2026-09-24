"""Ticket engine: state machine, SLA, routing, audit log, notifications. All screens call this."""
import random
from datetime import datetime, timedelta
from . import db, config as C

_clock = None                       # overridden only by the seeder to backdate history
def now(): return _clock or datetime.now()
def iso(d): return d.isoformat(timespec="seconds")
def ts(s): return datetime.fromisoformat(s)

# ---------- helpers ----------
def log(tid, actor, action, detail=""):
    db.run("INSERT INTO activity(tid,actor,action,detail,ts) VALUES(?,?,?,?,?)", (tid, actor, action, detail, iso(now())))
def notify(aud, tid, msg):
    db.run("INSERT INTO notifications(audience,tid,message,ts) VALUES(?,?,?,?)", (aud, tid, msg, iso(now())))
def _once(aud, tid, msg):
    if not db.one("SELECT 1 x FROM notifications WHERE audience=? AND tid=? AND message=?", (aud, tid, msg)): notify(aud, tid, msg)
def get(tid): return db.one("SELECT * FROM tickets WHERE tid=?", (tid,))
def timeline(tid): return db.q("SELECT * FROM activity WHERE tid=? ORDER BY ts, id", (tid,))
def attachments(tid): return db.q("SELECT id,filename,uploaded_by,ts,data FROM attachments WHERE tid=? ORDER BY id", (tid,))
def _new_tid():
    while True:
        t = "SR-" + "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=4))
        if not get(t): return t
def _h(h): return f"{int(h*60)}m" if h < 1 else (f"{h:.0f}h" if h < 48 else f"{h/24:.0f}d")

def sla_state(t):
    if t["status"] in C.DONE: return "Completed"
    if t["paused_at"]: return "SLA Paused"
    rem = (ts(t["sla_due_at"]) - now()).total_seconds()
    if rem < 0: return "SLA Breached"
    if rem <= C.APPROACH_RATIO * t["sla_hours"] * 3600: return "Approaching SLA"
    return "Within SLA"
def sla_text(t):
    s = sla_state(t)
    if s == "SLA Paused": return "Paused: waiting for student"
    if s == "Completed": return "Completed"
    rem = (ts(t["sla_due_at"]) - now()).total_seconds() / 3600
    return f"Due in {_h(rem)}" if rem >= 0 else f"Overdue by {_h(-rem)}"
def age_hours(t): return (now() - ts(t["created_at"])).total_seconds() / 3600

def all_rows():
    rows = db.q("SELECT * FROM tickets ORDER BY created_at DESC")
    for t in rows: t["sla"] = sla_state(t); t["age_h"] = age_hours(t)
    return rows

# ---------- creation ----------
def create(student_id, category, rtype, subject, desc, files=None):
    tid, dept = _new_tid(), C.route(category)
    pr = C.default_priority(category, rtype); hrs = C.SLA_HOURS[pr]; n = now()
    db.run("""INSERT INTO tickets(tid,student_id,student_name,category,request_type,department,subject,description,priority,
              status,created_at,updated_at,sla_hours,sla_due_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
           (tid, student_id, C.STUDENTS[student_id], category, rtype, dept, subject, desc, pr, "NEW", iso(n), iso(n), hrs, iso(n + timedelta(hours=hrs))))
    log(tid, C.STUDENTS[student_id], "Request created", f"{category} › {rtype}")
    log(tid, "System", f"Request routed to {dept}", f"Priority {pr}, SLA {hrs} hours")
    if files: attach(tid, files, C.STUDENTS[student_id])
    notify("ADMIN", tid, f"New {dept} ticket {tid} ({pr}).")
    notify(student_id, tid, f"Your request {tid} was submitted and routed to {dept}.")
    return tid
def attach(tid, files, by):
    for f in files:
        db.run("INSERT INTO attachments(tid,filename,uploaded_by,ts,data) VALUES(?,?,?,?,?)", (tid, f.name, by, iso(now()), f.getvalue()))
        log(tid, by, "Attachment uploaded", f.name)

# ---------- state machine ----------
def move(tid, to, actor, action, detail="", student_msg=None, **upd):
    t = get(tid)
    if to not in C.TRANSITIONS[t["status"]]:
        raise ValueError(f"Invalid transition {t['status']} -> {to}")
    upd.update(status=to, updated_at=iso(now()))
    if to == "WAITING_FOR_STUDENT": upd["paused_at"] = iso(now())                       # SLA pauses
    if t["status"] == "WAITING_FOR_STUDENT" and t["paused_at"]:                        # SLA resumes
        upd["sla_due_at"] = iso(ts(t["sla_due_at"]) + (now() - ts(t["paused_at"]))); upd["paused_at"] = None
    db.run(f"UPDATE tickets SET {','.join(k + '=?' for k in upd)} WHERE tid=?", (*upd.values(), tid))
    log(tid, actor, action, detail or f"{C.STATUS_LABEL[t['status']]} → {C.STATUS_LABEL[to]}")
    if student_msg: notify(t["student_id"], tid, student_msg)

def acknowledge(tid, actor):
    d = get(tid)["department"]
    move(tid, "ACKNOWLEDGED", actor, f"Request acknowledged by {d}", student_msg=f"Your request {tid} has been acknowledged by the {d} department.")
def assign(tid, staff, actor):
    t = get(tid)
    if t["status"] == "ACKNOWLEDGED":
        move(tid, "ASSIGNED", actor, f"Ticket assigned to {staff}", assigned_to=staff, student_msg=f"{tid} has been assigned to {staff}.")
    elif t["status"] not in ("NEW", "CLOSED"):
        db.run("UPDATE tickets SET assigned_to=?, updated_at=? WHERE tid=?", (staff, iso(now()), tid))
        log(tid, actor, f"Ticket reassigned to {staff}", f"Previously {t['assigned_to'] or 'Unassigned'}")
    else: raise ValueError("Acknowledge the ticket before assigning.")
    notify("ADMIN", tid, f"{tid} assigned to {staff}.")
def start_work(tid, actor):
    move(tid, "IN_PROGRESS", actor, "Work started", student_msg=f"Work has started on {tid}.")
def request_info(tid, actor, pending):
    move(tid, "WAITING_FOR_STUDENT", actor, "Additional information requested", pending, pending_action=pending,
         student_msg=f"Additional information is required for {tid}: {pending}")
def resume(tid, actor):
    move(tid, "IN_PROGRESS", actor, "Work resumed", pending_action=None)
def student_respond(tid, student_name, message, files):
    if files: attach(tid, files, student_name)
    move(tid, "IN_PROGRESS", student_name, "Student responded", message, pending_action=None)
    notify("ADMIN", tid, f"{student_name} responded on {tid}; work resumed.")
def resolve(tid, actor, summary, rtype):
    if not summary.strip(): raise ValueError("A resolution summary is required.")
    move(tid, "RESOLVED", actor, "Ticket resolved", f"{rtype}: {summary}", resolution=f"{rtype}: {summary}",
         resolved_at=iso(now()), student_msg=f"Your ticket {tid} has been resolved.")
def mark_ready(tid, actor, note):
    t = get(tid); msg = note or f"Ready for collection from the {t['department']} Office."
    move(tid, "READY_FOR_COLLECTION", actor, "Ready for collection", msg, resolution=msg, resolved_at=iso(now()),
         student_msg=f"{tid}: your document is ready for collection from the {t['department']} Office.")
def close(tid, actor):
    if not (get(tid)["resolution"] or "").strip(): raise ValueError("Resolution must be recorded before closing.")
    move(tid, "CLOSED", actor, "Ticket closed", closed_at=iso(now()))

# ---------- non-transition actions ----------
def comment(tid, actor, text):
    log(tid, actor, "Comment added", text)
    t = get(tid)
    if actor != t["student_name"]: notify(t["student_id"], tid, f"New comment on {tid}.")
def escalate(tid, actor, reason, to="Department Supervisor"):
    t = get(tid)
    if t["status"] == "CLOSED" or t["escalated"]: return
    db.run("UPDATE tickets SET escalated=1, escalated_to=?, updated_at=? WHERE tid=?", (to, iso(now()), tid))
    log(tid, actor, "Ticket escalated", f"Reason: {reason}. Escalated to {to}")
    notify("ADMIN", tid, f"{tid} escalated to {to}: {reason}.")
def set_priority(tid, actor, new):
    t = get(tid)
    if new == t["priority"]: return
    due = ts(t["sla_due_at"]) + timedelta(hours=C.SLA_HOURS[new] - t["sla_hours"])
    db.run("UPDATE tickets SET priority=?, sla_hours=?, sla_due_at=?, updated_at=? WHERE tid=?", (new, C.SLA_HOURS[new], iso(due), iso(now()), tid))
    log(tid, actor, "Priority changed", f"{t['priority']} → {new}; SLA {C.SLA_HOURS[new]}h")
def set_department(tid, actor, dept):
    t = get(tid)
    if dept == t["department"]: return
    db.run("UPDATE tickets SET department=?, assigned_to=NULL, updated_at=? WHERE tid=?", (dept, iso(now()), tid))
    log(tid, actor, "Department reassigned", f"{t['department']} → {dept}")
def sweep():
    """SLA monitor: escalate breached tickets, warn on approaching ones."""
    for t in db.q("SELECT * FROM tickets WHERE status NOT IN ('RESOLVED','CLOSED','READY_FOR_COLLECTION') AND paused_at IS NULL"):
        s = sla_state(t)
        if s == "SLA Breached" and not t["escalated"]:
            escalate(t["tid"], "System", "SLA breached"); _once("ADMIN", t["tid"], f"{t['tid']} has breached SLA.")
        elif s == "Approaching SLA": _once("ADMIN", t["tid"], f"{t['tid']} is approaching SLA.")
