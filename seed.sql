BEGIN;

INSERT INTO categories (name)
VALUES
    ('Food'),
    ('Transport'),
    ('Entertainment'),
    ('Rent'),
    ('Utilities')
ON CONFLICT (name) DO NOTHING; 

COMMIT;
