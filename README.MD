# Expense Tracker API

A RESTful API for managing personal finances, built with Python and FastAPI. The application supports user authentication, transaction management, filtering, pagination, and financial reports.

## Features

- **User authentication** — register and log in using email and password
- **JWT authorization** — protect API endpoints using bearer tokens
- **User data isolation** — users can access and manage only their own transactions
- **Transaction management** — create, retrieve, update, and delete transactions
- **Filtering** — filter transactions by date, category, and transaction type
- **Pagination** — retrieve transaction lists in pages
- **Financial reports** — generate summaries for a selected date range
- **Data validation** — validate request data with Pydantic
- **Database integration** — store users and transactions in SQLite using SQLAlchemy
- **Automated testing** — test API functionality and access control using pytest

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- PyJWT
- pwdlib with Argon2 password hashing
- pytest
- HTTPX

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Git

### 1. Clone the repository

```bash
git clone https://github.com/ellinhoms9/expense-tracker-api.git
cd expense-tracker-api
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the environment

Set a JWT secret key before starting the application:

```bash
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

This command generates a secret key for the current terminal session. For production, use a securely managed secret that remains consistent across application restarts.

**Important:** Never commit real secret keys or passwords to version control.

### 5. Run the API

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

- API: http://127.0.0.1:8000
- Interactive Swagger documentation: http://127.0.0.1:8000/docs

## Authentication

The API uses JSON Web Tokens (JWT) for authentication.

1. Register a user using `POST /auth/register`.
2. Log in using `POST /auth/login` to obtain an access token.
3. Use the Swagger **Authorize** button to authenticate requests.
4. Send the token as a bearer token when accessing protected endpoints.

The Swagger OAuth2 authorization flow uses `POST /auth/token`.

Passwords are hashed before being stored in the database.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Authenticate using JSON credentials |
| POST | `/auth/token` | Authenticate using OAuth2 form data |
| POST | `/transactions` | Create a transaction |
| GET | `/transactions` | List and filter transactions |
| GET | `/transactions/{transaction_id}` | Retrieve a transaction |
| PATCH | `/transactions/{transaction_id}` | Update a transaction |
| DELETE | `/transactions/{transaction_id}` | Delete a transaction |
| GET | `/reports/summary` | Generate a financial summary |

Most transaction and report endpoints require authentication.

## Example Request

Create a transaction using an authenticated request:

```http
POST /transactions
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

```json
{
  "amount": 125.50,
  "category": "Food",
  "description": "Lunch",
  "transaction_date": "2026-10-28",
  "transaction_type": "expense"
}
```

## Run Tests

Set the JWT secret key and run the test suite:

```bash
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
python -m pytest -v
```

The test suite covers API functionality, authentication, and transaction access isolation between users.

## Project Structure

```text
expense-tracker-api/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   └── security.py
├── tests/
│   └── test_api.py
├── requirements.txt
└── README.md
```

## Project Status

The core API functionality is implemented, including transaction CRUD operations, JWT authentication, user-specific data access, financial summaries, and automated tests.

## Future Improvements

- Docker support
- Continuous integration with GitHub Actions
- API deployment
- Additional test coverage and documentation

## Author

Developed as a backend portfolio project to demonstrate Python, FastAPI, REST API design, authentication, database integration, and automated testing.
