# finance-db

A small OLTP (transactional) database project built with PostgreSQL 18 and
Python's `psycopg` 3. It models users, bank accounts, and transactions, and
demonstrates the parts of a relational database that analytics projects do not:
constraints, ACID transactions, row-level locking, and reconciliation.

## Stack

- PostgreSQL 18 in Docker Compose
- Python 3.12 managed with `uv`
- `psycopg` 3 with plain parameterized SQL (no ORM)
- `pytest` for the small test suite

## Quickstart

Start the database and wait until it is healthy:

```bash
docker compose up -d --wait
```

Apply the schema and reference data (this resets all demo data):

```bash
docker compose exec -T db psql -U postgres -d finance -v ON_ERROR_STOP=1 < schema.sql
docker compose exec -T db psql -U postgres -d finance -v ON_ERROR_STOP=1 < seed.sql
```

Install dependencies and run the demo:

```bash
uv sync
uv run finance-db
```

Run the tests and the concurrency demonstration:

```bash
uv run pytest -q
uv run python concurrency_demo.py
```

Populate a reproducible random dataset (resets users, accounts, and transactions):

```bash
uv run python seed_random.py --reset
uv run python seed_random.py --users 20 --transactions 120 --seed 7
```

The seeder uses a fixed random seed by default and checks that the
reconciliation difference stays at `0.00`.

Inspect the data directly or run the showcase queries:

```bash
docker compose exec db psql -U postgres -d finance
docker compose exec -T db psql -U postgres -d finance -v ON_ERROR_STOP=1 < queries.sql
```

If Docker reports a permission error, run the commands with `sg docker -c "..."`.

## Schema

| Object | Purpose |
| --- | --- |
| `users` | Account owners with unique email and scrypt password hash |
| `accounts` | Balances per user, non-negative, unique per user and name |
| `categories` | Expense categories |
| `transactions` | Deposits, withdrawals, expenses, and both transfer legs |
| `monthly_spending_by_category` | View: expense totals per user, month, and category |
| `account_reconciliation` | View: cached balance vs. balance computed from transactions |

Money uses `NUMERIC(12, 2)` and Python `Decimal`, never floats. An expense
must have a category, enforced by a `CHECK` constraint.

## Design notes

- Each database operation is one transaction. A failure rolls back the whole
  operation, so a balance change and its transaction row always agree.
- Transfers lock both account rows with `SELECT ... FOR UPDATE`, in ID order, to
  avoid deadlocks and to prevent concurrent withdrawals from overspending.
- `withdraw` and `add_expense` lock the account row before checking the balance.
- Passwords are hashed with `hashlib.scrypt`; plaintext passwords are never
  stored.
- `account_reconciliation` is the data-quality check: its `difference` column
  must be `0.00` for every account.
- `schema.sql` drops and recreates its objects, so it is safe to re-run while
  iterating locally.

## Project layout

- `src/finance_db/db.py` — connection helper and database operations
- `src/finance_db/main.py` — demo scenarios
- `seed_random.py` — reproducible random data generator
- `tests/test_db.py` — pytest suite
- `concurrency_demo.py` — two threads competing for one account balance
- `schema.sql`, `seed.sql` — schema and reference data
- `queries.sql` — showcase queries and an `EXPLAIN ANALYZE` example
- `legacy/` — the original standalone Python exercises

Set `DATABASE_URL` to point at another database; it defaults to
`postgresql://postgres:postgres@localhost:5432/finance`.
