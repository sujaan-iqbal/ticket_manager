"""Seeds 40 realistic tickets (first 12 are NEW / ACKNOWLEDGED, i.e. pending) with backdated history."""
import random
from datetime import timedelta
from . import db, service as S, config as C

T = [("Fees & Payments", "Payment status issue", "Fee paid but ₹25,000 still outstanding", "I paid my full ₹25,000 fee, but the portal still shows ₹25,000 outstanding."),
     ("Fees & Payments", "Payment deducted but portal not updated", "Amount deducted, status pending", "₹12,500 was deducted from my bank on the 20th but the portal shows unpaid."),
     ("Fee Receipts", "Receipt request", "Need fee receipt for scholarship", "Please issue the semester 3 fee receipt for my scholarship application."),
     ("Assignments", "Submission not recorded", "ML Assignment 2 shows Not Submitted", "I submitted Assignment 2 yesterday but the portal shows 'Not Submitted'."),
     ("Assignments", "Grade missing", "Grade missing for DBMS Assignment 1", "My DBMS Assignment 1 grade has not been published."),
     ("Quizzes", "Quiz not accessible", "Cannot open Unit 3 quiz", "The quiz link shows access denied although it is open for my class."),
     ("Quizzes", "Result discrepancy", "Quiz score differs from answer key", "My Quiz 2 score does not match the answer key shared in class."),
     ("Attendance", "Incorrect attendance", "Marked absent on 18 September", "I attended on 18 September but was marked absent. Proof attached."),
     ("Attendance", "Attendance shortage", "Shortage affecting exam eligibility", "My attendance shows 71% due to medical leave; requesting review."),
     ("Certificates", "Bonafide certificate", "Bonafide certificate for bank loan", "Need a bonafide certificate for an education loan application."),
     ("Certificates", "Transfer certificate", "Transfer certificate request", "Requesting a transfer certificate for a change of institution."),
     ("ID Card", "Incorrect name", "Surname misspelt on ID card", "My surname is incorrect on my ID card. Identity proof attached."),
     ("ID Card", "Lost/damaged ID", "Lost ID card", "I lost my ID card and need a replacement."),
     ("Admission", "Personal information correction", "Date of birth wrong in records", "My date of birth is recorded incorrectly in the admission records."),
     ("Diary / Materials", "Not received", "Student diary not received", "I have not received the student diary issued to my batch."),
     ("Other Administrative Issue", "Portal / ERP access problem", "Unable to log into ERP", "My ERP login fails with 'account locked'.")]
PATHS = {"NEW": [], "ACKNOWLEDGED": ["ack"], "ASSIGNED": ["ack", "as"], "IN_PROGRESS": ["ack", "as", "st"],
         "WAITING_FOR_STUDENT": ["ack", "as", "st", "info"], "RESOLVED": ["ack", "as", "st", "res"],
         "READY_FOR_COLLECTION": ["ack", "as", "st", "rdy"], "CLOSED": ["ack", "as", "st", "res", "cl"]}
TARGETS = (["NEW"] * 6 + ["ACKNOWLEDGED"] * 6 + ["ASSIGNED"] * 3 + ["IN_PROGRESS"] * 7 + ["WAITING_FOR_STUDENT"] * 4
           + ["RESOLVED"] * 4 + ["READY_FOR_COLLECTION"] * 2 + ["CLOSED"] * 8)

def ensure():
    db.init()
    if not db.one("SELECT 1 x FROM tickets"): seed()

def seed():
    rnd = random.Random(7); base = S.datetime.now()
    for tgt in TARGETS:
        pool = [x for x in T if tgt != "READY_FOR_COLLECTION" or x[0] in ("Certificates", "ID Card")]
        cat, rt, subj, desc = rnd.choice(pool)
        age = rnd.choice([1, 3, 6, 10, 15, 26, 40, 60]) if tgt in ("NEW", "ACKNOWLEDGED") else rnd.choice([5, 9, 14, 20, 30, 50, 80, 120])
        S._clock = base - timedelta(hours=age)
        tid = S.create(rnd.choice(list(C.STUDENTS)), cat, rt, subj, desc)
        dept = C.route(cat); staff = rnd.choice(C.staff_in(dept)); path = PATHS[tgt]
        for i, step in enumerate(path, 1):
            S._clock = base - timedelta(hours=age) + timedelta(hours=age * 0.8 * i / len(path))
            {"ack": lambda: S.acknowledge(tid, staff), "as": lambda: S.assign(tid, staff, "Admin"),
             "st": lambda: S.start_work(tid, staff),
             "info": lambda: S.request_info(tid, staff, "Please upload supporting proof / receipt"),
             "res": lambda: S.resolve(tid, staff, "Verified and corrected in the system.", "Issue Resolved"),
             "rdy": lambda: S.mark_ready(tid, staff, f"Ready for collection from the {dept} Office."),
             "cl": lambda: S.close(tid, staff)}[step]()
    S._clock = None
    S.sweep()
