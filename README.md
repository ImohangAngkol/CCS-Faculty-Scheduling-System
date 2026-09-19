# CCS Faculty Scheduling System

A Genetic Algorithm-based Faculty Scheduling Decision-Support System for the
College of Computer Studies.

The system generates conflict-free faculty schedules while considering
faculty preferences, teaching loads, subject assignments, available rooms,
sections, and schedule constraints.

## Project Status

Current development status:

- [x] Genetic Algorithm core
- [x] Initial population generation
- [x] Fitness evaluation
- [x] Elitism selection
- [x] Faculty-swap crossover
- [x] Mutation
- [x] Best-ever chromosome preservation
- [x] Faculty preference fitness breakdown
- [x] Conflict validation
- [x] FastAPI backend
- [x] Automated backend tests
- [ ] React dashboard
- [ ] Faculty preference interface
- [ ] Admin dashboard
- [ ] PostgreSQL integration
- [ ] Authentication and role management
- [ ] Saved scheduling runs

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy

### Genetic Algorithm

The scheduling algorithm currently uses:

- Population generation
- Fitness-based evaluation
- Elitism
- Faculty assignment crossover
- Mutation
- Best-ever chromosome preservation
- Fresh chromosome injection

Lower fitness values represent better schedules.

### Frontend

Planned:

- React
- TypeScript
- Vite
- Tailwind CSS

### Database

Planned:

- PostgreSQL

## Current Architecture

```text
React Frontend
      |
      v
FastAPI Backend
      |
      v
GA Service Layer
      |
      v
Genetic Algorithm
      |
      v
Best Schedule


BACKEND STRUCTURE
backend/
├── main.py
├── data/
├── genetic_algorithm/
│   ├── analysis/
│   ├── models/
│   ├── operators/
│   └── utils/
├── routers/
├── schemas/
├── services/
└── tests/


Initial Population
        |
        v
Fitness Evaluation
        |
        v
Elitism
        |
        v
Parent Selection
        |
        v
Faculty-Swap Crossover
        |
        v
Mutation
        |
        v
Fresh Chromosomes
        |
        v
Fitness Sorting
        |
        v
Best-Ever Chromosome
        |
        v
Next Generation