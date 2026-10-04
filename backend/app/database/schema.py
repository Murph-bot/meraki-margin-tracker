SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL DEFAULT '',
        vat_number TEXT DEFAULT '',
        tax_scale TEXT DEFAULT 'self_employed',
        efka_category INTEGER NOT NULL DEFAULT 1,
        years_active INTEGER NOT NULL DEFAULT 1,
        charges_vat INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );""",
    """CREATE TABLE IF NOT EXISTS connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        processor TEXT NOT NULL CHECK(processor IN ('stripe','viva')),
        label TEXT DEFAULT '',
        api_key_encrypted TEXT NOT NULL,
        last_synced_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        deleted_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );""",
    """CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        connection_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        processor_txn_id TEXT,
        amount_cents INTEGER NOT NULL,
        fee_cents INTEGER DEFAULT 0,
        net_cents INTEGER NOT NULL,
        currency TEXT DEFAULT 'EUR',
        description TEXT DEFAULT '',
        customer_name TEXT DEFAULT '',
        invoice_number TEXT DEFAULT '',
        txn_timestamp TEXT NOT NULL,
        synced_at TEXT DEFAULT (datetime('now')),
        deleted_at TEXT,
        FOREIGN KEY (connection_id) REFERENCES connections(id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE (connection_id, processor_txn_id)
    );""",
    """CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount_cents INTEGER NOT NULL,
        category TEXT DEFAULT 'other',
        description TEXT DEFAULT '',
        date TEXT NOT NULL,
        recurring INTEGER DEFAULT 0,
        interval_days INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        deleted_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );""",
    """CREATE TABLE IF NOT EXISTS margin_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        gross_cents INTEGER NOT NULL,
        fees_cents INTEGER DEFAULT 0,
        expenses_cents INTEGER DEFAULT 0,
        estimated_tax_cents INTEGER DEFAULT 0,
        social_security_cents INTEGER DEFAULT 0,
        net_cents INTEGER NOT NULL,
        effective_rate REAL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );""",
    """CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        connection_id INTEGER,
        status TEXT NOT NULL,
        message TEXT,
        run_at TEXT DEFAULT (datetime('now'))
    );""",
    "CREATE INDEX IF NOT EXISTS idx_transactions_user_ts ON transactions(user_id, txn_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)",
]

# Run by _apply_migrations, after deleted_at is guaranteed to exist (old databases
# only gain the column through ALTER TABLE, so these cannot live in SCHEMA).
SOFT_DELETE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_live ON expenses(user_id) WHERE deleted_at IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_connections_user_live ON connections(user_id) WHERE deleted_at IS NULL",
]
