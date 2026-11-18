DROP VIEW IF EXISTS monthly_spending_by_category CASCADE;
DROP VIEW IF EXISTS account_reconciliation CASCADE;

DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL CHECK (length(name) >= 3),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL default now()
);

CREATE TABLE accounts (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    name        TEXT NOT NULL,
    balance     NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at  TIMESTAMPTZ NOT NULL default now(),
    UNIQUE (user_id, name)
);

CREATE TABLE categories (
    id      SERIAL PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE transactions (
    id          BIGSERIAL PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    category_id INTEGER REFERENCES categories(id),
    kind        TEXT NOT NULL CHECK (kind IN (
                    'deposit', 'withdrawal',
                    'expense',
                    'transfer_in', 'transfer_out')),
    amount      NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    description TEXT,
    occurred_at TIMESTAMPTZ NOT NULL default now(),
    CHECK (kind <> 'expense' OR category_id IS NOT NULL)
);

CREATE INDEX idx_transactions_account_time 
    ON transactions (account_id, occurred_at DESC);

CREATE OR REPLACE VIEW monthly_spending_by_category AS
SELECT
    a.user_id                                AS user_id,
    date_trunc('month', t.occurred_at)::date AS month,
    c.name                                   AS category,
    SUM(t.amount)                            AS total
FROM transactions AS t
JOIN accounts   AS a ON a.id = t.account_id
JOIN categories AS c ON c.id = t.category_id
WHERE t.kind = 'expense'
GROUP BY a.user_id, month, category;

CREATE OR REPLACE VIEW account_reconciliation AS
WITH totals AS (
    SELECT
        account_id,
        SUM(
            CASE kind
                WHEN 'deposit'      THEN  amount
                WHEN 'transfer_in'  THEN  amount
                WHEN 'withdrawal'   THEN -amount
                WHEN 'expense'      THEN -amount
                WHEN 'transfer_out' THEN -amount
                ELSE 0
            END
        ) AS calculated_balance
    FROM transactions
    GROUP BY account_id
)
SELECT
    a.id                                            AS account_id,
    a.name                                          AS account_name,
    a.balance                                       AS cached_balance,
    COALESCE(t.calculated_balance, 0)               AS calculated_balance,
    a.balance - COALESCE(t.calculated_balance, 0)   AS difference
FROM accounts AS a
LEFT JOIN totals AS t
       ON t.account_id = a.id;
