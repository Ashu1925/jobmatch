from fastapi.testclient import TestClient

from app.main import app
from app.auth import get_current_user
from app.models import User


def override_current_user() -> User:
    return User(
        id=1,
        email="test@example.com",
        password_hash="unused-in-tests",
        is_active=True,
    )


app.dependency_overrides[get_current_user] = override_current_user
client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_match_endpoint() -> None:
    response = client.post(
        "/api/match",
        json={
            "resume_text": "Python, Git and Docker experience.",
            "job_description": "Python, FastAPI, Git and Docker required.",
        },
    )

    assert response.status_code == 200
    assert response.json()["match_score"] == 75


def test_resume_endpoint_rejects_non_pdf() -> None:
    response = client.post(
        "/api/resume/extract",
        files={
            "resume": (
                "resume.txt",
                b"This is not a PDF resume.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF resumes are accepted."
