CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    concurrency VARCHAR(5) NOT NULL,
    stock INT NOT NULL
);
