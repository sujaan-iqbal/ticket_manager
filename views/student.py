import streamlit as st
from core import service as S, config as C, db
from . import ui

PAGES = ["Dashboard", "My Requests", "Raise Request", "Notifications", "Profile"]
GROUPS = {"Open": ("NEW", "ACKNOWLEDGED", "ASSIGNED"), "In Progress": ("IN_PROGRESS",),
          "Waiting for Me": ("WAITING_FOR_STUDENT",), "Resolved": ("RESOLVED", "READY_FOR_COLLECTION", "CLOSED")}

def render(u):
    sb = st.sidebar; sb.title("🎓 Support Portal"); sb.caption(f"{u['name']} · {u['id']}")
    sb.radio("Menu", PAGES, key="page", on_change=ui.close_ticket)
    sb.button("Logout", on_click=ui.logout)
    rows = [t for t in S.all_rows() if t["student_id"] == u["id"]]
    if st.session_state.get("open_ticket"):
        t = S.get(st.session_state.open_ticket)
        if t and t["student_id"] == u["id"]: return ui.detail(t["tid"], "STUDENT", None, u["name"])   # students see only their own
        ui.close_ticket()
    p = st.session_state.page
    if p == "Dashboard": dashboard(rows)
    elif p == "My Requests":
        f = st.selectbox("Filter", ["All"] + list(GROUPS)); st.title("My Requests")
        ui.table([t for t in rows if f == "All" or t["status"] in GROUPS[f]], "sr", None, admin=False)
    elif p == "Raise Request": raise_request(u)
    elif p == "Notifications": st.title("Notifications"); ui.notifications(u["id"])
    else:
        st.title("Profile"); st.write(f"**Name:** {u['name']}  \n**Student ID:** {u['id']}  \n**Programme:** B.Tech (demo)  \n**Total requests:** {len(rows)}")

def dashboard(rows):
    st.title("My Dashboard")
    for c, (k, sts) in zip(st.columns(4), GROUPS.items()): c.metric(k, sum(t["status"] in sts for t in rows))
    for t in rows:
        if t["status"] == "WAITING_FOR_STUDENT":
            st.warning(f"**{t['tid']}** – Action required from you: {t['pending_action']}")
            st.button("Respond", key=f"w{t['tid']}", on_click=ui.open_ticket, args=(t["tid"],))
    st.subheader("My Requests"); ui.table(rows, "sd", None, admin=False)

def raise_request(u):
    st.title("Raise a Request")
    st.caption("Select the area and issue you need help with.")

    # ---------------------------------------------------------
    # Show success message after ticket creation
    # ---------------------------------------------------------
    if st.session_state.get("created"):
        t = S.get(st.session_state.created)

        st.success(
            f"**Request Submitted Successfully**  \n"
            f"Ticket ID: **{t['tid']}** · "
            f"Department: {t['department']} · "
            f"Priority: {t['priority']} · "
            f"Status: New · "
            f"SLA: {t['sla_hours']} hours"
        )

        st.info("Save this ticket ID for future reference.")

        st.button(
            "View ticket",
            on_click=ui.open_ticket,
            args=(t["tid"],)
        )

        st.divider()

    # Select main area
    
    st.subheader("1. What do you need help with?")

    categories = {
        "📚 Academic": [
            "Assignments",
            "Quizzes",
            "Attendance"
        ],
        "💰 Finance": [
            "Fees & Payments",
            "Fee Receipts"
        ],
        "🏛️ Administration": [
            "Admission",
            "Certificates",
            "Documents"
        ],
        "🪪 Student Services": [
            "ID Card",
            "Diary / Materials"
        ],
        "💻 Other": [
            "Other Administrative Issue"
        ]
    }

    area = st.radio(
        "Select an area",
        list(categories.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )

    # Select service
    
    st.subheader("2. Select a service")

    available_categories = categories[area]

    cat = st.radio(
        "Select a service",
        available_categories,
        horizontal=True,
        label_visibility="collapsed"
    )

    #  Select issue
    st.subheader("3. What is the issue?")

    request_types = C.CATALOG[cat][2]

    rt = st.radio(
        "Select the issue",
        request_types,
        label_visibility="collapsed"
    )

    # Routing information


    st.info(
        f"Your request will be automatically routed to "
        f"**{C.route(cat)}**. "
        f"Priority and SLA will be determined by the system."
    )

    #  Request details
    st.subheader("4. Request Details")

    subj = st.text_input(
        "Subject",
        placeholder="Briefly describe your issue"
    )

    extra = []

    # Academic-specific information
    if cat in ("Assignments", "Quizzes", "Attendance"):

        c1, c2 = st.columns(2)

        course = c1.text_input(
            "Related subject / course",
            placeholder="e.g. Machine Learning"
        )

        if cat == "Attendance":
            item = c2.text_input(
                "Class / session",
                placeholder="e.g. ML - 18 Sept"
            )
        else:
            item = c2.text_input(
                "Assignment / quiz name",
                placeholder="e.g. Assignment 2"
            )

        extra += [
            ("Course", course),
            ("Item", item)
        ]

    # Date-specific issues
    if cat in (
        "Attendance",
        "Fees & Payments",
        "Fee Receipts",
        "Quizzes",
        "Assignments"
    ):
        incident_date = st.date_input(
            "Date of incident (optional)",
            value=None
        )

        extra.append(
            ("Date of incident", incident_date)
        )

    desc = st.text_area(
        "Describe your issue",
        placeholder="Explain what happened and what help you need...",
        height=150
    )

    more = st.text_area(
        "Additional details (optional)",
        placeholder="Add any other information that may help us resolve your request..."
    )

    files = st.file_uploader(
        "Attachments (optional)",
        accept_multiple_files=True,
        help="Upload screenshots, receipts, documents, or other supporting proof."
    )
    # SUBMIT
    st.divider()

    if st.button(
        "Submit Request",
        type="primary",
        use_container_width=True
    ):

        if not desc.strip():
            st.error("Please describe your request.")
            return

        body = desc

        for key, value in extra:
            if value:
                body += f"\n\n{key}: {value}"

        if more.strip():
            body += f"\n\nAdditional details: {more}"

        st.session_state.created = S.create(
            u["id"],
            cat,
            rt,
            subj.strip() or rt,
            body,
            files
        )

        st.rerun()