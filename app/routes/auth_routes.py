"""
Authentication API Endpoints

This module provides endpoints for user authentication,
including registration, login, and protected routes.

Endpoints:
- User registration and login.
- Protected endpoints requiring authentication.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from app.database import database
from app.utils import create_access_token, decode_access_token

# Configure log directory
log_dir = os.path.abspath(os.path.join(__file__, "../../../log"))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
log_path = os.path.join(log_dir, "auth_routes.log")
auth_routes_logger = logging.getLogger("auth_routes_logger")
auth_routes_logger.setLevel(logging.INFO)

# File and console handlers for auth_routes_logger
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()

# Adding handlers to auth_routes_logger
auth_routes_logger.addHandler(file_handler)
auth_routes_logger.addHandler(console_handler)

auth_routes_logger.info("Authentication Routes API initialized.")

# Load environment variables
load_dotenv()

# Determine the application environment
APP_ENV = os.getenv("APP_ENV", "production")

auth_router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    """
    Schema for user registration payload.

    Attributes:
        username (str): The username of the user.
        email (str): The email address of the user.
        password (str): The password of the user.
    """

    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """
    Schema for user login payload.

    Attributes:
        username (str): The username of the user.
        password (str): The password of the user.
    """

    username: str
    password: str


@auth_router.post("/register")
async def register_user(user: UserCreate):
    """
    Register a new user in the system.

    Args:
        user (UserCreate): The user registration data.

    Returns:
        dict: Success message.
    """
    if APP_ENV == "production":
        query = "SELECT * FROM users WHERE username = :username OR email = :email"
    else:
        schema_name = f"test_schema_{os.getpid()}"
        query = f"SELECT * FROM {schema_name}.users WHERE username = :username OR email = :email"

    existing_user = await database.fetch_one(
        query, values={"username": user.username, "email": user.email}
    )
    if existing_user:
        auth_routes_logger.info("Username or email already registered")
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    hashed_password = pwd_context.hash(user.password)
    if APP_ENV == "production":
        query = (
            "INSERT INTO users (username, email, hashed_password) VALUES "
            "(:username, :email, :hashed_password)"
        )
    else:
        schema_name = f"test_schema_{os.getpid()}"
        query = (
            f"INSERT INTO {schema_name}.users (username, email, hashed_password) VALUES "
            "(:username, :email, :hashed_password)"
        )
    await database.execute(
        query,
        values={
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
        },
    )
    auth_routes_logger.info("User registered successfully")
    return {"message": "User registered successfully"}


@auth_router.post("/login")
async def login_user(user: UserLogin):
    """
    Authenticate a user and generate a JWT token.

    Args:
        user (UserLogin): The user login data.

    Returns:
        dict: A JWT access token and token type.
    """
    if APP_ENV == "production":
        query = "SELECT * FROM users WHERE username = :username"
    else:
        schema_name = f"test_schema_{os.getpid()}"
        query = f"SELECT * FROM {schema_name}.users WHERE username = :username"
    db_user = await database.fetch_one(query, values={"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["hashed_password"]):
        auth_routes_logger.info("Invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials, " "please check your username and password",
        )

    # Create a JWT token
    access_token = create_access_token(data={"sub": db_user["username"]})

    # Return the token and a success message
    return {
        "message": "Login successful!",
        "access_token": access_token,
        "token_type": "bearer",
    }


@auth_router.get("/login", response_class=HTMLResponse)
async def login_page():
    """
    Serve the login HTML page.

    This endpoint serves the login HTML page to the user. The page is read from the
    static directory and returned as an HTML response. If the file is not found,
    a 404 error is returned.

    Returns:
        HTMLResponse: The login HTML page or a 404 error if the file is not found.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    login_path = os.path.join(current_dir, "../static/login.html")
    try:
        with open(login_path, "r", encoding="utf-8") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError as e:
        return HTMLResponse(
            content=f"Error: login.html not found: {e}", status_code=404
        )


@auth_router.get("/register", response_class=HTMLResponse)
async def register_page():
    """
    Serve the registration HTML page.

    This endpoint serves the registration HTML page to the user. The page is read
    from the static directory and returned as an HTML response. If the file is not found,
    a 404 error is returned.

    Returns:
        HTMLResponse: The registration HTML page or a 404 error if the file is not found.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    register_path = os.path.join(current_dir, "../static/register.html")
    try:
        with open(register_path, "r", encoding="utf-8") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError as e:
        return HTMLResponse(
            content=f"Error: register.html not found: {e}", status_code=404
        )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Validate and decode the current user's token.

    Args:
        token (str): The JWT token from the request.

    Returns:
        str: The username of the authenticated user.
    """
    payload = decode_access_token(token)
    if not payload:
        auth_routes_logger.info("Invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    auth_routes_logger.info("Valid token")
    return payload["sub"]


@auth_router.get("/protected-endpoint")
async def protected_endpoint(token: Optional[str] = None):
    """
    A protected endpoint that validates a token passed via URL.

    Args:
        token (Optional[str]): The token passed as a query parameter.

    Returns:
        dict: A greeting message with the username.
    """
    if token:
        auth_routes_logger.info("Token provided by URL")
        payload = decode_access_token(token)
        if not payload:
            auth_routes_logger.info("Invalid or expired token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        auth_routes_logger.info("Valid token, user %s", {payload["sub"]})
        return {"message": f"Hello, {payload['sub']}"}

    auth_routes_logger.info("Not authenticated, No token provided")
    raise HTTPException(status_code=401, detail="Not authenticated, No token provided")
