"""Demo scenarios that exercise the database layer and print the results."""

import secrets
from decimal import Decimal

from finance_db import db


def section(title):
    # Small visual separator between demo steps.
    print()
    print(title)
    print("-" * len(title))


def main():
    # Random suffix lets the demo run repeatedly without duplicate emails.
    suffix = secrets.token_hex(3)

    section("Create users")
    alice = db.create_user(
        "Alice Example", f"alice-{suffix}@example.com", "password123"
    )
    bob = db.create_user(
        "Bob Example", f"bob-{suffix}@example.com", "password123"
    )
    print(f"  created {alice['email']} and {bob['email']}")

    section("Reject duplicate email")
    try:
        db.create_user("Alice Again", alice["email"], "password123")
    except ValueError as exc:
        print(f"  rejected: {exc}")

    section("Create accounts and move money")
    alice_account = db.create_account(alice["id"], "Checking")
    bob_account = db.create_account(bob["id"], "Checking")
    print(f"  after deposit: {db.deposit(alice_account['id'], '100.00', 'Opening deposit')}")
    print(f"  after withdrawal: {db.withdraw(alice_account['id'], '30.00', 'Groceries')}")
    db.transfer(alice_account["id"], bob_account["id"], "40.00", "Shared lunch")
    alice_balance = db.get_account(alice_account["id"])["balance"]
    bob_balance = db.get_account(bob_account["id"])["balance"]
    print(f"  after transfer: alice={alice_balance} bob={bob_balance}")

    # The failed transfer must leave both balances exactly as they were.
    section("Reject overdraft transfer (rollback)")
    try:
        db.transfer(alice_account["id"], bob_account["id"], "1000.00", "Too much")
    except ValueError as exc:
        print(f"  rejected: {exc}")
    alice_balance = db.get_account(alice_account["id"])["balance"]
    bob_balance = db.get_account(bob_account["id"])["balance"]
    print(f"  balances unchanged: alice={alice_balance} bob={bob_balance}")

    section("Add expenses")
    categories = {row["name"]: row["id"] for row in db.list_categories()}
    db.add_expense(alice_account["id"], categories["Food"], "12.50", "Lunch")
    db.add_expense(alice_account["id"], categories["Transport"], "5.75", "Bus")
    print(f"  alice balance: {db.get_account(alice_account['id'])['balance']}")

    section("Monthly spending by category")
    for row in db.monthly_spending(alice["id"]):
        print(f"  {row['month']} {row['category']}: {row['total']}")

    section("Alice transaction history")
    for txn in db.get_transactions(alice_account["id"]):
        category = txn["category"] or "-"
        print(
            f"  {txn['occurred_at']:%Y-%m-%d %H:%M} "
            f"{txn['kind']:<12} {txn['amount']:>8} "
            f"{category:<13} {txn['description'] or ''}"
        )

    # Difference is nonzero if a balance and its ledger rows disagree.
    section("Reconciliation (cached vs computed)")
    total_difference = Decimal("0")
    for row in db.reconciliation_check():
        total_difference += abs(row["difference"])
        print(
            f"  account {row['account_id']}: "
            f"cached={row['cached_balance']} "
            f"computed={row['calculated_balance']} "
            f"diff={row['difference']}"
        )
    print(f"  total absolute difference: {total_difference}")


if __name__ == "__main__":
    main()
