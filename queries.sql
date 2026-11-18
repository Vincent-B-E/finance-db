SELECT u.name AS user_name, a.name AS account_name, a.balance
FROM users AS u
JOIN accounts AS a ON a.user_id = u.id
ORDER BY u.name, a.name;

SELECT user_id, month, category, total
FROM monthly_spending_by_category
ORDER BY month DESC, total DESC;

SELECT t.occurred_at, a.name AS account_name, c.name AS category,
       t.amount, t.description
FROM transactions AS t
JOIN accounts AS a ON a.id = t.account_id
JOIN categories AS c ON c.id = t.category_id
WHERE t.kind = 'expense'
ORDER BY t.amount DESC
LIMIT 10;

SELECT kind, COUNT(*) AS transactions, SUM(amount) AS total
FROM transactions
GROUP BY kind
ORDER BY kind;

SELECT * FROM account_reconciliation ORDER BY account_id;

EXPLAIN ANALYZE
SELECT *
FROM transactions
WHERE account_id = 1
ORDER BY occurred_at DESC
LIMIT 20;
