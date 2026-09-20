from unittest.mock import AsyncMock, patch
from app.timeutil import athens_now


def _today() -> str:
    return athens_now().date().isoformat()


def _today_noon() -> str:
    return athens_now().replace(hour=12, minute=0, second=0, microsecond=0).isoformat()


async def _auth(client, email="user@example.com"):
    response = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "secret123", "name": "User"},
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def test_expense_crud(client):
    headers = await _auth(client, "exp@example.com")
    created = await client.post(
        "/api/expenses",
        headers=headers,
        json={
            "amount_cents": 2500,
            "category": "software",
            "description": "GitHub",
            "date": "2026-09-01",
        },
    )
    assert created.status_code == 200
    expense_id = created.json()["id"]

    listed = await client.get("/api/expenses", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["amount_cents"] == 2500

    deleted = await client.delete(f"/api/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 200
    assert (await client.get("/api/expenses", headers=headers)).json() == []


async def test_expense_rejects_invalid_date(client):
    headers = await _auth(client, "baddate@example.com")
    created = await client.post(
        "/api/expenses",
        headers=headers,
        json={
            "amount_cents": 2500,
            "category": "software",
            "description": "GitHub",
            "date": "not-a-date",
        },
    )
    assert created.status_code == 422


async def test_dashboard_empty(client):
    headers = await _auth(client, "dash@example.com")
    response = await client.get("/api/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["invoiced_cents"] == 0
    assert body["vat_cents"] == 0
    assert body["social_security_cents"] == 26_077
    assert body["net_cents"] == -26_077
    assert "accountant" in body["disclaimer"].lower()
    assert "stripe" in body["missing_processors"]


async def test_connection_create_and_list(client):
    headers = await _auth(client, "conn@example.com")
    with patch("app.routers.connections_router.validate_stripe_key"), patch(
        "app.routers.connections_router.sync_connection",
        new_callable=AsyncMock,
        return_value=0,
    ):
        created = await client.post(
            "/api/connections",
            headers=headers,
            json={"processor": "stripe", "api_key": "sk_test_12345678", "label": "Main"},
        )
    assert created.status_code == 200
    listed = await client.get("/api/connections", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["processor"] == "stripe"
    assert "api_key" not in listed.json()[0]


async def test_connection_create_triggers_stripe_sync(client):
    headers = await _auth(client, "autosync@example.com")
    with patch("app.routers.connections_router.validate_stripe_key"), patch(
        "app.routers.connections_router.sync_connection",
        new_callable=AsyncMock,
        return_value=2,
    ) as sync_mock:
        created = await client.post(
            "/api/connections",
            headers=headers,
            json={"processor": "stripe", "api_key": "sk_test_12345678", "label": "Main"},
        )
    assert created.status_code == 200
    sync_mock.assert_awaited_once()


async def test_delete_connection_removes_its_transactions(client, db):
    headers = await _auth(client, "delconn@example.com")
    me = (await client.get("/api/auth/me", headers=headers)).json()
    with patch("app.routers.connections_router.validate_stripe_key"), patch(
        "app.routers.connections_router.sync_connection",
        new_callable=AsyncMock,
        return_value=0,
    ):
        created = await client.post(
            "/api/connections",
            headers=headers,
            json={"processor": "stripe", "api_key": "sk_test_12345678", "label": "Main"},
        )
    conn_id = created.json()["id"]
    today = _today_noon()
    await db.execute(
        """
        INSERT INTO transactions (
            connection_id, user_id, processor_txn_id, amount_cents, fee_cents, net_cents, txn_timestamp
        ) VALUES (?, ?, 'del-txn', 500000, 0, 500000, ?)
        """,
        (conn_id, me["id"], today),
    )
    await db.commit()
    before = (await client.get("/api/dashboard", headers=headers)).json()
    assert before["invoiced_cents"] == 500_000
    deleted = await client.delete(f"/api/connections/{conn_id}", headers=headers)
    assert deleted.status_code == 200
    after = (await client.get("/api/dashboard", headers=headers)).json()
    assert after["invoiced_cents"] == 0


async def test_benchmarks_require_auth(client):
    assert (await client.get("/api/benchmarks")).status_code in (401, 403)
    headers = await _auth(client, "bench@example.com")
    response = await client.get("/api/benchmarks", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["profession"]


async def test_monthly_report(client):
    headers = await _auth(client, "rep@example.com")
    response = await client.get("/api/reports/monthly", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_monthly_report_includes_efka_and_does_not_clamp_negative_net(client):
    headers = await _auth(client, "rep-tax@example.com")
    today = _today()
    created = await client.post(
        "/api/expenses",
        headers=headers,
        json={
            "amount_cents": 5000,
            "category": "software",
            "description": "Tools",
            "date": today,
        },
    )
    assert created.status_code == 200
    response = await client.get("/api/reports/monthly", headers=headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["expenses_cents"] == 5000
    assert rows[0]["vat_cents"] == 0
    assert rows[0]["social_security_cents"] == 26_077
    assert rows[0]["net_cents"] == -31_077


async def test_dashboard_includes_current_month_expense(client):
    headers = await _auth(client, "seed@example.com")
    me = (await client.get("/api/auth/me", headers=headers)).json()
    today = _today()
    created = await client.post(
        "/api/expenses",
        headers=headers,
        json={
            "amount_cents": 5000,
            "category": "software",
            "description": "Tools",
            "date": today,
        },
    )
    assert created.status_code == 200
    response = await client.get("/api/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["expenses_cents"] == 5000
    assert me["email"] == "seed@example.com"


async def test_update_efka_category_changes_dashboard(client):
    headers = await _auth(client, "efka@example.com")
    updated = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={"efka_category": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["efka_category"] == 3
    dash = await client.get("/api/dashboard", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["social_security_cents"] == 37_063


async def _seed_income(db, user_id: int, amount_cents: int = 500_000) -> None:
    today = _today_noon()
    cursor = await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) VALUES (?, 'stripe', 'seed', 'enc')",
        (user_id,),
    )
    await db.commit()
    await db.execute(
        """
        INSERT INTO transactions (
            connection_id, user_id, processor_txn_id, amount_cents, fee_cents, net_cents, txn_timestamp
        ) VALUES (?, ?, 'seed-txn', ?, 0, ?, ?)
        """,
        (cursor.lastrowid, user_id, amount_cents, amount_cents, today),
    )
    await db.commit()


async def test_update_years_active_changes_prepayment(client, db):
    headers = await _auth(client, "years@example.com")
    me = (await client.get("/api/auth/me", headers=headers)).json()
    await _seed_income(db, me["id"])
    first = (await client.get("/api/dashboard", headers=headers)).json()
    assert first["income_tax_cents"] > 0
    first_prepay = first["tax_prepayment_cents"]

    updated = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={"years_active": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["years_active"] == 3
    later = (await client.get("/api/dashboard", headers=headers)).json()
    assert later["income_tax_cents"] == first["income_tax_cents"]
    assert later["tax_prepayment_cents"] > first_prepay


async def test_dashboard_hourly_uses_hours_query(client):
    headers = await _auth(client, "hours@example.com")
    response = await client.get("/api/dashboard", headers=headers, params={"hours": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["effective_hourly_cents"] == round(body["net_cents"] / 10)


async def test_dashboard_requires_bearer_token(client):
    response = await client.get("/api/dashboard")
    assert response.status_code == 401


async def test_charges_vat_reduces_dashboard_net(client, db):
    headers = await _auth(client, "vat@example.com")
    me = (await client.get("/api/auth/me", headers=headers)).json()
    await _seed_income(db, me["id"], 124_000)
    before = (await client.get("/api/dashboard", headers=headers)).json()
    assert before["vat_cents"] == 0
    updated = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={"charges_vat": True},
    )
    assert updated.status_code == 200
    assert updated.json()["charges_vat"] is True
    after = (await client.get("/api/dashboard", headers=headers)).json()
    assert after["vat_cents"] == 24_000
    assert after["net_cents"] < before["net_cents"]
    report = (await client.get("/api/reports/monthly", headers=headers)).json()
    assert report[0]["vat_cents"] == 24_000


async def test_dashboard_includes_recurring_expense_from_prior_month(client):
    from datetime import timedelta

    headers = await _auth(client, "recur@example.com")
    start = athens_now().date().replace(day=1)
    prior = (start - timedelta(days=30)).isoformat()
    created = await client.post(
        "/api/expenses",
        headers=headers,
        json={
            "amount_cents": 2500,
            "category": "software",
            "description": "GitHub",
            "date": prior,
            "recurring": True,
            "interval_days": 30,
        },
    )
    assert created.status_code == 200
    dash = await client.get("/api/dashboard", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["expenses_cents"] == 2500
