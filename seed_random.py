"""Populate the database with reproducible random demo data.

Examples:
    uv run python seed_random.py --reset
    uv run python seed_random.py --users 20 --transactions 120 --seed 7
"""

import argparse
import random
from decimal import Decimal

from finance_db import db

FIRST_NAMES = [
    "Ava", "Liam", "Mia", "Noah", "Zoe", "Elias", "Nora", "Hugo",
    "Lina", "Omar", "Sofia", "Kai", "Emma", "Jonas", "Maya", "Theo",
]
LAST_NAMES = [
    "Jansen", "Peeters", "Maes", "Willems", "Claes", "Goossens",
    "Wouters", "De Smet", "Vermeulen", "Lambert", "Dubois", "Moreau",
]
DEMO_PASSWORD = "password123"
CENT = Decimal("0.01")


def reset_data():
    # Remove generated rows but keep the reference categories.
    with db.get_connection() as conn:
        conn.execute(
            "TRUNCATE transactions, accounts, users RESTART IDENTITY CASCADE"
        )
        # Re-create categories if the schema was applied without seed.sql.
        conn.execute(
            """
            INSERT INTO categories (name)
            VALUES ('Food'), ('Transport'), ('Entertainment'), ('Rent'), ('Utilities')
            ON CONFLICT (name) DO NOTHING
            """
        )


def random_amount(rng, low, high):
    # Work in whole cents so the result is always a valid NUMERIC(12,2) value.
    cents = rng.randint(low * 100, high * 100)
    return (Decimal(cents) * CENT).quantize(CENT)


def create_users(rng, count):
    users = []
    for index in range(count):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        # The index keeps emails unique even when names repeat.
        email = f"{first.lower()}.{last.lower()}.{index}@example.com"
        user = db.create_user(f"{first} {last}", email, DEMO_PASSWORD)
        users.append(user)
    return users


def create_accounts(rng, users):
    accounts = []
    for user in users:
        # Everyone gets a checking account; some also get savings.
        names = ["Checking"]
        if rng.random() < 0.6:
            names.append("Savings")
        for name in names:
            account = db.create_account(user["id"], name)
            opening = random_amount(rng, 100, 1000)
            db.deposit(account["id"], opening, "Opening deposit")
            accounts.append(account)
    return accounts


def populate_transactions(rng, accounts, categories, count):
    stats = {
        "deposit": 0,
        "withdrawal": 0,
        "expense": 0,
        "transfer": 0,
        "skipped": 0,
    }
    for _ in range(count):
        account = rng.choice(accounts)
        # Weighted mix: mostly expenses, fewer transfers.
        action = rng.choices(
            ["deposit", "withdrawal", "expense", "transfer"],
            weights=[15, 20, 55, 10],
        )[0]
        try:
            if action == "deposit":
                db.deposit(
                    account["id"], random_amount(rng, 10, 200), "Random deposit"
                )
            elif action == "withdrawal":
                db.withdraw(
                    account["id"], random_amount(rng, 5, 100), "Random withdrawal"
                )
            elif action == "expense":
                category = rng.choice(categories)
                db.add_expense(
                    account["id"],
                    category["id"],
                    random_amount(rng, 5, 80),
                    f"Random {category['name'].lower()} expense",
                )
            else:
                candidates = [a for a in accounts if a["id"] != account["id"]]
                if not candidates:
                    stats["skipped"] += 1
                    continue
                other = rng.choice(candidates)
                db.transfer(
                    account["id"],
                    other["id"],
                    random_amount(rng, 5, 50),
                    "Random transfer",
                )
        except ValueError:
            # Not enough money for this random amount; try the next one.
            stats["skipped"] += 1
            continue
        stats[action] += 1
    return stats


def main():
    parser = argparse.ArgumentParser(description="Seed random finance data")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--transactions", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="clear users, accounts, and transactions before seeding",
    )
    args = parser.parse_args()

    # A fixed seed makes the generated dataset reproducible.
    rng = random.Random(args.seed)

    if args.reset:
        reset_data()
        print("reset: cleared users, accounts, and transactions")

    categories = db.list_categories()
    users = create_users(rng, args.users)
    accounts = create_accounts(rng, users)
    stats = populate_transactions(rng, accounts, categories, args.transactions)

    rows = db.reconciliation_check()
    total_difference = sum(abs(row["difference"]) for row in rows)

    print(f"users: {len(users)}")
    print(f"accounts: {len(accounts)}")
    print(f"deposits: {stats['deposit']}")
    print(f"withdrawals: {stats['withdrawal']}")
    print(f"expenses: {stats['expense']}")
    print(f"transfers: {stats['transfer']}")
    print(f"skipped (insufficient funds): {stats['skipped']}")
    print(f"reconciliation difference: {total_difference}")

    if total_difference != 0:
        raise SystemExit("reconciliation failed: balances do not match the ledger")


if __name__ == "__main__":
    main()
