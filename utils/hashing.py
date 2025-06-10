# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def hash_password(password):
#     return pwd_context.hash(password)

# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# import bcrypt

# def hash_password(password: str) -> str:
#     """Meng-hash kata sandi menggunakan bcrypt."""
#     hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#     return hashed_bytes.decode('utf-8')

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Memverifikasi apakah kata sandi biasa sesuai dengan kata sandi yang di-hash."""
#     return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# if __name__ == "__main__":
#     # Contoh penggunaan
#     plain = "mysecretpassword"
#     hashed = hash_password(plain)
#     print(f"Kata sandi biasa: {plain}")
#     print(f"Kata sandi ter-hash: {hashed}")
#     is_correct = verify_password(plain, hashed)
#     print(f"Verifikasi (benar): {is_correct}")
#     is_incorrect = verify_password("wrongpassword", hashed)
#     print(f"Verifikasi (salah): {is_incorrect}")