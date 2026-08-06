CREATE TABLE orders (
    order_id     INT PRIMARY KEY,
    customer_id  INT,
    order_date   DATE,
    total_amount DECIMAL(10, 2)
);

INSERT INTO orders (order_id, customer_id, order_date, total_amount) VALUES
(101, 1,  '2024-01-15', 72.97),
(102, 2,  '2024-01-17', 44.99),
(103, 1,  '2024-02-02', 49.99),
(104, 3,  '2024-02-10', 99.98),
(105, 5,  '2024-02-14', 89.99),
(106, 4,  '2024-02-20', 16.98),
(107, 6,  '2024-03-01', 119.98),
(108, 2,  '2024-03-05', 34.99),
(109, 8,  '2024-03-12', 69.99),
(110, 3,  '2024-03-18', 46.98);
