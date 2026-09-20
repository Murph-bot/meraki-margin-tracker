from app.services.sync_service import record_daily_snapshots
from app.timeutil import athens_now


async def test_record_daily_snapshots_writes_month_margin(db):
    await db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        ("snap@example.com", "hash", "Snap"),
    )
    await db.commit()
    user_id = (await (await db.execute("SELECT id FROM users")).fetchone())["id"]
    today = athens_now().replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
    cursor = await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) VALUES (?, 'stripe', 'seed', 'enc')",
        (user_id,),
    )
    await db.commit()
    await db.execute(
        """
        INSERT INTO transactions (
            connection_id, user_id, processor_txn_id, amount_cents, fee_cents, net_cents, txn_timestamp
        ) VALUES (?, ?, 'snap-txn', 500000, 0, 500000, ?)
        """,
        (cursor.lastrowid, user_id, today),
    )
    await db.commit()

    await record_daily_snapshots(db)
    await record_daily_snapshots(db)

    rows = await (await db.execute("SELECT * FROM margin_snapshots WHERE user_id = ?", (user_id,))).fetchall()
    assert len(rows) == 1
    assert rows[0]["gross_cents"] == 500_000
    assert rows[0]["net_cents"] != 0
    assert rows[0]["date"] == athens_now().date().isoformat()
