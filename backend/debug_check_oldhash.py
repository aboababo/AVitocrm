from auth import is_old_password_hash

s = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94"
print("len=", len(s))
print("lower all hex=", all(c in "0123456789abcdef" for c in s.lower()))
print("func=", is_old_password_hash(s))
print(repr(s))
