"""Tests assume schema.sql has been applied and the database is running."""

from decimal import Decimal

import pytest

from finance_db import db


@pytest.fixture(autouse=True)
def clean_database():
    # Every test starts from the same empty tables and seeded categories.
    with db.get_connection() as conn:
        conn.execute(
            """
            TRUNCATE transactions, accounts, categories, users
            RESTART IDENTITY CASCADE
            """
        )
        conn.execute(
            """
            INSERT INTO categories (name)
            VALUES ('Food'), ('Transport'), ('Entertainment'), ('Rent'), ('Utilities')
            """
        )
    yield


def make_account(email="alice@example.com"):
    # Convenience helper: one user with one checking account.
    user = db.create_user("Alice Example", email, "password123")
    account = db.create_account(user["id"], "Checking")
    return user, account


def test_duplicate_email_is_rejected():
    db.create_user("Alice Example", "alice@example.com", "password123")
    with pytest.raises(ValueError, match="already registered"):
        db.create_user("Alice Two", "alice@example.com", "password123")


def test_deposit_and_withdraw():
    _, account = make_account()
    assert db.deposit(account["id"], "100.00") == Decimal("100.00")
    assert db.withdraw(account["id"], "40.00") == Decimal("60.00")


def test_insufficient_funds_leaves_balance_untouched():
    _, account = make_account()
    db.deposit(account["id"], "10.00")
    with pytest.raises(ValueError, match="insufficient funds"):
        db.withdraw(account["id"], "11.00")
    assert db.get_account(account["id"])["balance"] == Decimal("10.00")


def test_transfer_is_atomic():
    _, alice_account = make_account("alice@example.com")
    _, bob_account = make_account("bob@example.com")
    db.deposit(alice_account["id"], "100.00")

    db.transfer(alice_account["id"], bob_account["id"], "30.00")
    assert db.get_account(alice_account["id"])["balance"] == Decimal("70.00")
    assert db.get_account(bob_account["id"])["balance"] == Decimal("30.00")

    with pytest.raises(ValueError, match="insufficient funds"):
        db.transfer(alice_account["id"], bob_account["id"], "1000.00")
    assert db.get_account(alice_account["id"])["balance"] == Decimal("70.00")
    assert db.get_account(bob_account["id"])["balance"] == Decimal("30.00")


def test_expense_requires_a_category():
    _, account = make_account()
    db.deposit(account["id"], "50.00")
    with pytest.raises(ValueError, match="requires a category"):
        db.add_expense(account["id"], None, "5.00")


def test_reconciliation_matches_after_operations():
    user, alice_account = make_account("alice@example.com")
    _, bob_account = make_account("bob@example.com")
    categories = {row["name"]: row["id"] for row in db.list_categories()}

    db.deposit(alice_account["id"], "100.00")
    db.withdraw(alice_account["id"], "20.00")
    db.transfer(alice_account["id"], bob_account["id"], "30.00")
    db.add_expense(alice_account["id"], categories["Food"], "12.50")

    rows = db.reconciliation_check()
    total_difference = sum(abs(row["difference"]) for row in rows)
    assert total_difference == Decimal("0")
