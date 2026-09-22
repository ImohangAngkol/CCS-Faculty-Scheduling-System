from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import faculty
from routers import genetic_algorithm

from routers import chromosomes

app = FastAPI(
    title="CCS Faculty Scheduling System API",
    description=(
        "Backend API for the Genetic Algorithm-based "
        "Faculty Scheduling Decision-Support System."
    ),
    version="1.0.0"
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

app.include_router(faculty.router)
app.include_router(genetic_algorithm.router)
app.include_router(chromosomes.router)


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "message": "CCS Faculty Scheduling System API is running."
    }


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "ok"
    }