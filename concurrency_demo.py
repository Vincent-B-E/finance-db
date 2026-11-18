"""Two threads try to withdraw 80.00 from the same 100.00 account."""

import secrets
import threading

from finance_db import db


def attempt(account_id, barrier, results, label):
    # Barrier makes both threads start at the same moment.
    barrier.wait()
    try:
        balance = db.withdraw(account_id, "80.00", f"{label} withdrawal")
        results.append((label, "ok", balance))
    except ValueError as exc:
        results.append((label, "rejected", str(exc)))


def main():
    suffix = secrets.token_hex(3)
    user = db.create_user(
        "Concurrent User", f"concurrent-{suffix}@example.com", "password123"
    )
    account = db.create_account(user["id"], "Checking")
    db.deposit(account["id"], "100.00", "Opening deposit")
    print(f"start balance: {db.get_account(account['id'])['balance']}")

    # withdraw() uses SELECT ... FOR UPDATE, so only one thread can spend.
    barrier = threading.Barrier(2)
    results = []
    threads = [
        threading.Thread(
            target=attempt, args=(account["id"], barrier, results, label)
        )
        for label in ("thread-a", "thread-b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    print("results:")
    for label, status, detail in sorted(results):
        print(f"  {label}: {status} ({detail})")
    print(f"final balance: {db.get_account(account['id'])['balance']}")
    total_difference = sum(
        abs(row["difference"]) for row in db.reconciliation_check()
    )
    print(f"total reconciliation difference: {total_difference}")


if __name__ == "__main__":
    main()
