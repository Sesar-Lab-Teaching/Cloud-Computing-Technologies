CREATE TABLE IF NOT EXISTS accounts (
    id INT PRIMARY KEY,
    name VARCHAR(40),
    balance INT
);

INSERT IGNORE INTO accounts
    (id, name, balance)
VALUES
    (1, 'Mario', 100);

INSERT IGNORE INTO accounts
    (id, name, balance)
VALUES
    (2, 'Luigi', 200);