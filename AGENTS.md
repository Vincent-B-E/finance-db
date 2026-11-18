# Project

`finance-db` is a small OLTP demo: PostgreSQL 18 in Docker, Python 3.12 with
`psycopg` 3 and plain parameterized SQL, plus a pytest suite. It exists to show
the transactional side of data work (constraints, ACID, row locks,
reconciliation) that analytics portfolios usually skip.

# Project Rules

- Target level: Junior/Mid Data Engineer portfolio project. Keep architecture
  flat and readable.
- DO NOT create Alembic migrations, GitHub Actions, pre-commit hooks, or
  multi-folder docs unless explicitly asked.
- Use plain SQL files (`schema.sql`, `seed.sql`) and standard `psycopg` (v3) or
  `SQLAlchemy` core. No heavy ORM magic.
- Ask for approval with a file list before creating more than 2 files at once.
- `legacy/` holds the original standalone Python exercises. Leave it as a
  historical reference; new work goes in `src/finance_db/` or the top-level
  scripts.

# Stack and Commands

Start the database and wait for health:

```bash
docker compose up -d --wait
```

Apply schema and reference data (both are idempotent-ish: `schema.sql` drops and
recreates its objects, so it resets demo data):

```bash
docker compose exec -T db psql -U postgres -d finance -v ON_ERROR_STOP=1 < schema.sql
docker compose exec -T db psql -U postgres -d finance -v ON_ERROR_STOP=1 < seed.sql
```

Install and run:

```bash
uv sync
uv run finance-db
uv run pytest -q
uv run python concurrency_demo.py
```

If Docker reports a permission error, prefix commands with
`sg docker -c "..."`.

# Layout

- `src/finance_db/db.py` — connection helper and database operations
- `src/finance_db/main.py` — demo scenarios
- `schema.sql`, `seed.sql` — schema and reference data
- `seed_random.py` — reproducible random dataset
- `test_db.py` — pytest suite
- `concurrency_demo.py` — two threads competing for one balance
- `queries.sql` — showcase queries and `EXPLAIN ANALYZE`
- `legacy/` — original standalone exercises

# Invariants to Preserve

- Money is `NUMERIC(12, 2)` in SQL and `Decimal` in Python. Never floats.
- One database operation is one transaction; a failure rolls back the whole
  operation so balances and transaction rows always agree.
- Transfers lock both account rows with `SELECT ... FOR UPDATE` in ascending ID
  order to avoid deadlocks. Do not change lock order casually.
- `withdraw` and `add_expense` lock the account row before checking the balance.
- `account_reconciliation.difference` must be `0.00` for every account. This is
  the data-quality check.
- An expense must have a category, enforced by a `CHECK` constraint.
- Passwords are hashed with `hashlib.scrypt`; never store or log plaintext.

# Working Agreement

Teaching and coding preferences (pacing, when to take over, comment style,
explain-backs) live in the global `data-engineering-tutor` skill. Keep this file
repo-specific so it can be published.
