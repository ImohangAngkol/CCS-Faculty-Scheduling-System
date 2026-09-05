from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import faculty


app = FastAPI(
    title="CCS Faculty Scheduling System API",
    description="Backend API for the Genetic Algorithm Faculty Scheduling Decision-Support System.",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(faculty.router)


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
def root():
    return {
        "message": "CCS Faculty Scheduling System API is running"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok"
    }