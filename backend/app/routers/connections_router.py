import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import get_current_user
from app.crypto import encrypt_secret, decrypt_secret
from app.database import get_db
from app.services.stripe_adapter import validate_stripe_key, sync_connection
from app.services.viva_adapter import VivaNotImplementedError, sync_viva

router = APIRouter(prefix="/api/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    processor: str = Field(pattern="^(stripe|viva)$")
    api_key: str = Field(min_length=8)
    label: str = ""


class ConnectionResponse(BaseModel):
    id: int
    processor: str
    label: str
    last_synced_at: str | None


@router.get("")
async def list_connections(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT id, processor, label, last_synced_at FROM connections WHERE user_id = ? ORDER BY id",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [
        ConnectionResponse(
            id=row["id"],
            processor=row["processor"],
            label=row["label"],
            last_synced_at=row["last_synced_at"],
        )
        for row in rows
    ]


@router.post("")
async def create_connection(
    req: ConnectionCreate,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    if req.processor == "stripe":
        try:
            await asyncio.to_thread(validate_stripe_key, req.api_key)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Stripe key rejected: {exc}") from exc
    encrypted = encrypt_secret(req.api_key)
    cursor = await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) VALUES (?, ?, ?, ?)",
        (user_id, req.processor, req.label, encrypted),
    )
    connection_id = cursor.lastrowid
    await db.commit()
    last_synced_at = None
    if req.processor == "stripe":
        try:
            await sync_connection(db, connection_id, user_id, req.api_key)
            synced = await db.execute(
                "SELECT last_synced_at FROM connections WHERE id = ?",
                (connection_id,),
            )
            row = await synced.fetchone()
            last_synced_at = row["last_synced_at"] if row else None
        except Exception:
            last_synced_at = None
    return ConnectionResponse(
        id=connection_id,
        processor=req.processor,
        label=req.label,
        last_synced_at=last_synced_at,
    )


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    cursor = await db.execute(
        "SELECT id FROM connections WHERE id = ? AND user_id = ?",
        (connection_id, user_id),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.execute(
        "DELETE FROM transactions WHERE connection_id = ? AND user_id = ?",
        (connection_id, user_id),
    )
    await db.execute(
        "DELETE FROM connections WHERE id = ? AND user_id = ?",
        (connection_id, user_id),
    )
    await db.commit()
    return {"ok": True}


@router.post("/{connection_id}/sync")
async def trigger_sync(
    connection_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    cursor = await db.execute(
        "SELECT id, processor, api_key_encrypted FROM connections WHERE id = ? AND user_id = ?",
        (connection_id, user_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    api_key = decrypt_secret(row["api_key_encrypted"])
    if row["processor"] == "viva":
        try:
            inserted = await sync_viva(api_key)
        except VivaNotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
    else:
        inserted = await sync_connection(db, row["id"], user_id, api_key)
    return {"ok": True, "inserted": inserted}
