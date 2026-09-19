from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_generate_rejects_zero_population():
    response = client.post(
        "/api/ga/generate",
        params={
            "population_size": 0,
        },
    )

    assert response.status_code in (400, 422)


def test_generate_rejects_negative_population():
    response = client.post(
        "/api/ga/generate",
        params={
            "population_size": -1,
        },
    )

    assert response.status_code in (400, 422)


def test_run_rejects_zero_population():
    response = client.post(
        "/api/ga/run",
        params={
            "population_size": 0,
            "generations": 1,
            "fresh_chromosomes": 1,
        },
    )

    assert response.status_code in (400, 422)


def test_run_rejects_negative_generations():
    response = client.post(
        "/api/ga/run",
        params={
            "population_size": 6,
            "generations": -1,
            "fresh_chromosomes": 1,
        },
    )

    assert response.status_code in (400, 422)


def test_run_rejects_negative_fresh_chromosomes():
    response = client.post(
        "/api/ga/run",
        params={
            "population_size": 6,
            "generations": 1,
            "fresh_chromosomes": -1,
        },
    )

    assert response.status_code in (400, 422)


def test_run_accepts_small_valid_values():
    response = client.post(
        "/api/ga/run",
        params={
            "population_size": 6,
            "generations": 1,
            "fresh_chromosomes": 1,
        },
    )

    assert response.status_code == 200