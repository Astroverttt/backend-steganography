import bcrypt

def hash_password(password: str) -> str:
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

if __name__ == "__main__":
    plain = "mysecretpassword"
    hashed = hash_password(plain)
    print(f"Kata sandi biasa: {plain}")
    print(f"Kata sandi ter-hash: {hashed}")
    is_correct = verify_password(plain, hashed)
    print(f"Verifikasi (benar): {is_correct}")
    is_incorrect = verify_password("wrongpassword", hashed)
    print(f"Verifikasi (salah): {is_incorrect}")