from fastapi import APIRouter, Depends, Query
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
async def list_transactions(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    cursor = await db.execute(
        """
        SELECT id, connection_id, processor_txn_id, amount_cents, fee_cents, net_cents,
               currency, description, txn_timestamp
        FROM transactions
        WHERE user_id = ? AND deleted_at IS NULL
        ORDER BY txn_timestamp DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    return [dict(row) for row in await cursor.fetchall()]
