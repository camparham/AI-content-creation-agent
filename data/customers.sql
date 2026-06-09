CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name        VARCHAR(100),
    email       VARCHAR(100),
    city        VARCHAR(50)
);

INSERT INTO customers (customer_id, name, email, city) VALUES
(1,  'Sarah Johnson',  'sarah.johnson@email.com',  'Chicago'),
(2,  'Marcus Lee',     'marcus.lee@email.com',     'Austin'),
(3,  'Priya Patel',    'priya.patel@email.com',    'New York'),
(4,  'James Carter',   'james.carter@email.com',   'Houston'),
(5,  'Emily Davis',    'emily.davis@email.com',    'Chicago'),
(6,  'Daniel Kim',     'daniel.kim@email.com',     'Seattle'),
(7,  'Aisha Brown',    'aisha.brown@email.com',    'Atlanta'),
(8,  'Chris Nguyen',   'chris.nguyen@email.com',   'Austin'),
(9,  'Laura Martinez', 'laura.m@email.com',        'Miami'),
(10, 'Kevin Wilson',   'kevin.w@email.com',        'New York');
