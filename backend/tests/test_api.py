from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert "message" in data


def test_health():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


def test_ga_status():
    response = client.get("/api/ga/status")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"


def test_generate_initial_population():
    response = client.post(
        "/api/ga/generate",
        params={
            "population_size": 2,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"

    data = body["data"]

    assert data["population_generated"] > 0
    assert data["fitness"] >= 0
    assert len(data["schedule"]) > 0

    required_fields = {
        "subject",
        "title",
        "type",
        "day",
        "start",
        "end",
        "section",
        "faculty",
        "room",
    }

    for entry in data["schedule"]:
        assert required_fields.issubset(
            entry.keys()
        )


def test_full_ga_run():
    response = client.post(
        "/api/ga/run",
        params={
            "population_size": 6,
            "generations": 1,
            "fresh_chromosomes": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"

    data = body["data"]

    assert data["best_fitness"] >= 0
    assert data["generations_completed"] == 1
    assert data["population_size"] == 6

    assert "fitness_breakdown" in data
    assert "history" in data
    assert "schedule" in data

    breakdown = data["fitness_breakdown"]

    expected_breakdown_fields = {
        "subject_preference",
        "time_preference",
        "day_preference",
        "number_of_preparations",
        "teaching_load_balance",
        "daily_teaching_load",
    }

    assert expected_breakdown_fields.issubset(
        breakdown.keys()
    )

    # The individual penalties should equal total fitness.
    assert sum(
        breakdown.values()
    ) == data["best_fitness"]


def test_best_ever_never_gets_worse():
    response = client.post(
        "/api/ga/run",
        params={
            "population_size": 6,
            "generations": 2,
            "fresh_chromosomes": 1,
        },
    )

    assert response.status_code == 200

    history = response.json()["data"]["history"]

    best_values = []

    for row in history:

        if row["generation"] == 0:
            best_values.append(
                row["best_fitness"]
            )
        else:
            best_values.append(
                row["best_ever_fitness"]
            )

    for previous, current in zip(
        best_values,
        best_values[1:],
    ):
        assert current <= previous