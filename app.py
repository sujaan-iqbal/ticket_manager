import streamlit as st
st.set_page_config(page_title="Student Support Portal", page_icon="🎓", layout="wide")
from core import seed
from views import auth, student, admin

@st.cache_resource
def _boot(): seed.ensure(); return True
_boot()

if "user" not in st.session_state:
    auth.login(); st.stop()
u = st.session_state.user
st.session_state.setdefault("page", "Dashboard")
if st.session_state.page not in (student.PAGES if u["role"] == "STUDENT" else admin.PAGES): st.session_state.page = "Dashboard"
(student if u["role"] == "STUDENT" else admin).render(u)
