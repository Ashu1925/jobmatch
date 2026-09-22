from app.matching import calculate_match, extract_skills


def test_postgresql_does_not_create_separate_sql_skill() -> None:
    assert extract_skills("PostgreSQL") == {"postgresql"}


def test_java_backend_aliases_are_normalized() -> None:
    skills = extract_skills(
        "Java, Spring Boot, RESTful APIs, CI/CD and Microservices"
    )

    assert {
        "java",
        "spring boot",
        "rest api",
        "ci/cd",
        "microservices",
    }.issubset(skills)


def test_match_score_and_skill_explanations() -> None:
    result = calculate_match(
        resume_text="Python, Git and Docker",
        job_description="Python, FastAPI, Git and Docker",
    )

    assert result == {
        "match_score": 75,
        "matching_skills": ["docker", "git", "python"],
        "missing_skills": ["fastapi"],
    }
