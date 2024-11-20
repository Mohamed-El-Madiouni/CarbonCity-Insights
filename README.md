# CarbonCity Insights

**CarbonCity Insights** is a data engineering project designed to analyze and visualize carbon emissions and energy consumption for various cities. The project leverages external APIs and structured data processing to provide real-time insights into urban energy usage and environmental impact.
<br>
<br>
---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Setup and Installation](#setup-and-installation)
4. [Configuration](#configuration)
5. [API Documentation](#api-documentation)
   1. [Endpoints Overview](#endpoints-overview)
   2. [Vehicle Emissions Endpoint](#vehicle-emissions-endpoint)
6. [Running Tests](#running-tests)
7. [Logging](#logging)
8. [Contributing](#contributing)
<br>
<br>
---

## Project Overview

CarbonCity Insights processes and analyzes vehicle and city data to calculate carbon emissions. The project uses Python, FastAPI, and PostgreSQL to provide a scalable backend API. It includes pagination, filtering, and efficient database querying to handle large datasets effectively.
<br>
<br>
---

## Project Structure
- **.github/** : CI/CD workflows for automated testing and deployment
- **app/** : Application logic
  - **routes/** : FastAPI route definitions
  - **services/** : Business logic and data processing
  - **database.py** : Database connection and schema management
  - **main.py** : FastAPI application entry point
- **tests/** : Unit and integration tests
  - **test_routes/** : Route-specific tests
  - **test_services/** : Service and database integration tests
  - **conftest.py** : Common fixtures for testing
- **.env** : Environment variables
- **README.md** : Project documentation
- **requirements.txt** : Python dependencies
- **pytest.ini** : Pytest configuration
<br>
<br>
---

## Setup and Installation

### Prerequisites
- Python >= 3.10
- PostgreSQL >= 12
- Virtual environment tool (`venv`, `virtualenv`, etc.)

### Steps
1. Clone the repository :
```bash
git clone https://github.com/mohamed-el-madiouni/CarbonCity-Insights.git
cd CarbonCity-Insights
```
2. Create a virtual environment and install dependencies :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Configure environment variables in the `.env` file :
```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
APP_ENV=production/test
RENDER_SERVICE_ID=srv-***********
CARBON_INTERFACE_API_KEY=**************
NOTIFICATION_EMAIL=xxxx@gmail.com
EMAIL_PASSWORD=**************

```
4.  Run the FastAPI application :
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
The API documentation will be available at http://localhost:8000/docs.
<br>
<br>
---

## Configuration

- `.env` **file**: All critical configurations are managed through environment variables.
- **Database setup**: Ensure that the production and test databases are configured and accessible.
- **CI/CD Integration**: The GitHub Actions workflow file (`.github/workflows/ci_cd.yaml`) automates testing and deployment.
<br>
<br>
---

## API Documentation

**API URL** : https://carboncity-insights.onrender.com

### Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Returns a welcome message. |
| `/db_test` | GET | Tests the database connection. |
| `/vehicle_emissions` | GET | Retrieves vehicle emissions data with filters. |

### Vehicle Emissions Endpoint

**URL**: `/vehicle_emissions`  
**Method**: `GET`  
**Description**: Fetches vehicle emissions data, supports filtering and pagination.

**Parameters**:
- `vehicle_make_name` (optional): Filter results by vehicle manufacturer.
- `year` (optional): Filter results by the year of manufacture.
- `cursor` (optional): Cursor for pagination. Omit for the first page.
- `limit` (optional): Number of records per page. Default is 10. Max is 200.

**Example Request**:
```bash
curl -X GET "http://localhost:8000/vehicle_emissions?vehicle_make_name=Ferrari&year=2010&limit=5"
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

## Running Tests

### Unit Tests
Run unit tests for core functionalities:
```bash
PYTHONPATH=. pytest tests/test_routes/
```

### Integration Tests
Run tests for database interactions and endpoint integration:
```bash
PYTHONPATH=. pytest tests/test_services/
```

### All Tests
Run all tests:
```bash
PYTHONPATH=. pytest
```
<br>

---

## Logging

Logs are stored in the `log/` directory and include details about API requests, database interactions, and errors.<br>
You can configure logging levels :
 - **INFO**: Logs successful operations.
 - **ERROR**: Logs issues during execution.
<br>
<br>

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
