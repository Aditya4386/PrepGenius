def test_jit_student_profile_creation(client):
    """Verifies that an uninitialized student record is automatically created on first GET."""
    headers = {"Authorization": "Bearer mock_student_jit_01"}
    response = client.get("/api/v1/profile", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "mock_student_jit_01"
    assert data["target_role"] is None
    assert data["company_type"] is None
    assert data["skills"] == []
    assert data["education"] == []
    assert data["is_profile_complete"] is False


def test_update_profile_success(client):
    """Verifies updating profile with valid targeted role, company type, skills, and education."""
    headers = {"Authorization": "Bearer mock_student_update_02"}

    payload = {
        "target_role": "Backend Developer",
        "company_type": "product",
        "target_companies": ["Google", "Amazon", "Microsoft"],
        "career_goal": "Aspiring Cloud Backend Engineer targeting high-scale distributed systems.",
        "weekly_study_hours": 15.0,
        "preparation_deadline": "2026-12-31",
        "skills": [
            {"name": "Python", "level": "advanced"},
            {"name": "FastAPI", "level": "intermediate"},
            {"name": "MySQL", "level": "intermediate"},
        ],
        "education": [
            {
                "institution": "National Institute of Technology",
                "degree": "B.Tech Information Technology",
                "year_of_completion": 2026,
                "cgpa": 9.1,
            }
        ],
    }

    response = client.put("/api/v1/profile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["student_id"] == "mock_student_update_02"
    assert data["target_role"] == "Backend Developer"
    assert data["company_type"] == "product"
    assert len(data["target_companies"]) == 3
    assert data["weekly_study_hours"] == 15.0
    assert len(data["skills"]) == 3
    assert data["skills"][0]["name"] == "Python"
    assert data["skills"][0]["level"] == "advanced"
    assert len(data["education"]) == 1
    assert data["education"][0]["cgpa"] == 9.1
    assert data["is_profile_complete"] is True


def test_reject_invalid_target_role(client):
    """Verifies that an unsupported role outside the 36 locked roles is rejected with 422."""
    headers = {"Authorization": "Bearer mock_student_role_err"}
    payload = {
        "target_role": "Invalid Made Up Hacker Role",
        "company_type": "product",
    }
    response = client.put("/api/v1/profile", json=payload, headers=headers)
    assert response.status_code == 422


def test_reject_invalid_company_type(client):
    """Verifies that company type must be product, service, or startup."""
    headers = {"Authorization": "Bearer mock_student_company_err"}
    payload = {
        "target_role": "Full-Stack Developer",
        "company_type": "nonprofit",  # invalid
    }
    response = client.put("/api/v1/profile", json=payload, headers=headers)
    assert response.status_code == 422


def test_reject_out_of_bound_weekly_hours(client):
    """Verifies that weekly study hours must be between 1.0 and 80.0."""
    headers = {"Authorization": "Bearer mock_student_hours_err"}

    # Test excessive hours (> 80)
    response_high = client.put(
        "/api/v1/profile",
        json={"weekly_study_hours": 120.0},
        headers=headers,
    )
    assert response_high.status_code == 422

    # Test negative hours
    response_low = client.put(
        "/api/v1/profile",
        json={"weekly_study_hours": -5.0},
        headers=headers,
    )
    assert response_low.status_code == 422


def test_data_ownership_and_cross_student_isolation(client):
    """Verifies that Student A and Student B have strictly isolated profiles."""
    headers_a = {"Authorization": "Bearer mock_student_alpha"}
    headers_b = {"Authorization": "Bearer mock_student_beta"}

    # Update Student A's profile
    client.put(
        "/api/v1/profile",
        json={
            "target_role": "Data Analyst",
            "company_type": "service",
            "weekly_study_hours": 12.0,
            "skills": [{"name": "SQL", "level": "advanced"}],
        },
        headers=headers_a,
    )

    # Update Student B's profile
    client.put(
        "/api/v1/profile",
        json={
            "target_role": "AI/ML Engineer",
            "company_type": "startup",
            "weekly_study_hours": 25.0,
            "skills": [{"name": "PyTorch", "level": "advanced"}],
        },
        headers=headers_b,
    )

    # Read Student A - ensure no Student B data leaked
    res_a = client.get("/api/v1/profile", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["student_id"] == "mock_student_alpha"
    assert data_a["target_role"] == "Data Analyst"
    assert data_a["skills"][0]["name"] == "SQL"

    # Read Student B - ensure no Student A data leaked
    res_b = client.get("/api/v1/profile", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["student_id"] == "mock_student_beta"
    assert data_b["target_role"] == "AI/ML Engineer"
    assert data_b["skills"][0]["name"] == "PyTorch"
