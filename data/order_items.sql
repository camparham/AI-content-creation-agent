CREATE TABLE order_items (
    order_id   INT,
    product_id INT,
    quantity   INT,
    unit_price DECIMAL(10, 2),
    PRIMARY KEY (order_id, product_id)
);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(101, 1,  2, 29.99),
(101, 3,  1, 12.99),
(102, 2,  1, 44.99),
(103, 4,  1, 49.99),
(104, 6,  1, 89.99),
(104, 7,  1,  9.99),
(105, 6,  1, 89.99),
(106, 3,  1, 12.99),
(106, 7,  1,  9.99),
(107, 9,  1, 69.99),
(107, 4,  1, 49.99),
(108, 5,  1, 34.99),
(109, 9,  1, 69.99),
(110, 2,  1, 44.99),
(110, 7,  1,  9.99);
