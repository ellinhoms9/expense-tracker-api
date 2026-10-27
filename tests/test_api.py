
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=test_engine)


def test_create_transaction(client):
    response = client.post(
        "/transactions",
        json={
            "amount": 250.50,
            "category": "Food",
            "description": "Lunch",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 201
    assert response.json()["category"] == "Food"


def test_reject_negative_amount(client):
    response = client.post(
        "/transactions",
        json={
            "amount": -100,
            "category": "Food",
            "description": "Invalid expense",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 422


def test_missing_transaction_returns_404(client):
    response = client.get("/transactions/999")

    assert response.status_code == 404


def test_delete_transaction(client):
    create_response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "Food",
            "description": "Test",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/transactions/{transaction_id}"
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/transactions/{transaction_id}"
    )

    assert get_response.status_code == 404


def test_update_transaction(client):
    create_response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "Food",
            "description": "Lunch",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    update_response = client.patch(
        f"/transactions/{transaction_id}",
        json={
            "amount": 150,
            "description": "Dinner",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["amount"] == "150.00"
    assert update_response.json()["description"] == "Dinner"
    assert update_response.json()["category"] == "Food"



def test_filter_transactions_by_category(client):
    transactions = [
        {
            "amount": 100,
            "category": "Food",
            "description": "Lunch",
            "transaction_date": "2026-10-20",
            "transaction_type": "expense",
        },
        {
            "amount": 200,
            "category": "Transport",
            "description": "Taxi",
            "transaction_date": "2026-10-21",
            "transaction_type": "expense",
        },
        {
            "amount": 300,
            "category": "Food",
            "description": "Dinner",
            "transaction_date": "2026-10-22",
            "transaction_type": "expense",
        },
    ]

    for transaction in transactions:
        response = client.post("/transactions", json=transaction)
        assert response.status_code == 201

    response = client.get("/transactions", params={"category": "Food"})

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(
        transaction["category"] == "Food"
        for transaction in response.json()
    )


def test_filter_transactions_by_type(client):
    transactions = [
        {
            "amount": 3000,
            "category": "Salary",
            "description": "Monthly salary",
            "transaction_date": "2026-10-20",
            "transaction_type": "income",
        },
        {
            "amount": 500,
            "category": "Food",
            "description": "Groceries",
            "transaction_date": "2026-10-21",
            "transaction_type": "expense",
        },
        {
            "amount": 200,
            "category": "Transport",
            "description": "Taxi",
            "transaction_date": "2026-10-22",
            "transaction_type": "expense",
        },
    ]

    for transaction in transactions:
        response = client.post("/transactions", json=transaction)
        assert response.status_code == 201

    response = client.get(
        "/transactions",
        params={"transaction_type": "expense"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(
        transaction["transaction_type"] == "expense"
        for transaction in response.json()
    )


def test_filter_transactions_by_date_range(client):
    transactions = [
        {
            "amount": 100,
            "category": "Food",
            "description": "Before period",
            "transaction_date": "2026-10-19",
            "transaction_type": "expense",
        },
        {
            "amount": 200,
            "category": "Food",
            "description": "Period start",
            "transaction_date": "2026-10-20",
            "transaction_type": "expense",
        },
        {
            "amount": 300,
            "category": "Transport",
            "description": "Period end",
            "transaction_date": "2026-10-25",
            "transaction_type": "expense",
        },
        {
            "amount": 400,
            "category": "Food",
            "description": "After period",
            "transaction_date": "2026-10-26",
            "transaction_type": "expense",
        },
    ]

    for transaction in transactions:
        response = client.post("/transactions", json=transaction)
        assert response.status_code == 201

    response = client.get(
        "/transactions",
        params={
            "date_from": "2026-10-20",
            "date_to": "2026-10-25",
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert len(result) == 2
    assert {item["description"] for item in result} == {
        "Period start",
        "Period end",
    }


def test_summary_report(client):
    transactions = [
        {
            "amount": 3000,
            "category": "Salary",
            "description": "Monthly salary",
            "transaction_date": "2026-10-20",
            "transaction_type": "income",
        },
        {
            "amount": 500,
            "category": "Food",
            "description": "Groceries",
            "transaction_date": "2026-10-21",
            "transaction_type": "expense",
        },
        {
            "amount": 200,
            "category": "Transport",
            "description": "Taxi",
            "transaction_date": "2026-10-22",
            "transaction_type": "expense",
        },
        {
            "amount": 1000,
            "category": "Salary",
            "description": "Outside period",
            "transaction_date": "2026-11-01",
            "transaction_type": "income",
        },
    ]

    for transaction in transactions:
        response = client.post("/transactions", json=transaction)
        assert response.status_code == 201

    response = client.get(
        "/reports/summary",
        params={
            "date_from": "2026-10-20",
            "date_to": "2026-10-31",
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert float(result["total_income"]) == 3000.0
    assert float(result["total_expenses"]) == 700.0
    assert float(result["balance"]) == 2300.0



def test_summary_rejects_invalid_date_range(client):
    response = client.get(
        "/reports/summary",
        params={
            "date_from": "2026-10-31",
            "date_to": "2026-10-20",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "date_from must not be later than date_to"
    )


def test_filter_rejects_invalid_transaction_type(client):
    response = client.get(
        "/transactions",
        params={"transaction_type": "gift"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "transaction_type must be income or expense"
    )



def test_update_missing_transaction_returns_404(client):
    response = client.patch(
        "/transactions/999",
        json={"amount": 150},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"



def test_reject_category_with_only_spaces(client):
    response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "   ",
            "description": "Test",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 422


def test_category_whitespace_is_stripped(client):
    response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "  Food  ",
            "description": "Lunch",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 201
    assert response.json()["category"] == "Food"



def test_update_rejects_category_with_only_spaces(client):
    create_response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "Food",
            "description": "Lunch",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    update_response = client.patch(
        f"/transactions/{transaction_id}",
        json={"category": "   "},
    )

    assert update_response.status_code == 422



def test_reject_description_with_only_spaces(client):
    response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "Food",
            "description": "   ",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 422


def test_description_whitespace_is_stripped(client):
    response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "Food",
            "description": "  Lunch  ",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] == "Lunch"



def test_update_rejects_description_with_only_spaces(client):
    create_response = client.post(
        "/transactions",
        json={
            "amount": 100,
            "category": "Food",
            "description": "Lunch",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    update_response = client.patch(
        f"/transactions/{transaction_id}",
        json={"description": "   "},
    )

    assert update_response.status_code == 422



def test_reject_amount_with_more_than_two_decimal_places(client):
    response = client.post(
        "/transactions",
        json={
            "amount": "10.999",
            "category": "Food",
            "description": "Test amount precision",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )

    assert response.status_code == 422



def test_reject_amount_exceeding_max_digits(client):
    response = client.post(
        "/transactions",
        json={
            "amount": "100000000.00",
            "category": "Salary",
            "description": "Amount exceeds allowed maximum",
            "transaction_date": "2026-10-27",
            "transaction_type": "income",
        },
    )

    assert response.status_code == 422
