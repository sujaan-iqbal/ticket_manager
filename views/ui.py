"""Shared UI helpers: badges, ticket table with per-row action button, ticket detail page."""
import streamlit as st
from datetime import datetime
from core import service as S, config as C

PC = {"CRITICAL": "red", "HIGH": "orange", "MEDIUM": "blue", "LOW": "gray"}
SC = {"Within SLA": "green", "Approaching SLA": "orange", "SLA Breached": "red", "SLA Paused": "violet", "Completed": "gray"}
ICON = {"Approaching SLA": "⚠ ", "SLA Breached": "🚨 ", "SLA Paused": "⏸ "}

def fmt(s): return datetime.fromisoformat(s).strftime("%d %b %Y, %I:%M %p")
def badge(t, c): return f":{c}[**{t}**]"
def age(t):
    h = t["age_h"]; return f"{int(h*60)}m" if h < 1 else (f"{h:.0f}h" if h < 48 else f"{h/24:.0f}d")
def status_md(t):
    return C.STATUS_LABEL[t["status"]] + (" 🔺" if t["escalated"] else "")
def sla_md(t): return badge(ICON.get(t["sla"], "") + S.sla_text(t), SC[t["sla"]])
def open_ticket(tid): st.session_state.open_ticket = tid
def close_ticket(): st.session_state.open_ticket = None
def logout():
    st.session_state.clear()

# ---------- ticket table (action button on the right of every row) ----------
ROW_ACTIONS = {"NEW": ("✓ Acknowledge", S.acknowledge), "ASSIGNED": ("▶ Start Work", S.start_work),
               "WAITING_FOR_STUDENT": ("↻ Resume", S.resume), "RESOLVED": ("Close", S.close), "READY_FOR_COLLECTION": ("Close", S.close)}
def table(rows, ns, actor, admin=True):
    if not rows: st.info("No tickets found."); return
    w = [1.0, 1.3, 2.4, 0.9, 1.4, 1.3, 0.6, 1.5, 1.2]
    hdr = ["Ticket", "Student" if admin else "Category", "Request", "Priority", "Status", "Assigned To" if admin else "Department", "Age", "SLA", "Action"]
    for c, h in zip(st.columns(w), hdr): c.markdown(f"**{h}**")
    for t in rows:
        c = st.columns(w, vertical_alignment="center"); tid = t["tid"]
        c[0].button(tid, key=f"{ns}o{tid}", on_click=open_ticket, args=(tid,), type="tertiary")
        c[1].write(t["student_name"] if admin else t["category"])
        c[2].markdown(f"{t['request_type']}  \n<small>{t['subject']}</small>", unsafe_allow_html=True)
        c[3].markdown(badge(t["priority"], PC[t["priority"]]))
        c[4].write(status_md(t))
        c[5].write((t["assigned_to"] or "Unassigned") if admin else t["department"])
        c[6].write(age(t)); c[7].markdown(sla_md(t))
        if admin and t["status"] in ROW_ACTIONS:
            lbl, fn = ROW_ACTIONS[t["status"]]
            c[8].button(lbl, key=f"{ns}a{tid}", on_click=fn, args=(tid, actor), help="Performs the next workflow step")
        else:
            c[8].button("Assign" if admin and t["status"] == "ACKNOWLEDGED" else ("Open" if not admin else "Actions ⋯"),
                        key=f"{ns}b{tid}", on_click=open_ticket, args=(tid,))

# ---------- ticket detail ----------
def detail(tid, role, actor, user_name=None):
    t = S.get(tid); t["sla"] = S.sla_state(t)
    st.button("← Back", on_click=close_ticket)
    st.subheader(f"{t['tid']} · {t['subject']}")
    st.caption(f"{t['category']} › {t['request_type']}  |  Student: {t['student_name']} ({t['student_id']})")
    a, b, c, d, e = st.columns(5)
    a.markdown("Priority  \n" + badge(t["priority"], PC[t["priority"]]))
    b.markdown("Status  \n**" + C.STATUS_LABEL[t["status"]] + "**")
    c.markdown(f"Department  \n**{t['department']}**")
    d.markdown(f"Assigned To  \n**{t['assigned_to'] or 'Unassigned'}**")
    e.markdown("SLA  \n" + sla_md(t))
    st.caption(f"Created {fmt(t['created_at'])} · SLA {t['sla_hours']}h · Due {fmt(t['sla_due_at'])}")
    if t["escalated"]: st.error(f"🔺 Escalated to: {t['escalated_to']}")
    if t["status"] == "WAITING_FOR_STUDENT":
        st.warning(f"**Action required from student:** {t['pending_action']}  \nSLA paused: waiting for student information.")
    if t["resolution"]: st.success(f"**Resolution:** {t['resolution']}")
    with st.expander("Description", expanded=True): st.write(t["description"])
    files = S.attachments(tid)
    if files:
        st.markdown("**Attachments**")
        for f in files:
            st.download_button(f"📎 {f['filename']} ({f['uploaded_by']})", f["data"], file_name=f["filename"], key=f"dl{f['id']}")
    (admin_panel if role == "ADMIN" else student_panel)(t, actor if role == "ADMIN" else user_name)
    st.markdown("### Activity timeline")
    for x in reversed(S.timeline(tid)):
        st.markdown(f"**{fmt(x['ts'])}** — {x['action']}  \n<small>by {x['actor']}{' · ' + x['detail'] if x['detail'] else ''}</small>", unsafe_allow_html=True)

def student_panel(t, name):
    tid = t["tid"]; st.divider()
    if t["status"] == "WAITING_FOR_STUDENT":
        st.markdown("#### Respond to the request")
        msg = st.text_area("Your response", key=f"rm{tid}"); up = st.file_uploader("Upload document", accept_multiple_files=True, key=f"ru{tid}")
        if st.button("Submit response", type="primary", key=f"rs{tid}"):
            if not msg.strip() and not up: st.error("Add a message or a file.")
            else: S.student_respond(tid, name, msg or "Uploaded requested document", up); st.rerun()
    elif t["status"] == "READY_FOR_COLLECTION":
        st.info(t["resolution"])
        if st.button("I have collected it (close ticket)", key=f"col{tid}"): S.close(tid, name); st.rerun()
    if t["status"] != "CLOSED":
        cm = st.text_input("Add a comment", key=f"sc{tid}")
        if st.button("Post comment", key=f"sp{tid}") and cm.strip(): S.comment(tid, name, cm); st.rerun()

def admin_panel(t, actor):
    tid, s = t["tid"], t["status"]; st.divider(); st.markdown(f"#### Actions (acting as **{actor}**)")
    def go(fn, *a):
        try: fn(*a); st.rerun()
        except ValueError as e: st.error(str(e))
    staff = C.staff_in(t["department"])
    if s == "NEW":
        if st.button("✓ Acknowledge", type="primary", key=f"k{tid}"): go(S.acknowledge, tid, actor)
    elif s == "ACKNOWLEDGED":
        p = st.selectbox("Assign to", staff, key=f"as{tid}")
        if st.button("Assign", type="primary", key=f"ab{tid}"): go(S.assign, tid, p, actor)
    elif s == "ASSIGNED":
        if st.button("▶ Start Work", type="primary", key=f"sw{tid}"): go(S.start_work, tid, actor)
    elif s == "IN_PROGRESS":
        c1, c2, c3 = st.columns(3)
        with c1.expander("Request information"):
            pa = st.text_input("Pending action for student", "Upload payment receipt", key=f"pa{tid}")
            if st.button("Request Info", key=f"ri{tid}"): go(S.request_info, tid, actor, pa)
        with c2.expander("Resolve"):
            rt = st.selectbox("Resolution type", ["Issue Resolved", "Request Approved", "Request Rejected", "Information Provided"], key=f"rt{tid}")
            rs = st.text_area("Resolution summary", key=f"rsm{tid}")
            if st.button("Mark Resolved", type="primary", key=f"rv{tid}"): go(S.resolve, tid, actor, rs, rt)
        with c3.expander("Ready for collection"):
            nt = st.text_input("Note", f"Ready for collection from the {t['department']} Office.", key=f"nt{tid}")
            if st.button("Mark Ready", key=f"mr{tid}"): go(S.mark_ready, tid, actor, nt)
    elif s == "WAITING_FOR_STUDENT":
        if st.button("↻ Resume work", key=f"rz{tid}"): go(S.resume, tid, actor)
    elif s in ("RESOLVED", "READY_FOR_COLLECTION"):
        if st.button("Close Ticket", type="primary", key=f"cl{tid}"): go(S.close, tid, actor)
    if s != "CLOSED":
        with st.expander("More: comment · priority · reassign · escalate"):
            cm = st.text_input("Comment (visible to student)", key=f"cm{tid}")
            if st.button("Add comment", key=f"cb{tid}") and cm.strip(): go(S.comment, tid, actor, cm)
            x1, x2, x3 = st.columns(3)
            pr = x1.selectbox("Priority", C.PRIORITIES, C.PRIORITIES.index(t["priority"]), key=f"pr{tid}")
            if x1.button("Set priority", key=f"pb{tid}"): go(S.set_priority, tid, actor, pr)
            dp = x2.selectbox("Department", C.DEPARTMENTS, C.DEPARTMENTS.index(t["department"]), key=f"dp{tid}")
            if x2.button("Move department", key=f"db{tid}"): go(S.set_department, tid, actor, dp)
            if s not in ("NEW", "ACKNOWLEDGED"):
                ns = x3.selectbox("Reassign to", C.staff_in(t["department"]) or ["-"], key=f"rsg{tid}")
                if x3.button("Reassign", key=f"rb{tid}"): go(S.assign, tid, ns, actor)
            if not t["escalated"]:
                er = st.text_input("Escalation reason", "Needs supervisor attention", key=f"er{tid}")
                if st.button("🔺 Escalate", key=f"eb{tid}"): go(S.escalate, tid, actor, er)

def notifications(aud):
    from core import db
    rows = db.q("SELECT * FROM notifications WHERE audience=? ORDER BY ts DESC, id DESC LIMIT 40", (aud,))
    if not rows: st.info("No notifications.")
    for n in rows:
        c1, c2 = st.columns([6, 1], vertical_alignment="center")
        c1.markdown(f"🔔 {n['message']}  \n<small>{fmt(n['ts'])}</small>", unsafe_allow_html=True)
        c2.button("Open", key=f"n{n['id']}", on_click=open_ticket, args=(n["tid"],))
