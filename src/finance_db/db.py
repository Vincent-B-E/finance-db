"""Database access for the finance demo.

Plain parameterized SQL with psycopg 3. Every public operation runs in a
single transaction, so callers never see a half-applied change.
"""

import hashlib
import os
import secrets
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

# Override DATABASE_URL to point the demo at another database.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/finance",
)

# All money is quantized to two decimal places.
MONEY = Decimal("0.01")


def get_connection() -> Connection[dict[str, Any]]:
    # cast: psycopg's stubs fix the row type at tuple, but dict_row returns dicts.
    return cast(
        Connection[dict[str, Any]],
        psycopg.connect(DATABASE_URL, row_factory=dict_row),  # type: ignore
    )


def hash_password(password):
    # Random salt per password; salt and derived key are stored together.
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )
    return f"scrypt${salt.hex()}${key.hex()}"


def verify_password(password, stored_hash):
    # Recompute the key with the stored salt and compare in constant time.
    _, salt_hex, key_hex = stored_hash.split("$")
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return secrets.compare_digest(key.hex(), key_hex)


def _money(value):
    # Convert safely to Decimal so floats never touch money arithmetic.
    return Decimal(str(value)).quantize(MONEY)


def _positive_amount(value):
    amount = _money(value)
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    return amount


def create_user(name, email, password):
    # Validate first so the caller gets a friendly error, not a raw DB error.
    name = name.strip()
    email = email.strip().lower()
    if len(name) < 3:
        raise ValueError("name must be at least 3 characters")
    if "@" not in email:
        raise ValueError("email must contain @")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    try:
        with get_connection() as conn:
            # RETURNING returns the new row without a second query.
            row = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, name, email, created_at
                """,
                (name, email, hash_password(password)),
            ).fetchone()
            assert row is not None
            return row
    except psycopg.errors.UniqueViolation:
        # Translate the constraint error into a message the demo can print.
        raise ValueError(f"email already registered: {email}") from None


def create_account(user_id, name):
    name = name.strip()
    if not name:
        raise ValueError("account name is required")
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO accounts (user_id, name)
                VALUES (%s, %s)
                RETURNING id, user_id, name, balance, created_at
                """,
                (user_id, name),
            ).fetchone()
            assert row is not None
            return row
    except psycopg.errors.ForeignKeyViolation:
        raise ValueError(f"user {user_id} does not exist") from None
    except psycopg.errors.UniqueViolation:
        raise ValueError(f"user {user_id} already has an account named {name!r}") from None


def deposit(account_id, amount, description=None):
    amount = _positive_amount(amount)
    with get_connection() as conn:
        # Balance update and ledger row commit together on block exit.
        row = conn.execute(
            """
            UPDATE accounts
            SET balance = balance + %s
            WHERE id = %s
            RETURNING balance
            """,
            (amount, account_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"account {account_id} does not exist")
        conn.execute(
            """
            INSERT INTO transactions (account_id, kind, amount, description)
            VALUES (%s, 'deposit', %s, %s)
            """,
            (account_id, amount, description),
        )
        return row["balance"]


def withdraw(account_id, amount, description=None):
    amount = _positive_amount(amount)
    with get_connection() as conn:
        # Lock the row so a concurrent withdrawal cannot spend the same money.
        account = conn.execute(
            "SELECT balance FROM accounts WHERE id = %s FOR UPDATE",
            (account_id,),
        ).fetchone()
        if account is None:
            raise ValueError(f"account {account_id} does not exist")
        if account["balance"] < amount:
            raise ValueError("insufficient funds")
        new_balance = account["balance"] - amount
        conn.execute(
            "UPDATE accounts SET balance = %s WHERE id = %s",
            (new_balance, account_id),
        )
        conn.execute(
            """
            INSERT INTO transactions (account_id, kind, amount, description)
            VALUES (%s, 'withdrawal', %s, %s)
            """,
            (account_id, amount, description),
        )
        return new_balance


def transfer(from_account_id, to_account_id, amount, description=None):
    amount = _positive_amount(amount)
    if from_account_id == to_account_id:
        raise ValueError("cannot transfer to the same account")
    # Lock rows in a stable order so opposite transfers cannot deadlock.
    first, second = sorted((from_account_id, to_account_id))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, balance
            FROM accounts
            WHERE id IN (%s, %s)
            ORDER BY id
            FOR UPDATE
            """,
            (first, second),
        ).fetchall()
        accounts = {row["id"]: row["balance"] for row in rows}
        if len(accounts) != 2:
            raise ValueError("one or both accounts do not exist")
        if accounts[from_account_id] < amount:
            raise ValueError("insufficient funds")
        conn.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id = %s",
            (amount, from_account_id),
        )
        conn.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (amount, to_account_id),
        )
        # Both ledger legs belong to the same transaction as the balance moves.
        conn.execute(
            """
            INSERT INTO transactions (account_id, kind, amount, description)
            VALUES (%s, 'transfer_out', %s, %s)
            """,
            (from_account_id, amount, description),
        )
        conn.execute(
            """
            INSERT INTO transactions (account_id, kind, amount, description)
            VALUES (%s, 'transfer_in', %s, %s)
            """,
            (to_account_id, amount, description),
        )


UNCATEGORIZED = "Uncategorized"


def _resolve_category_id(conn, category_id):
    if category_id is not None:
        return category_id
    # "No category picked" becomes an explicit bucket, not NULL.
    row = conn.execute(
        "SELECT id FROM categories WHERE name = %s",
        (UNCATEGORIZED,),
    ).fetchone()
    if row is None:
        raise ValueError(f"category {UNCATEGORIZED!r} is missing; apply seed.sql")
    return row["id"]


def add_expense(account_id, category_id, amount, description=None):
    amount = _positive_amount(amount)
    try:
        with get_connection() as conn:
            category_id = _resolve_category_id(conn, category_id)
            account = conn.execute(
                "SELECT balance FROM accounts WHERE id = %s FOR UPDATE",
                (account_id,),
            ).fetchone()
            if account is None:
                raise ValueError(f"account {account_id} does not exist")
            if account["balance"] < amount:
                raise ValueError("insufficient funds")
            conn.execute(
                "UPDATE accounts SET balance = balance - %s WHERE id = %s",
                (amount, account_id),
            )
            conn.execute(
                """
                INSERT INTO transactions
                    (account_id, category_id, kind, amount, description)
                VALUES (%s, %s, 'expense', %s, %s)
                """,
                (account_id, category_id, amount, description),
            )
            return account["balance"] - amount
    except psycopg.errors.ForeignKeyViolation:
        raise ValueError(f"category {category_id} does not exist") from None


def get_account(account_id):
    with get_connection() as conn:
        account = conn.execute(
            """
            SELECT id, user_id, name, balance, created_at
            FROM accounts
            WHERE id = %s
            """,
            (account_id,),
        ).fetchone()
    if account is None:
        raise ValueError(f"account {account_id} does not exist")
    return account


def get_transactions(account_id, limit=20):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT t.id, t.kind, t.amount, c.name AS category,
                   t.description, t.occurred_at
            FROM transactions AS t
            LEFT JOIN categories AS c ON c.id = t.category_id
            WHERE t.account_id = %s
            ORDER BY t.occurred_at DESC, t.id DESC
            LIMIT %s
            """,
            (account_id, limit),
        ).fetchall()


def list_categories():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name 
            FROM categories 
            ORDER BY name
            """
        ).fetchall()


def monthly_spending(user_id):
    # The view does the aggregation; this just filters by owner.
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT month, category, total
            FROM monthly_spending_by_category
            WHERE user_id = %s
            ORDER BY month DESC, total DESC
            """,
            (user_id,),
        ).fetchall()


def reconciliation_check():
    # difference is 0.00 when cached balances match the ledger.
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * 
            FROM account_reconciliation 
            ORDER BY account_id
            """
        ).fetchall()