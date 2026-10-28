
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.security import get_current_user

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
assert get_current_user not in app.dependency_overrides


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/register",
            json={
                "email": "pytest@example.com",
                "password": "TestPassword123",
            },
        )
        assert response.status_code == 201

        login_response = test_client.post(
            "/auth/login",
            json={
                "email": "pytest@example.com",
                "password": "TestPassword123",
            },
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        test_client.headers.update(
            {"Authorization": f"Bearer {token}"}
        )

        yield test_client

    Base.metadata.drop_all(bind=test_engine)


def test_create_transaction_unauthorized(client):
    client.headers.pop("Authorization", None)

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

    assert response.status_code == 401


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



def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "newuser@example.com"
    assert "hashed_password" not in response.json()



def test_login_user(client):
    client.post(
        "/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "TestPassword123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"



def test_user_cannot_access_another_users_transaction(client):
    # Створюємо транзакцію першого користувача
    transaction_response = client.post(
        "/transactions/",
        json={
            "amount": 150,
            "category": "Food",
            "description": "Private expense",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )
    assert transaction_response.status_code == 201

    transaction_id = transaction_response.json()["id"]

    # Реєструємо другого користувача
    register_response = client.post(
        "/auth/register",
        json={
            "email": "second@example.com",
            "password": "SecondPassword123",
        },
    )
    assert register_response.status_code == 201

    # Авторизуємо другого користувача
    login_response = client.post(
        "/auth/login",
        json={
            "email": "second@example.com",
            "password": "SecondPassword123",
        },
    )
    assert login_response.status_code == 200

    second_token = login_response.json()["access_token"]

    # Другий користувач намагається отримати чужу транзакцію
    response = client.get(
        f"/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 404



def test_user_cannot_update_another_users_transaction(client):
    transaction_response = client.post(
        "/transactions/",
        json={
            "amount": 150,
            "category": "Food",
            "description": "Private expense",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )
    assert transaction_response.status_code == 201
    transaction_id = transaction_response.json()["id"]

    client.post(
        "/auth/register",
        json={
            "email": "update_test@example.com",
            "password": "TestPassword123",
        },
    )
    login_response = client.post(
        "/auth/login",
        json={
            "email": "update_test@example.com",
            "password": "TestPassword123",
        },
    )
    assert login_response.status_code == 200

    second_token = login_response.json()["access_token"]

    response = client.patch(
        f"/transactions/{transaction_id}",
        json={"description": "Hacked expense"},
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 404


def test_user_cannot_delete_another_users_transaction(client):
    transaction_response = client.post(
        "/transactions/",
        json={
            "amount": 150,
            "category": "Food",
            "description": "Private expense",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )
    assert transaction_response.status_code == 201
    transaction_id = transaction_response.json()["id"]

    client.post(
        "/auth/register",
        json={
            "email": "delete_test@example.com",
            "password": "TestPassword123",
        },
    )
    login_response = client.post(
        "/auth/login",
        json={
            "email": "delete_test@example.com",
            "password": "TestPassword123",
        },
    )
    assert login_response.status_code == 200

    second_token = login_response.json()["access_token"]

    response = client.delete(
        f"/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 404



def test_user_sees_only_own_transactions(client):
    # Перший користувач створює транзакцію
    transaction_response = client.post(
        "/transactions/",
        json={
            "amount": 150,
            "category": "Food",
            "description": "First user's expense",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )
    assert transaction_response.status_code == 201

    # Реєструємо другого користувача
    register_response = client.post(
        "/auth/register",
        json={
            "email": "list_test@example.com",
            "password": "TestPassword123",
        },
    )
    assert register_response.status_code == 201

    # Входимо під другим користувачем
    login_response = client.post(
        "/auth/login",
        json={
            "email": "list_test@example.com",
            "password": "TestPassword123",
        },
    )
    assert login_response.status_code == 200

    second_token = login_response.json()["access_token"]

    # Отримуємо список транзакцій другого користувача
    response = client.get(
        "/transactions/",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []



def test_summary_contains_only_current_users_transactions(client):
    # Перший користувач створює витрату
    transaction_response = client.post(
        "/transactions/",
        json={
            "amount": 150,
            "category": "Food",
            "description": "First user's expense",
            "transaction_date": "2026-10-27",
            "transaction_type": "expense",
        },
    )
    assert transaction_response.status_code == 201

    # Реєструємо другого користувача
    register_response = client.post(
        "/auth/register",
        json={
            "email": "summary_test@example.com",
            "password": "TestPassword123",
        },
    )
    assert register_response.status_code == 201

    # Авторизуємо другого користувача
    login_response = client.post(
        "/auth/login",
        json={
            "email": "summary_test@example.com",
            "password": "TestPassword123",
        },
    )
    assert login_response.status_code == 200

    second_token = login_response.json()["access_token"]

    # Другий користувач отримує власний звіт

    response = client.get(
        "/reports/summary",
        params={
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
        },

        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total_expenses"] == 0

def test_get_db_closes_session():
    from unittest.mock import MagicMock, patch

    with patch("app.database.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        generator = get_db()
        db = next(generator)

        assert db is mock_db

        generator.close()

        mock_db.close.assert_called_once()


def test_login_user_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "TestPassword123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_invalid_token_returns_401(client):
    client.headers["Authorization"] = "Bearer invalid-token"

    response = client.get("/transactions")

    assert response.status_code == 401

def test_token_without_subject_returns_401(client):
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.security import ALGORITHM, SECRET_KEY

    token = jwt.encode(
        {
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"
    response = client.get("/transactions")

    assert response.status_code == 401

def test_token_for_nonexistent_user_returns_401(client):
    from app.security import create_access_token

    token = create_access_token("missing-user@example.com")
    client.headers["Authorization"] = f"Bearer {token}"

    response = client.get("/transactions")

    assert response.status_code == 401

def test_get_transactions_pagination(client):
    for i in range(3):
        response = client.post(
            "/transactions",
            json={
                "amount": 100 + i,
                "category": "Food",
                "description": f"Transaction {i}",
                "transaction_date": "2026-10-27",
                "transaction_type": "expense",
            },
        )
        assert response.status_code == 201

    response = client.get("/transactions?limit=2&offset=1")

    assert response.status_code == 200
    assert len(response.json()) == 2

def test_login_for_swagger(client):
    response = client.post(
        "/auth/token",
        data={
            "username": "pytest@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_for_swagger_wrong_password(client):
    response = client.post(
        "/auth/token",
        data={
            "username": "pytest@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"