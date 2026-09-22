# CCS Faculty Scheduling System
## System Architecture

The CCS Faculty Scheduling System is a web-based decision-support
system that uses a Genetic Algorithm to generate faculty schedules.

## Technology Stack

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS
- React Router

### Backend
- Python
- FastAPI
- Uvicorn
- Pydantic

### Genetic Algorithm
The Genetic Algorithm is implemented in Python and is responsible
for generating and optimizing faculty schedules.

The current optimization process evaluates schedules using the
following soft-constraint fitness components:

1. Subject preference
2. Time preference
3. Day preference
4. Number of preparations
5. Teaching load balance
6. Daily teaching load

Lower fitness values represent better schedules.

### Database

PostgreSQL is planned for persistent storage. Database integration
has not yet been implemented.

## High-Level Architecture

Faculty / Administrator
        |
        v
React Frontend
        |
        | HTTP / API
        v
FastAPI Backend
        |
        v
Genetic Algorithm
        |
        v
Generated Faculty Schedule

Future:

React Frontend
        |
        v
FastAPI Backend
       / \
      /   \
     v     v
PostgreSQL   Genetic Algorithm