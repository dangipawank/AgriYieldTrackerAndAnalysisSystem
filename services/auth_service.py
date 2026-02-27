from datetime import datetime
import bcrypt
from sqlalchemy import select, update

from models import engine, users


ROLE_FARMER = "Farmer"
ROLE_OFFICER = "Officer"
ROLE_ADMIN = "Admin"




def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_user_by_login(login_value: str):
    with engine.connect() as conn:
        user = conn.execute(
            select(users)
            .where((users.c.username == login_value) | (users.c.email == login_value))
        ).mappings().first()
    return user


def get_user_by_id(user_id: int):
    with engine.connect() as conn:
        user = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
    return user


def update_user_last_seen(user_id: int):
    with engine.connect() as conn:
        conn.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(updated_at=datetime.utcnow())
        )
        conn.commit()
