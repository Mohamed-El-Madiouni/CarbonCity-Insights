# CarbonCity Insights

`CarbonCity Insights` is a comprehensive data engineering and API development project designed to provide vehicle emission insights. It includes features such as user authentication, advanced rate limiting, caching, interactive interfaces, and integration with external APIs for environmental data.

---
## Table of Contents

1. [Features](#features)
2. [Technologies Used](#technologies-used)
3. [Project Goals](#project-goals)
4. [Project Structure](#project-structure)
5. [Setup and Installation](#setup-and-installation)
6. [Configuration](#configuration)
7. [API Documentation](#api-documentation)
   1. [Authentication Endpoints](#authentication-endpoints)
   2. [Vehicle Emissions Endpoints](#vehicle-emissions-endpoints)
8. [Running Tests](#running-tests)
9. [Logging](#logging)
10. [Rate Limiting](#rate-limiting)
11. [Contributing](#contributing)
<br>
<br>
---

## Features

1. User authentication with JWT.
2. Rate limiting to prevent abuse, implemented via Redis.
3. Vehicle emissions API with filtering, pagination, and comparison capabilities.
4. Interactive web pages for comparing vehicle emissions.
5. Backend integration with the Carbon Interface API for real-time emissions data.
6. Database operations with PostgreSQL, including schema management and data deduplication.
7. Asynchronous processing and caching for performance optimization.
8. CI/CD pipelines with linting, formatting, and testing using GitHub Actions.
9. Detailed logging for debugging and performance monitoring.

---

## Technologies Used

- **Python**: Core programming language for the entire project.
- **FastAPI**: Framework for API development.
- **PostgreSQL**: Relational database for storing and querying data.
- **Redis**: In-memory caching and rate limiting.
- **GitHub Actions**: CI/CD pipeline for automated testing and deployment.
- **Render**: Cloud hosting platform for deploying the API.
- **Pytest**: Unit, integration, and performance testing.
- **Pydantic**: For data validation and schema enforcement.
- **JWT**: JSON Web Tokens for secure user authentication.
- **HTML/CSS/JavaScript**: For user-facing interfaces like login, registration, and vehicle emissions comparison.
<br>
<br>

---

## Project Goals

1. Develop a scalable API aggregating vehicle emissions data from external APIs and storing it efficiently.
2. Implement advanced data engineering practices, including caching, monitoring, and database optimization.
3. Provide a feature-rich comparison interface for analyzing carbon emissions.
4. Showcase rate-limiting, authentication, and real-world data fetching pipelines.

<br>
<br>

---

## Project Structure
- **`.github/`**: CI/CD workflows for testing, linting, and deployment.
- **`app/`**: Application logic.
  - **`routes/`**: FastAPI route definitions for authentication and vehicle emissions.
  - **`services/`**: Business logic and data fetching from external APIs.
  - **`static/`**: HTML files for login, registration, and vehicle comparison.
  - **`database.py`**: Database connection and schema management.
  - **`main.py`**: FastAPI application entry point.
  - **`redis_cache.py`**: Redis caching utilities.
  - **`utils.py`**: Utilities for JWT, serialization, and helpers.
- **`tests/`**: Unit, integration, and rate-limiting tests.
  - **`test_routes/`**: Route-specific tests.
  - **`test_services/`**: Service and database integration tests.
  - **`test_rate_limiting.py`**: Tests for rate-limiting functionality.
  - **`conftest.py`**: Common test fixtures.
- **`.env`**: Environment variables for configuration.
- **`README.md`**: Project documentation.
- **`requirements.txt`**: Python dependencies.
- **`pytest.ini`**: Pytest configuration for logging and async tests.
<br>
<br>
---

## Setup and Installation

### Prerequisites
- Python >= 3.10
- PostgreSQL >= 12
- Redis >= 5.0
- Virtual environment tool (`venv`, `virtualenv`, etc.)

### Steps
1. Clone the repository:
```bash
git clone https://github.com/mohamed-el-madiouni/CarbonCity-Insights.git
cd CarbonCity-Insights
```
2. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Configure environment variables in the `.env` file:
```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
APP_ENV=production/test
REDIS_URL=redis://URL:6379/0
JWT_SECRET_KEY=secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=300
RENDER_SERVICE_ID=srv-***********
CARBON_INTERFACE_API_KEY=**************
NOTIFICATION_EMAIL=xxxx@gmail.com
EMAIL_PASSWORD=**************

```
4.  Run the FastAPI application:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
The API documentation will be available at https://carboncity-insights.onrender.com/docs.
<br>
<br>
---

## Configuration

### `.env` File

Critical configurations, such as database credentials, Redis settings, and API keys, are managed through the `.env` file.

### Database setup
Ensure that the production and test databases are configured and accessible.

### CI/CD Integration
The GitHub Actions workflow (`.github/workflows/ci_cd.yaml`) automates linting, testing, and deployment to Render.
<br>
<br>
---

## API Documentation

**API URL** : https://carboncity-insights.onrender.com

---

### Authentication Endpoints
| Endpoint    | Method | Description                     |
|-------------|--------|---------------------------------|
| `/register` | POST   | Register a new user.           |
| `/login`    | POST   | Authenticate a user.           |

---

#### `/register`

**Method**: `POST`  
**Description**: Registers a new user by storing their email and hashed password.

**Parameters**:
`
- `email` (required): The user's email.
- `password` (required): The user's password.
`

**Example Request**:
```bash
curl -X POST "https://carboncity-insights.onrender.com/register" \
-H "Content-Type: application/json" \
-d '{
    "username": "username",
    "email": "user@example.com",
    "password": "securepassword"
}'
```

**Example Response**:
```bash
{
    "message": "User registered successfully."
}
```

---

#### `/login`

**Method**: `POST  
**Description**: Authenticates a user and generates a JWT token.

**Parameters**:
`
- `email` (required): The user's email.
- `password` (required): The user's password.
`

**Example Request**:
```bash
curl -X POST "https://carboncity-insights.onrender.com/login" \
-H "Content-Type: application/json" \
-d '{
    "username": "username",
    "password": "securepassword"
}'
```

**Example Response**:
```bash
{
    "message"= "Login successful!",
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer"
}
```

---

### Vehicle Emissions Endpoints


| Endpoint                     | Method | Description |
|------------------------------|--------|-------------|
| `/vehicle_emissions`         | GET    | Retrieves vehicle emissions data with filters. |
| `/vehicle_emissions/makes`   | GET    | Retrieve the list of available vehicle manufacturers. |
| `/vehicle_emissions/models`  | GET    | Retrieve the list of models for a specific manufacturer. |
| `/vehicle_emissions/years`   | GET    | Retrieve the available years for a specific vehicle model and manufacturer. |
| `/vehicle_emissions/compare` | GET    | Serve an interactive HTML page to compare vehicle emissions. |
| `/vehicle_emissions/compare` | POST   | Compare carbon emissions between two vehicles. |

### Vehicle Emissions Endpoint

#### `/vehicle_emissions`  
**Method**: `GET`  
**Description**: Fetches vehicle emissions data, supports filtering and pagination.

**Parameters**:
- `vehicle_make_name` (optional): Filter results by vehicle manufacturer.
- `year` (optional): Filter results by the year of manufacture.
- `cursor` (optional): Cursor for pagination. Omit for the first page.
- `limit` (optional): Number of records per page. Default is 10. Max is 200.

**Example Request**:
```bash
curl -X GET "https://carboncity-insights.onrender.com/vehicle_emissions?vehicle_make_name=Ferrari&year=2010&limit=5&token=eyJhbG..."
```

**Example Response**:
```json
{
  "data": [
    {
      "id": "e43e1bee-cb9f-4a7c-8868-365ee07d2ea1",
      "vehicle_model_name": "California",
      "vehicle_make_name": "Ferrari",
      "year": 2010,
      "distance_value": 100.0,
      "distance_unit": "km",
      "carbon_emission_g": 36814.0
    }
  ],
  "next_cursor": "e77e1bee-cb9f-4a7c-8868-365ee07d2ea1"
}
```
<br>
---

#### `/vehicle_emissions/makes`  
**Method**: `GET`  
**Description**: Retrieve a list of available vehicle manufacturers.

**Parameters**: None

**Example Request**:
```bash
curl -X GET "https://carboncity-insights.onrender.com/vehicle_emissions/makes?token=eyJhbG..."
```

**Example Response**:
```json
{
  "makes": [
    "Alfa Romeo",
    "Ferrari"
  ]
}
```
<br>
---
#### `/vehicle_emissions/models`  
**Method**: `GET`  
**Description**: Retrieve the list of models for a specific manufacturer.

**Parameters**:
- `make` (required): The manufacturer name.

**Example Request**:
```bash
curl -X GET "https://carboncity-insights.onrender.com/vehicle_emissions/models?make=Ferrari&token=eyJhbG..."
```

**Example Response**:
```json
{
  "models": [
    "458 Italia",
    "F40",
    "Mondial"
  ]
}
```
<br>

---
#### `/vehicle_emissions/years`  
**Method**: `GET`  
**Description**: Retrieve the available years for a specific vehicle model and manufacturer.

**Parameters**:
- `make` (required): The manufacturer name.
- `model` (required): The model name.

**Example Request**:
```bash
curl -X GET "https://carboncity-insights.onrender.com/vehicle_emissions/years?make=Ferrari&model=F40&token=eyJhbG..."
```

**Example Response**:
```json
{
  "years": [
    1991,
    1992
  ]
}
```
<br>

---
#### `/vehicle_emissions/compare`  
**Method**: `GET`  
**Description**: Serve an interactive HTML page to compare vehicle emissions.

**Parameters**: None

**Example Request**:
```bash
curl -X GET "https://carboncity-insights.onrender.com/vehicle_emissions/compare?token=eyJhbG..."
```

**Example Response**:
- Returns an HTML page (not JSON).
<br>

---
#### `/vehicle_emissions/compare`  
**Method**: `POST`  
**Description**: Compare carbon emissions between two vehicles.

**Parameters**:
- `vehicle_1` 
  - `make` (required): Manufacturer of the first vehicle.
  - `model` (required): Model of the first vehicle.
  - `year` (required): Year of the first vehicle.
- `vehicle_2` 
  - `make` (required): Manufacturer of the second vehicle.
  - `model` (required): Model of the second vehicle.
  - `year` (required): Year of the second vehicle.

**Example Request**:
```bash
curl -X POST "https://carboncity-insights.onrender.com/vehicle_emissions/compare?token=eyJhbG..." \
-H "Content-Type: application/json" \
-d '{
    "vehicle_1": {"make": "Ferrari", "model": "F40", "year": 1991},
    "vehicle_2": {"make": "Ferrari", "model": "Ferrari F50", "year": 1995}
}'
```

**Example Response**:
```json
{
  "vehicle_1": {
    "vehicle_make_name": "Ferrari",
    "vehicle_model_name": "F40",
    "year": 1991,
    "carbon_emission_g": 42477.0
  },
  "vehicle_2": {
    "vehicle_make_name": "Ferrari",
    "vehicle_model_name": "Ferrari F50",
    "year": 1995,
    "carbon_emission_g": 69026.0
  },
  "comparison": {
    "message": "Ferrari F40 (1991) consumption : 42477.0 g/100km.<br><br>Ferrari Ferrari F50 (1995) consumption : 69026.0 g/100km.<br><br>So the Ferrari F40 (1991) emits 38.46% less carbon compared to the Ferrari Ferrari F50 (1995).",
    "percentage_difference": 38.46
  }
}
```
<br>



---

## Running Tests, Logging, Rate Limiting

### Running Tests

#### Unit Tests

Run unit tests for core functionalities:
```bash
PYTHONPATH=. pytest tests/test_routes/
```

#### Integration Tests
Run tests for database interactions and endpoint integration:
```bash
PYTHONPATH=. pytest tests/test_services/
```

#### All Tests
Run all tests:
```bash
PYTHONPATH=. pytest
```
<br>

---

## Logging

Logs are stored in the `log/` directory and provide details about:
- **API requests**: Including response times and endpoints hit.
- **Database interactions**: Query execution times and errors.
- **Redis operations**: Cache hits/misses and rate-limiting details.
- **Error tracking**: Stack traces for debugging.
Log levels can be configured as `INFO` or `ERROR`.


<br>
<br>

---

## Rate Limiting

Rate limiting is implemented using Redis to prevent abuse and ensure fair usage. Default limits:
- **10 requests per minute** for general API endpoints.
- **5 requests per minute** for heavy endpoints like `/compare`.

### Why Redis for Rate Limiting?
Redis was chosen for its high-speed in-memory operations, making it ideal for real-time rate limiting. Its ability to handle expiring keys ensures that rate limit windows reset efficiently without additional cleanup logic. Moreover, Redis supports atomic operations, which guarantees accuracy even under heavy concurrent requests.

### How Rate Limiting Protects the API
Rate limiting ensures that the API is not overwhelmed by excessive requests from a single user or malicious bots. By capping the number of requests allowed within a given time window:
- It mitigates the risk of **DDoS attacks** by throttling abusive clients.
- It ensures fair resource allocation among all users.
- It preserves the server's performance, especially for computationally intensive endpoints like `/compare`.

### Configurable Rate Limiting Parameters
The rate limiting thresholds can be adjusted using the following environment variables in the `.env` file:
- `RATE_LIMIT_GENERAL`: Maximum requests allowed per minute for general endpoints (default: 10).
- `RATE_LIMIT_HEAVY`: Maximum requests allowed per minute for heavy endpoints like `/compare` (default: 5).
- `RATE_LIMIT_WINDOW`: Duration of the rate limiting window in seconds (default: 60).

Example:
```bash
RATE_LIMIT_GENERAL=20
RATE_LIMIT_HEAVY=10
RATE_LIMIT_WINDOW=120
```

These values can be modified to suit the expected traffic and resource allocation needs of the API.

### Response on Limit Exceeded
```bash
HTTP/1.1 429 Too Many Requests
{
    "detail": "You have reached the limit of requests allowed per minute. Please wait one minute and try again later."
}
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch:
```bash
git checkout -b feature/your-feature
```
3. Commit your changes and push them:
```bash
git commit -m "Add new feature"
git push origin feature/your-feature
```
4. Create a pull request.
