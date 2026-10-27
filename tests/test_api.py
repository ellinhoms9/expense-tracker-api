
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
