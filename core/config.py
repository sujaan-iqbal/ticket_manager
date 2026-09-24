"""Static configuration: departments, catalog, routing, priorities, SLA, state machine."""
SLA_HOURS = {"CRITICAL": 4, "HIGH": 12, "MEDIUM": 24, "LOW": 72}   # configurable
APPROACH_RATIO = 0.25          # "approaching" when <=25% of SLA time remains
PRIORITIES = list(SLA_HOURS)
DEPARTMENTS = ["Finance", "Academic", "Administration", "Student Services", "IT / ERP Support"]

STATUS_LABEL = {
    "NEW": "New", "ACKNOWLEDGED": "Acknowledged", "ASSIGNED": "Assigned",
    "IN_PROGRESS": "In Progress", "WAITING_FOR_STUDENT": "Waiting for Student",
    "READY_FOR_COLLECTION": "Ready for Collection", "RESOLVED": "Resolved", "CLOSED": "Closed"}
TRANSITIONS = {
    "NEW": ["ACKNOWLEDGED"], "ACKNOWLEDGED": ["ASSIGNED"], "ASSIGNED": ["IN_PROGRESS"],
    "IN_PROGRESS": ["WAITING_FOR_STUDENT", "RESOLVED", "READY_FOR_COLLECTION"],
    "WAITING_FOR_STUDENT": ["IN_PROGRESS"], "RESOLVED": ["CLOSED"],
    "READY_FOR_COLLECTION": ["CLOSED"], "CLOSED": []}
DONE = ("RESOLVED", "CLOSED", "READY_FOR_COLLECTION")   # SLA no longer running
COLLECTION_CATS = ("Certificates", "ID Card", "Diary / Materials", "Documents")

# category: (group, department, request types)  -> routing is category -> department
CATALOG = {
    "Assignments": ("Academic", "Academic", ["Submission issue", "Upload failed", "Submission not recorded", "Grade missing", "Grade incorrect", "Assignment access issue", "Other"]),
    "Quizzes": ("Academic", "Academic", ["Quiz not accessible", "Quiz submission issue", "Result missing", "Result discrepancy", "Other"]),
    "Attendance": ("Academic", "Academic", ["Attendance not updated", "Incorrect attendance", "Attendance shortage", "Attendance correction request", "Other"]),
    "Fees & Payments": ("Finance", "Finance", ["Payment status issue", "Payment failed", "Payment deducted but portal not updated", "Fee status incorrect", "Refund issue", "Other"]),
    "Fee Receipts": ("Finance", "Finance", ["Receipt not received", "Receipt request", "Incorrect receipt details"]),
    "Admission": ("Administration", "Administration", ["Admission document issue", "Admission status issue", "Personal information correction", "Other"]),
    "Certificates": ("Administration", "Administration", ["Bonafide certificate", "Study certificate", "Course certificate", "Character certificate", "Transfer certificate", "Other"]),
    "Documents": ("Administration", "Administration", ["Document verification", "Document copy request", "Other"]),
    "ID Card": ("Student Services", "Student Services", ["New ID card", "Lost/damaged ID", "Incorrect name", "Incorrect course/year", "Other"]),
    "Diary / Materials": ("Student Services", "Student Services", ["Not received", "Lost/damaged", "Replacement request", "Other"]),
    "Other Administrative Issue": ("Other", "IT / ERP Support", ["Portal / ERP access problem", "General information", "Other"]),
}
CRITICAL_TYPES = {"Quiz not accessible", "Payment failed", "Portal / ERP access problem"}
HIGH_TYPES = {"Payment status issue", "Payment deducted but portal not updated", "Fee status incorrect",
              "Submission issue", "Upload failed", "Submission not recorded", "Attendance shortage",
              "Attendance correction request", "Incorrect attendance", "Quiz submission issue", "Admission status issue"}
LOW_CATS = {"Diary / Materials", "Other Administrative Issue"}

def route(category): return CATALOG[category][1]
def default_priority(category, rtype):
    if rtype in CRITICAL_TYPES: return "CRITICAL"
    if rtype in HIGH_TYPES: return "HIGH"
    if category in LOW_CATS or rtype in ("General information", "Other"): return "LOW"
    return "MEDIUM"

STAFF = {"Priya Sharma": "Finance", "Rohit Verma": "Finance", "Dr. Anita Rao": "Academic",
         "Prof. Suresh Iyer": "Academic", "Meena Nair": "Administration", "Karan Mehta": "Administration",
         "Farhan Ali": "Student Services", "Deepa Menon": "Student Services", "Arjun Reddy": "IT / ERP Support"}
STUDENTS = {"STU1001": "Rahul Menon", "STU1002": "Ananya Iyer", "STU1003": "Sneha Kapoor", "STU1004": "Vikram Singh",
            "STU1005": "Ishita Rao", "STU1006": "Aditya Nair", "STU1007": "Kavya Reddy", "STU1008": "Rohan Das",
            "STU1009": "Meera Joshi", "STU1010": "Arjun Patel"}
def staff_in(dept): return [n for n, d in STAFF.items() if d == dept]
