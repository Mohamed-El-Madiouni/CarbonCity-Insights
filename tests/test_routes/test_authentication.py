"""
Test suite for authentication-related functionality in the FastAPI application.

This file contains tests for the following features:
- User registration, including successful registration and duplicate user handling.
- User login, covering both successful logins and invalid credentials.
- Rendering of HTML pages for login and registration.

Tested Endpoints:
- POST /register: User registration.
- POST /login: User login.
- GET /login: Rendering of the login page.
- GET /register: Rendering of the registration page.

Each test case verifies specific behaviors and response formats to ensure the authentication
system functions correctly in both success and error scenarios.

Dependencies:
- Pytest for asynchronous testing.
- FastAPI TestClient for simulating HTTP requests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_register_user(test_client, user_test):
    """
    Test the user registration endpoint.
    """
    response = await test_client.post("/register", json=user_test)
    assert response.status_code == 200
    assert response.json() == {"message": "User registered successfully"}


@pytest.mark.asyncio
async def test_register_user_duplicate(test_client, user_test):
    """
    Test registering a user with an existing username or email.
    """
    # Register the user once
    await test_client.post("/register", json=user_test)

    # Attempt to register the same user again
    response = await test_client.post("/register", json=user_test)
    assert response.status_code == 400
    assert response.json() == {"detail": "Username or email already registered"}


@pytest.mark.asyncio
async def test_login_user_success(test_client, user_test):
    """
    Test successful login for a registered user.
    """
    # Register the user
    await test_client.post("/register", json=user_test)

    # Login with the registered user
    login_data = {"username": user_test["username"], "password": user_test["password"]}
    response = await test_client.post("/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["message"] == "Login successful!"


@pytest.mark.asyncio
async def test_login_user_invalid_credentials(test_client):
    """
    Test login with invalid credentials.
    """
    login_data = {"username": "invaliduser", "password": "wrongpassword"}
    response = await test_client.post("/login", json=login_data)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login_page():
    """
    Test rendering the login HTML page.
    """
    response = client.get("/login")
    assert response.status_code == 200
    assert "<title>Login</title>" in response.text


def test_register_page():
    """
    Test rendering the register HTML page.
    """
    response = client.get("/register")
    assert response.status_code == 200
    assert "<title>Register</title>" in response.text
