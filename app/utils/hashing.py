import bcrypt as bcrypt_lib


def hash_password(password: str):
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt_lib.gensalt()
    hashed = bcrypt_lib.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_hash(password: str, hash: str):
    password_bytes = password.encode('utf-8')[:72]
    hash_bytes = hash.encode('utf-8')
    return bcrypt_lib.checkpw(password_bytes, hash_bytes)
