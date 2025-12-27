-- Очистка данных
DELETE FROM messages;
DELETE FROM chats;

-- Создание тестовых чатов
INSERT INTO chats (user_id, client_name, client_phone, title, description, priority, status, message_count, unread_count, created_at, updated_at)
VALUES 
(1, 'John Smith', '+79161112233', 'Delivery question', 'Customer asks about delivery time', 'NORMAL', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
(1, 'Mary Johnson', '+79162223344', 'Payment problem', 'Cannot pay online order', 'HIGH', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
(1, 'Alex Brown', '+79163334455', 'Product consultation', 'Need help choosing product', 'LOW', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
(1, 'Olga Davis', '+79164445566', 'Complaint', 'Received defective item', 'URGENT', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
(1, 'Serge Wilson', '+79165556677', 'Warranty service', 'Question about warranty terms', 'NORMAL', 'ACTIVE', 0, 0, datetime('now'), datetime('now'));