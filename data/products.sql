CREATE TABLE products (
    product_id INT PRIMARY KEY,
    name       VARCHAR(100),
    category   VARCHAR(50),
    price      DECIMAL(10, 2)
);

INSERT INTO products (product_id, name, category, price) VALUES
(1,  'Wireless Mouse',      'Electronics', 29.99),
(2,  'Desk Lamp',           'Home Office', 44.99),
(3,  'Notebook Set',        'Stationery',  12.99),
(4,  'USB-C Hub',           'Electronics', 49.99),
(5,  'Standing Desk Mat',   'Home Office', 39.99),
(6,  'Mechanical Keyboard', 'Electronics', 89.99),
(7,  'Planner',             'Stationery',   9.99),
(8,  'Monitor Stand',       'Home Office', 34.99),
(9,  'Webcam',              'Electronics', 69.99),
(10, 'Sticky Notes Pack',   'Stationery',   6.99);
