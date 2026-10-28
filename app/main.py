from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Transaction, User
from app.schemas import (
    LoginRequest,
    Token,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    UserCreate,
    UserResponse,
)
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


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


@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register_user(data: UserCreate, db: DbSession):
    normalized_email = str(data.email).lower()

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = User(
        email=normalized_email,
        hashed_password=hash_password(data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user



@app.post("/auth/login", response_model=Token)
def login_user(data: LoginRequest, db: DbSession):
    normalized_email = str(data.email).lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None or not verify_password(
        data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.post("/auth/token", response_model=Token)
def login_for_swagger(
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    normalized_email = form_data.username.lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.post("/transactions", response_model=TransactionResponse, status_code=201)
def create_transaction(
    data: TransactionCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
):
    transaction = Transaction(
        **data.model_dump(),
        user_id=current_user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction



@app.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Transaction)
    query = query.where(Transaction.user_id == current_user.id)

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

def get_transaction(
    transaction_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return transaction



@app.patch("/transactions/{transaction_id}", response_model=TransactionResponse)

def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

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

def delete_transaction(
    transaction_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    db.delete(transaction)
    db.commit()

    return Response(status_code=204)



@app.get("/reports/summary")

def get_summary(
    db: DbSession,
    date_from: date,
    date_to: date,
    current_user: Annotated[User, Depends(get_current_user)],
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
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= date_from,
        Transaction.transaction_date <= date_to,
    ).group_by(Transaction.transaction_type)

    totals = {
        transaction_type: Decimal(str(amount))
        for transaction_type, amount in db.execute(query).all()
    }

    income = totals.get("income", Decimal(0))
    expenses = totals.get("expense", Decimal(0))

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_income": income,
        "total_expenses": expenses,
        "balance": income - expenses,
    }
