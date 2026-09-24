import pandas as pd, streamlit as st
from core import service as S, config as C
from . import ui

PAGES = ["Dashboard", "All Tickets", "Departments", "My Queue", "Escalations", "SLA Monitoring", "Reports", "Notifications"]
ACTIVE = lambda t: t["status"] not in C.DONE
def go_dept(d): st.session_state.page = "Departments"; st.session_state.dept = d; ui.close_ticket()

def render(u):
    S.sweep()
    sb = st.sidebar; sb.title("🎓 Support Portal"); sb.caption("Admin / Staff console")
    sb.selectbox("Acting as", ["Admin"] + list(C.STAFF), key="actor")
    sb.radio("Menu", PAGES, key="page", on_change=ui.close_ticket)
    sb.button("Logout", on_click=ui.logout)
    actor = st.session_state.actor; rows = S.all_rows()
    if st.session_state.get("open_ticket"): return ui.detail(st.session_state.open_ticket, "ADMIN", actor)
    p = st.session_state.page
    if p == "Dashboard": dashboard(rows)
    elif p == "All Tickets": st.title("All Tickets"); ui.table(filtered(rows), "al", actor)
    elif p == "Departments": departments(rows, actor)
    elif p == "My Queue": my_queue(rows, actor)
    elif p == "Escalations":
        st.title("Escalations"); ui.table([t for t in rows if t["escalated"] and t["status"] != "CLOSED"], "es", actor)
    elif p == "SLA Monitoring": sla_page(rows, actor)
    elif p == "Reports": reports(rows)
    else: st.title("Notifications"); ui.notifications("ADMIN")

def dashboard(rows):
    st.title("Operations Dashboard")
    act = [t for t in rows if ACTIVE(t)]; cnt = lambda f: sum(1 for t in rows if f(t))
    k = [("Total Tickets", len(rows)), ("Open", len(act)), ("Unassigned", cnt(lambda t: ACTIVE(t) and not t["assigned_to"])),
         ("In Progress", cnt(lambda t: t["status"] == "IN_PROGRESS")), ("Waiting for Student", cnt(lambda t: t["status"] == "WAITING_FOR_STUDENT")),
         ("SLA Approaching", cnt(lambda t: t["sla"] == "Approaching SLA")), ("SLA Breached", cnt(lambda t: t["sla"] == "SLA Breached")),
         ("Escalated", cnt(lambda t: t["escalated"] and t["status"] != "CLOSED")), ("Resolved", cnt(lambda t: t["status"] in C.DONE))]
    for r in (k[:5], k[5:]):
        for c, (l, v) in zip(st.columns(5), r): c.metric(l, v)
    st.subheader("Departments (click to open queue)")
    for c, d in zip(st.columns(5), C.DEPARTMENTS):
        c.button(f"{d}\n\n{sum(t['department'] == d for t in rows)} tickets · {sum(t['department'] == d and ACTIVE(t) for t in rows)} open",
                 key=f"d{d}", on_click=go_dept, args=(d,), use_container_width=True)
    st.subheader("Needs attention"); ui.table([t for t in act if t["status"] in ("NEW", "ACKNOWLEDGED") or t["sla"] == "SLA Breached"][:10], "dh", st.session_state.actor)

def departments(rows, actor):
    d = st.session_state.setdefault("dept", C.DEPARTMENTS[0])
    d = st.radio("Department", C.DEPARTMENTS, index=C.DEPARTMENTS.index(d), horizontal=True); st.session_state.dept = d
    st.title(f"{d} Support Queue"); ui.table(filtered([t for t in rows if t["department"] == d], "dq"), "dq", actor)

def my_queue(rows, actor):
    st.title("My Queue")
    if actor == "Admin": st.info("Select a staff member under 'Acting as' to see their queue. Showing unassigned tickets."); mine = [t for t in rows if ACTIVE(t) and not t["assigned_to"]]
    else:
        dept = C.STAFF[actor]; mine = [t for t in rows if ACTIVE(t) and (t["assigned_to"] == actor or (t["department"] == dept and not t["assigned_to"]))]
        st.caption(f"{actor} · {dept}: tickets assigned to you or unassigned in your department")
    ui.table(mine, "mq", actor)

def sla_page(rows, actor):
    st.title("SLA Monitoring")
    for title, s in (("🚨 Breached", "SLA Breached"), ("⚠ Approaching", "Approaching SLA"), ("⏸ Paused (waiting for student)", "SLA Paused")):
        sub = [t for t in rows if t["sla"] == s and t["status"] != "CLOSED"]; st.subheader(f"{title} ({len(sub)})"); ui.table(sub, "sl" + s[:3], actor)

def filtered(rows, ns="f"):
    c = st.columns(4)
    q = c[0].text_input("Search (ID, student, subject)", key=ns + "q").lower()
    dept = c[1].selectbox("Department", ["All"] + C.DEPARTMENTS, key=ns + "d")
    cat = c[2].selectbox("Category", ["All"] + list(C.CATALOG), key=ns + "c")
    rts = sorted({t["request_type"] for t in rows}); rt = c[3].selectbox("Request type", ["All"] + rts, key=ns + "r")
    c = st.columns(5)
    stt = c[0].selectbox("Status", ["All"] + list(C.STATUS_LABEL), format_func=lambda s: C.STATUS_LABEL.get(s, s), key=ns + "s")
    pr = c[1].selectbox("Priority", ["All"] + C.PRIORITIES, key=ns + "p")
    asg = c[2].selectbox("Assigned", ["All", "Unassigned"] + list(C.STAFF), key=ns + "a")
    sla = c[3].selectbox("SLA", ["All", "Within SLA", "Approaching SLA", "SLA Breached", "SLA Paused"], key=ns + "l")
    dt = c[4].date_input("Created on/after", value=None, key=ns + "dt"); esc = st.checkbox("Escalated only", key=ns + "e")
    out = []
    for t in rows:
        if q and q not in f"{t['tid']} {t['student_id']} {t['student_name']} {t['subject']}".lower(): continue
        if dept != "All" and t["department"] != dept: continue
        if cat != "All" and t["category"] != cat: continue
        if rt != "All" and t["request_type"] != rt: continue
        if stt != "All" and t["status"] != stt: continue
        if pr != "All" and t["priority"] != pr: continue
        if asg != "All" and (t["assigned_to"] or "Unassigned") != asg: continue
        if sla != "All" and t["sla"] != sla: continue
        if dt and t["created_at"][:10] < dt.isoformat(): continue
        if esc and not t["escalated"]: continue
        out.append(t)
    st.caption(f"{len(out)} ticket(s)"); return out

def reports(rows):
    st.title("Reports")
    df = pd.DataFrame(rows); a, b = st.columns(2)
    a.subheader("By department"); a.bar_chart(df["department"].value_counts())
    b.subheader("By category"); b.bar_chart(df["category"].value_counts())
    act = df[df["status"].isin([s for s in C.STATUS_LABEL if s not in C.DONE])]
    bins = pd.cut(act["age_h"], [-1, 24, 72, 168, 1e9], labels=["< 1 day", "1–3 days", "3–7 days", "7+ days"])
    c, d = st.columns(2)
    c.subheader("Ticket aging (open)"); c.bar_chart(bins.value_counts().reindex(["< 1 day", "1–3 days", "3–7 days", "7+ days"]).fillna(0))
    d.subheader("SLA performance"); d.bar_chart(df[df["sla"] != "Completed"]["sla"].value_counts())
    st.subheader("Priority distribution"); st.bar_chart(df["priority"].value_counts().reindex(C.PRIORITIES).fillna(0))
