import json
from pathlib import Path

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
)

from fastapi.responses import (
    Response,
)
from services.ga_service import validate_saved_result

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
# LATEST COMPLETED GA RESULT
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

LATEST_RESULT_FILE = (
    BACKEND_DIR
    / "saved_chromosomes"
    / "latest_ga_result.json"
)


def _load_latest_ga_result():
    """
    Load the most recently completed GA result.

    This is different from the saved-best chromosome.

    latest result = most recently generated schedule
    saved best    = persistent best baseline across GA runs
    """

    if not LATEST_RESULT_FILE.exists():
        return None

    try:

        with open(
            LATEST_RESULT_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return None


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

    try:
        content = path.read_bytes()
        validate_saved_result(json.loads(content))
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    # Serve exactly the bytes validated above, avoiding a second file read.
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="best_chromosome.json"'},
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
# ANALYZE LATEST COMPLETED GA RESULT
#
# DOES NOT RUN THE GA
#
# This analyzes the SAME latest result that is written by
# /api/ga/run or /api/ga/stream.
# ============================================================

@router.post("/latest/analyze")
def analyze_latest_ga_result():

    try:

        payload = _load_latest_ga_result()

        if payload is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "No latest completed GA result exists yet."
                ),
            )

        result = analyze_chromosome_payload(
            payload,
            source="latest",
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
# ANALYZE SAVED BEST
#
# DOES NOT RUN THE GA
#
# This is intentionally separate from latest/analyze.
# It analyzes the persistent best baseline chromosome.
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
