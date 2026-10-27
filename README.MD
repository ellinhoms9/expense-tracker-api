# Expense Tracker API

A REST API for tracking personal finances, built with Python and FastAPI.

## Features

- Create, retrieve, update, and delete transactions
- Filter transactions by date, category, and type
- Paginate transaction lists
- Generate financial summaries for a selected period
- Validate incoming data using Pydantic
- Store transactions in an SQLite database
- Automated API tests using pytest

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- pytest
- HTTPX

## Getting Started

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd expense-tracker-api
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the API

```bash
python -m uvicorn app.main:app --reload
```

### 5. Open API documentation

Visit http://127.0.0.1:8000/docs

## Run Tests

```bash
python -m pytest -v
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/transactions` | Create a transaction |
| GET | `/transactions` | List transactions |
| GET | `/transactions/{transaction_id}` | Retrieve a transaction |
| PATCH | `/transactions/{transaction_id}` | Update a transaction |
| DELETE | `/transactions/{transaction_id}` | Delete a transaction |
| GET | `/reports/summary` | Generate a financial summary |

## Project Status

Core CRUD operations, transaction filtering, financial summaries, and initial automated tests are implemented.

## License

MIT