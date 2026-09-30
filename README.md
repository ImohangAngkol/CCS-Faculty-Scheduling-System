# CCS Faculty Scheduling System

A Genetic Algorithm–based faculty scheduling decision-support system for the College of Computer Studies (CCS), MSU-IIT.

The project combines a Python/FastAPI backend, a React + TypeScript dashboard, and a Genetic Algorithm for generating and evaluating faculty schedules using scheduling constraints, faculty preferences, workload rules, rooms, sections, and time slots.

> **Project status:** Active development / thesis prototype.

---

## Features

- Genetic Algorithm–based faculty schedule generation
- Saved best chromosome / baseline workflow
- Faculty preference management
- Subject preference ranking
- Drag-and-drop weekly preference calendar
- Faculty schedule viewing
- Room assignment support
- Chromosome analysis and fitness breakdown
- Faculty workload and preparation analysis
- FastAPI REST API with Swagger documentation
- React + TypeScript administrative dashboard
- PostgreSQL / SQLAlchemy / Alembic-ready backend structure

---

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- pandas
- NumPy
- Matplotlib
- SQLAlchemy
- Alembic
- PostgreSQL / psycopg2

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Axios
- FullCalendar
- React Router
- TanStack Query
- React Hook Form
- Zod
- Recharts

---

## Project Structure

```text
Genetic-Algorithm Dashboard/
│
├── backend/
│   ├── data/
│   ├── genetic_algorithm/
│   │   ├── analysis/
│   │   ├── models/
│   │   ├── operators/
│   │   └── utils/
│   ├── routers/
│   ├── saved_chromosomes/
│   ├── schemas/
│   ├── services/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── context/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── package-lock.json
│
├── notebooks/
├── docs/
├── screenshots/
├── .gitignore
└── README.md
```

---

## Requirements

Install these before starting:

- Git
- Python 3.12+ recommended
- Node.js 20+ recommended
- npm
- VS Code or another IDE
- PostgreSQL / pgAdmin if database features are being used

The current development machine may use a newer Python release, but collaborators should use a stable Python version supported by all required packages.

---

## Clone the Repository

```bash
git clone https://github.com/ImohangAngkol/CCS-Faculty-Scheduling-System.git
cd CCS-Faculty-Scheduling-System
```

---

# Backend Setup

## 1. Create a Python virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2. Upgrade pip

```powershell
python -m pip install --upgrade pip
```

## 3. Install backend dependencies

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
```

## 4. Start the backend

```powershell
cd backend
python -m uvicorn main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Frontend Setup

Open a second terminal.

```powershell
cd frontend
npm install
npm run dev
```

The Vite terminal will display the local frontend URL, normally:

```text
http://localhost:5173
```

Because `package-lock.json` is committed, collaborators can also use:

```powershell
npm ci
```

for a reproducible install.

---

## FullCalendar

The faculty preference calendar currently uses the matching FullCalendar 6.1.x package family.

The project should keep these packages on compatible versions:

```text
@fullcalendar/core
@fullcalendar/react
@fullcalendar/timegrid
@fullcalendar/interaction
```

Do not mix FullCalendar 7.x `core` with 6.x plugins.

---

# Running Both Applications

Use two terminals.

### Terminal 1 — Backend

```powershell
cd backend
python -m uvicorn main:app --reload
```

### Terminal 2 — Frontend

```powershell
cd frontend
npm run dev
```

---

# Important Data Files

The scheduling prototype currently reads data from files under:

```text
backend/data/
```

These include faculty, subject, room, faculty preference, workload, and semester schedule data.

Do not rename required CSV/JSON/XLSX files unless the corresponding Python loader is also updated.

---

# Genetic Algorithm Overview

The scheduling solution is represented as a chromosome containing subject/faculty/room/time assignments.

Major GA components are organized under:

```text
backend/genetic_algorithm/
```

Key areas:

```text
models/      data structures
operators/   fitness, population, mutation, elitism, saved best chromosome
utils/       schedule construction and supporting functions
analysis/    result interpretation and visual analysis
```

The system follows a **lower fitness penalty = better schedule** convention.

The current project evaluates criteria such as:

- Faculty scheduling preferences
- Subject preference ranking
- Preferred teaching times and days
- Schedule compactness / spacing
- Lecture-laboratory day preference
- Number of preparations
- Faculty workload
- Daily teaching load
- Scheduling feasibility

Hard scheduling rules and workload policies are still being refined with adviser guidance.

---

# Faculty Preference Interface

Faculty/admin users can:

- Browse available subjects
- Select preferred subjects
- Rank selected subjects
- Drag selected subject components into a weekly preference timetable
- Move and resize preferred timetable blocks in 30-minute increments
- Configure schedule style preference
- Configure lecture/laboratory day preference
- Set preference importance values

Calendar placements are soft preferences for the Genetic Algorithm and are not intended to override hard scheduling constraints.

---

# Saved Chromosome Workflow

Saved chromosomes are stored under:

```text
backend/saved_chromosomes/
```

The project supports loading and analyzing an existing chromosome without performing another optimization run.

The intended GA workflow is:

```text
Saved best chromosome
        ↓
Use as baseline
        ↓
Run Genetic Algorithm
        ↓
Compare new best against baseline
        ↓
Save only if the new chromosome is better
```

---

# Development Notes

Before pushing changes:

```powershell
git status
git diff
```

Stage only the files related to the current checkpoint:

```powershell
git add <files>
git commit -m "Describe the checkpoint"
git push
```

Do not commit:

- virtual environments
- `node_modules`
- frontend build output
- Python cache files
- IDE-local settings
- secrets or `.env`
- temporary test files

---

# Updating Dependencies

## Backend

After intentionally installing/removing a backend dependency, update:

```text
backend/requirements.txt
```

A quick snapshot of the active environment can be generated with:

```powershell
python -m pip freeze > backend/requirements-freeze.txt
```

Use `requirements.txt` as the curated direct-dependency list and the freeze file only when an exact environment snapshot is needed.

## Frontend

After installing/removing npm dependencies:

```powershell
npm install
```

Commit both:

```text
frontend/package.json
frontend/package-lock.json
```

Do not manually edit `package-lock.json`.

---

# Troubleshooting

### Backend import errors

Make sure the virtual environment is active and the backend is started from:

```text
backend/
```

using:

```powershell
python -m uvicorn main:app --reload
```

### Frontend dependency errors

From `frontend/`:

```powershell
npm install
```

If dependencies are already locked and a clean reproducible install is needed:

```powershell
npm ci
```

### FullCalendar type conflicts

All FullCalendar packages must use compatible versions. Check with:

```powershell
npm list @fullcalendar/core @fullcalendar/react @fullcalendar/timegrid @fullcalendar/interaction
```

---

# Current Development Priorities

- Finalize faculty workload rules with adviser confirmation
- Persist drag-and-drop calendar preferences in the backend
- Enforce the continuous 3-hour laboratory scheduling rule
- Integrate faculty specialization / expertise matching
- Audit hard constraints
- Verify best-chromosome reuse and replacement logic
- Connect persistent PostgreSQL storage
- Complete authentication / roles
- Conduct final thesis evaluation and testing

---

## Contributors

This repository is being developed as an undergraduate thesis project for the College of Computer Studies, MSU-IIT.

