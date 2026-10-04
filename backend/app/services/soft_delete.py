"""Soft delete / restore for expenses and connections (see docs/soft-deletes.md).

A row with deleted_at NULL is live. Deleting sets deleted_at to a UTC
"YYYY-MM-DD HH:MM:SS" string (SQLite datetime('now')). Every function here runs its
statements in one transaction and commits at the end.
"""


async def _now(db) -> str:
    cursor = await db.execute("SELECT datetime('now')")
    return (await cursor.fetchone())[0]


async def soft_delete_expense(db, expense_id: int, user_id: int) -> bool:
    deleted_at = await _now(db)
    cursor = await db.execute(
        "UPDATE expenses SET deleted_at = ? WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (deleted_at, expense_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def restore_expense(db, expense_id: int, user_id: int) -> bool:
    cursor = await db.execute(
        "UPDATE expenses SET deleted_at = NULL "
        "WHERE id = ? AND user_id = ? AND deleted_at IS NOT NULL",
        (expense_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def soft_delete_connection(db, connection_id: int, user_id: int) -> bool:
    """Soft-delete a live connection and its live transactions with ONE timestamp,
    so restore can tell cascade-deleted transactions from independently deleted ones."""
    deleted_at = await _now(db)
    try:
        cursor = await db.execute(
            "UPDATE connections SET deleted_at = ? "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (deleted_at, connection_id, user_id),
        )
        if cursor.rowcount == 0:
            await db.rollback()
            return False
        await db.execute(
            "UPDATE transactions SET deleted_at = ? "
            "WHERE connection_id = ? AND user_id = ? AND deleted_at IS NULL",
            (deleted_at, connection_id, user_id),
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return True


async def restore_connection(db, connection_id: int, user_id: int) -> bool:
    """Restore a soft-deleted connection plus the transactions that were deleted with
    it (same deleted_at). Transactions deleted at another time stay deleted."""
    try:
        cursor = await db.execute(
            "SELECT deleted_at FROM connections "
            "WHERE id = ? AND user_id = ? AND deleted_at IS NOT NULL",
            (connection_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return False
        deleted_at = row[0]
        await db.execute(
            "UPDATE transactions SET deleted_at = NULL "
            "WHERE connection_id = ? AND user_id = ? AND deleted_at = ?",
            (connection_id, user_id, deleted_at),
        )
        await db.execute(
            "UPDATE connections SET deleted_at = NULL WHERE id = ? AND user_id = ?",
            (connection_id, user_id),
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return True
