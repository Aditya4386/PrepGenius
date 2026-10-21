def test_register_student_success(client):
    """Test successful student registration, password hashing, and token issuance."""
    payload = {
        "full_name": "Aditya Sharma",
        "email": "aditya.sharma@example.edu",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["student"]["email"] == "aditya.sharma@example.edu"
    assert data["student"]["full_name"] == "Aditya Sharma"
    assert data["student"]["id"].startswith("std_")

    # Verify that calling /api/v1/profile with this token immediately works (JIT profile initialized)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    profile_res = client.get("/api/v1/profile", headers=headers)
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["student_id"] == data["student"]["id"]


def test_register_duplicate_email_fails(client):
    """Test that registering an existing email address is rejected with 400."""
    payload = {
        "full_name": "Rohan Verma",
        "email": "rohan.duplicate@example.com",
        "password": "Password123!",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt second registration with same email
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()


def test_login_success(client):
    """Test student login with valid credentials."""
    # First register
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pooja Patel",
            "email": "pooja.patel@example.com",
            "password": "CorrectPassword456!",
        },
    )

    # Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "pooja.patel@example.com",
            "password": "CorrectPassword456!",
        },
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["student"]["full_name"] == "Pooja Patel"

    # Test /api/v1/auth/me
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "pooja.patel@example.com"


def test_login_invalid_password_fails(client):
    """Test login rejection when password is wrong."""
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Karan Mehra",
            "email": "karan@example.com",
            "password": "RealPassword789!",
        },
    )

    bad_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "karan@example.com",
            "password": "WrongPassword999!",
        },
    )
    assert bad_login.status_code == 401
    assert "invalid email or password" in bad_login.json()["detail"].lower()
