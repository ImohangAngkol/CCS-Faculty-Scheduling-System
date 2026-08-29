from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Genetic Algorithm Faculty Scheduling API",
    version="1.0.0"
)

# React na frontend communicates with fast API through CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Faculty Scheduling API is running"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok"
    }