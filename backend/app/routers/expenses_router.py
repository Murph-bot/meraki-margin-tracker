from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from datetime import date as date_cls
from app.auth import get_current_user
from app.database import get_db
from app.services.soft_delete import restore_expense, soft_delete_expense

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

ALLOWED_CATEGORIES = {
    "software",
    "hardware",
    "office",
    "travel",
    "professional_services",
    "other",
}


class ExpenseCreate(BaseModel):
    amount_cents: int = Field(gt=0)
    category: str = "other"
    description: str = ""
    date: str
    recurring: bool = False
    interval_days: int = 0

    @field_validator("date")
    @classmethod
    def date_is_iso(cls, value: str) -> str:
        date_cls.fromisoformat(value)
        return value


class ExpenseResponse(BaseModel):
    id: int
    amount_cents: int
    category: str
    description: str
    date: str
    recurring: bool
    interval_days: int


def _row_to_expense(row) -> ExpenseResponse:
    return ExpenseResponse(
        id=row["id"],
        amount_cents=row["amount_cents"],
        category=row["category"],
        description=row["description"],
        date=row["date"],
        recurring=bool(row["recurring"]),
        interval_days=row["interval_days"],
    )


@router.get("")
async def list_expenses(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT * FROM expenses WHERE user_id = ? AND deleted_at IS NULL ORDER BY date DESC, id DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_expense(row) for row in rows]


@router.post("")
async def create_expense(
    req: ExpenseCreate,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    category = req.category if req.category in ALLOWED_CATEGORIES else "other"
    cursor = await db.execute(
        """
        INSERT INTO expenses (user_id, amount_cents, category, description, date, recurring, interval_days)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            req.amount_cents,
            category,
            req.description,
            req.date,
            1 if req.recurring else 0,
            req.interval_days,
        ),
    )
    await db.commit()
    return ExpenseResponse(
        id=cursor.lastrowid,
        amount_cents=req.amount_cents,
        category=category,
        description=req.description,
        date=req.date,
        recurring=req.recurring,
        interval_days=req.interval_days,
    )


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    if not await soft_delete_expense(db, expense_id, user_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"ok": True}


@router.post("/{expense_id}/restore")
async def restore_expense_endpoint(
    expense_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    if not await restore_expense(db, expense_id, user_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"ok": True}
