import streamlit as st
from core import config as C

def login():
    st.title("🎓 Student Support Portal")
    st.caption("Raise, track and resolve student requests. Demo prototype.")
    t1, t2 = st.tabs(["Student Login", "Admin / Staff Login"])
    with t1:
        sid = st.selectbox("Student ID", list(C.STUDENTS), format_func=lambda s: f"{s} · {C.STUDENTS[s]}")
        if st.button("Login as student", type="primary"):
            st.session_state.user = {"role": "STUDENT", "id": sid, "name": C.STUDENTS[sid]}; st.rerun()
    with t2:
        u = st.text_input("Username", "admin"); p = st.text_input("Password", "admin123", type="password")
        if st.button("Login as admin", type="primary"):
            if (u, p) == ("admin", "admin123"): st.session_state.user = {"role": "ADMIN", "id": "ADMIN", "name": "Admin"}; st.rerun()
            else: st.error("Demo credentials: admin / admin123")
