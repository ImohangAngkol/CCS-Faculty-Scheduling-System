from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import faculty
from routers import genetic_algorithm
from routers import preferences
from routers import chromosomes
from routers import subjects
from routers import ga_history
from routers import fitness_analysis
from routers import auth
from routers import schedules
from routers import external_schedules
from routers import external_confirmations
from routers import ga_constrained
from routers import adjustments
from services.auth_service import allowed_origins
from services.preference_authorization import require_admin, require_principal
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(
    title="CCS Faculty Scheduling System API",
    description=(
        "Backend API for the Genetic Algorithm-based "
        "Faculty Scheduling Decision-Support System."
    ),
    version="1.0.0"
)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(_request, error):
    # Do not echo passwords or credential-bearing payloads in validation errors.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in error.errors()]})


@app.middleware("http")
async def private_response_headers(request, call_next):
    response = await call_next(request)
    if request.url.path not in {"/", "/api/health", "/docs", "/openapi.json", "/redoc"}:
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

app.include_router(
    preferences.router
)

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

app.include_router(faculty.router)
app.include_router(genetic_algorithm.router, dependencies=[Depends(require_admin)])
app.include_router(chromosomes.router, dependencies=[Depends(require_admin)])
app.include_router(subjects.router, dependencies=[Depends(require_principal)])
app.include_router(ga_history.router, dependencies=[Depends(require_admin)])
app.include_router(fitness_analysis.router, dependencies=[Depends(require_admin)])
app.include_router(auth.router)
app.include_router(schedules.router)
app.include_router(external_schedules.router)
app.include_router(external_confirmations.router)
app.include_router(ga_constrained.router)
app.include_router(adjustments.router)


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
