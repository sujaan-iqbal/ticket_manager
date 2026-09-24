# Student Support & Ticket Management System

## Problem Statement

Students face issues related to fees, attendance, assignments, certificates, ID cards, admissions, and ERP/portal access.

The system provides a centralized platform to raise, manage, track, and resolve these requests.

## System Design

```text
                         ┌──────────────┐
                         │   Students   │
                         └──────┬───────┘
                                │
                         Raise / Track
                                │
                                ▼
                    ┌─────────────────────┐
                    │   Streamlit Portal  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Authentication &     │
                    │ Role Management      │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌────────────────┐          ┌────────────────┐
        │ Student Portal │          │  Admin Portal  │
        └───────┬────────┘          └───────┬────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    ┌──────────────────┐
                    │ Ticket Management│
                    └────────┬─────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │ Priority │    │   SLA    │    │Department│
       │ Assignment│   │ Tracking │    │  Routing │
       └────┬─────┘    └────┬─────┘    └────┬─────┘
            └───────────────┼───────────────┘
                            ▼
                   ┌─────────────────┐
                   │ SQLite Database │
                   └────────┬────────┘
                            │
                            ▼
                 Activity & Notifications
```

## Ticket Workflow

```text
NEW
 │
 ▼
ACKNOWLEDGED
 │
 ▼
ASSIGNED
 │
 ▼
IN_PROGRESS
 │
 ├───────────────► RESOLVED ─────► CLOSED
 │
 ▼
WAITING_FOR_STUDENT
 │
 ▼
IN_PROGRESS
 │
 └───────────────► RESOLVED ─────► CLOSED
```

## How to Run

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd student-support
```

### 2. Create a Virtual Environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python -m streamlit run app.py
```

The application will be available at:

```text
http://localhost:8501
```

## Demo Login

**Admin**

```text
Username: admin
Password: admin123
```

Student accounts are available in the application.

## Live Demo

[Streamlit Application](YOUR_STREAMLIT_DEPLOYED_URL)
