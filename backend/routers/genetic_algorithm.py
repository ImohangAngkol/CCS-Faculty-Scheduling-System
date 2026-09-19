from fastapi import APIRouter, HTTPException, Query

from services.ga_service import (
    generate_schedule,
    run_genetic_algorithm,
)


router = APIRouter(
    prefix="/api/ga",
    tags=["Genetic Algorithm"],
)


@router.get("/status")
def get_ga_status():
    return {
        "status": "ready",
        "message": "Genetic Algorithm API is available.",
    }


@router.post("/generate")
def generate_ga_schedule(
    population_size: int = Query(
        default=10,
        ge=1,
        le=500,
    ),
):
    try:
        result = generate_schedule(
            population_size=population_size,
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.post("/run")
def run_ga(
    population_size: int = Query(
        default=20,
        ge=2,
        le=500,
    ),
    generations: int = Query(
        default=5,
        ge=1,
        le=10000,
    ),
    fresh_chromosomes: int = Query(
        default=5,
        ge=0,
        le=500,
    ),
):
    try:
        result = run_genetic_algorithm(
            population_size=population_size,
            generations=generations,
            fresh_chromosomes=fresh_chromosomes,
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )