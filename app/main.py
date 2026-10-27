from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Transaction
from app.schemas import TransactionCreate, TransactionResponse, TransactionUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Expense Tracker API",
    description="REST API for tracking personal finances",
    version="1.0.0",
    lifespan=lifespan,
)

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/")
def root():
    return {"message": "Expense Tracker API is running"}


@app.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=201,
)
def create_transaction(
    data: TransactionCreate,
    db: DbSession,
):
    transaction = Transaction(**data.model_dump())

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


@app.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Transaction)

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must not be later than date_to",
        )

    if date_from:
        query = query.where(
            Transaction.transaction_date >= date_from
        )

    if date_to:
        query = query.where(
            Transaction.transaction_date <= date_to
        )

    if category:
        query = query.where(Transaction.category == category)

    if transaction_type:
        if transaction_type not in ("income", "expense"):
            raise HTTPException(
                status_code=400,
                detail="transaction_type must be income or expense",
            )
        query = query.where(
            Transaction.transaction_type == transaction_type
        )

    query = (
        query
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )

    return db.scalars(query).all()


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: DbSession):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@app.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: DbSession,
):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    changes = data.model_dump(exclude_unset=True)

    if "amount" in changes and changes["amount"] is None:
        raise HTTPException(status_code=422, detail="Amount cannot be null")

    if "category" in changes and changes["category"] is None:
        raise HTTPException(status_code=422, detail="Category cannot be null")

    if "transaction_date" in changes and changes["transaction_date"] is None:
        raise HTTPException(status_code=422, detail="Date cannot be null")

    if "transaction_type" in changes and changes["transaction_type"] is None:
        raise HTTPException(status_code=422, detail="Type cannot be null")

    for field, value in changes.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)

    return transaction


@app.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: DbSession):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return Response(status_code=204)


@app.get("/reports/summary")
def get_summary(
    db: DbSession,
    date_from: date,
    date_to: date,
):
    if date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must not be later than date_to",
        )

    query = select(
        Transaction.transaction_type,
        func.coalesce(func.sum(Transaction.amount), 0),
    ).where(
        Transaction.transaction_date >= date_from,
        Transaction.transaction_date <= date_to,
    ).group_by(Transaction.transaction_type)

    totals = {
        transaction_type: Decimal(str(amount))
        for transaction_type, amount in db.execute(query).all()
    }

    income = totals.get("income", Decimal("0"))
    expenses = totals.get("expense", Decimal("0"))

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_income": income,
        "total_expenses": expenses,
        "balance": income - expenses,
    }