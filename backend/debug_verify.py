from app.core.security import security_manager
h = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8j1G1v7e1O'
print('verify:', security_manager.verify_password('password', h))
