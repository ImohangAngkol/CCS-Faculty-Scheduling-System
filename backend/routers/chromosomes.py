from fastapi import (
    APIRouter,
    Body,
    HTTPException,
)

from fastapi.responses import (
    FileResponse,
)

from services.chromosome_service import (
    get_best_chromosome_path,
    get_saved_best_metadata,
    load_saved_best_payload,
    load_uploaded_payload,
    save_uploaded_payload,
)

from services.chromosome_analysis_service import (
    analyze_chromosome_payload,
)


router = APIRouter(
    prefix="/api/chromosomes",
    tags=["Chromosomes"],
)


# ============================================================
# SAVED BEST STATUS
# ============================================================

@router.get("/best")
def get_saved_best():

    return {
        "status": "success",
        "data": get_saved_best_metadata(),
    }


# ============================================================
# DOWNLOAD SAVED BEST
# ============================================================

@router.get("/best/download")
def download_saved_best():

    path = get_best_chromosome_path()


    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "No saved best chromosome exists yet."
            ),
        )


    return FileResponse(
        path=path,
        filename="best_chromosome.json",
        media_type="application/json",
    )


# ============================================================
# UPLOAD CHROMOSOME
# ============================================================

@router.post("/upload")
def upload_baseline(
    payload: dict = Body(...),
):

    try:

        normalized = save_uploaded_payload(
            payload
        )


        return {
            "status": "success",

            "message":
                "Chromosome uploaded successfully.",

            "data": {
                "fitness":
                    normalized.get(
                        "best_fitness"
                    ),

                "entries":
                    len(
                        normalized.get(
                            "schedule",
                            [],
                        )
                    ),
            },
        }


    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ============================================================
# ANALYZE SAVED BEST
#
# DOES NOT RUN THE GA
# ============================================================

@router.post("/best/analyze")
def analyze_saved_best():

    try:

        payload = load_saved_best_payload()


        if payload is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "No saved best chromosome exists yet."
                ),
            )


        result = analyze_chromosome_payload(
            payload,
            source="saved",
        )


        return {
            "status": "success",
            "data": result,
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ============================================================
# ANALYZE UPLOADED CHROMOSOME
#
# DOES NOT RUN THE GA
# ============================================================

@router.post("/uploaded/analyze")
def analyze_uploaded_chromosome():

    try:

        payload = load_uploaded_payload()


        if payload is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "No uploaded chromosome exists."
                ),
            )


        result = analyze_chromosome_payload(
            payload,
            source="uploaded",
        )


        return {
            "status": "success",
            "data": result,
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )