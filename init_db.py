from sqlalchemy import text, select, insert

from models import (
    engine,
    metadata,
    users,
    season_master
)
from services.auth_service import (
    hash_password,
    ROLE_ADMIN,
    ROLE_FARMER,
    ROLE_OFFICER
)


def init_database():
    # ✅ Step 1: Create schema (important for your master tables)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS mastersetup"))

    # ✅ Step 2: Create all tables (including raw_yield_data)
    metadata.create_all(engine)

    # ✅ Step 3: Alter existing tables safely (idempotent)
    alter_statements = [
        # crop_master
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS created_by INTEGER NULL",
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS updated_by INTEGER NULL",
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()",
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()",

        # yielddata
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS created_by INTEGER NULL",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS updated_by INTEGER NULL",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()",
    ]

    with engine.begin() as conn:

        # Apply alter statements
        for statement in alter_statements:
            conn.execute(text(statement))

        # ✅ Step 4: Insert default seasons (if empty)
        season_count = conn.execute(select(season_master)).fetchall()

        if len(season_count) == 0:
            conn.execute(insert(season_master).values(seasonname="Spring"))
            conn.execute(insert(season_master).values(seasonname="Summer"))
            conn.execute(insert(season_master).values(seasonname="Winter"))

        # ✅ Step 5: Insert default users (safe, no duplicates)
        default_users = [
            {"username": "admin", "email": "admin@agri.local", "password": "admin123", "role": ROLE_ADMIN},
            {"username": "officer", "email": "officer@agri.local", "password": "officer123", "role": ROLE_OFFICER},
            {"username": "farmer", "email": "farmer@agri.local", "password": "farmer123", "role": ROLE_FARMER},
        ]

        for user_item in default_users:
            existing_user = conn.execute(
                select(users).where(
                    (users.c.username == user_item["username"]) |
                    (users.c.email == user_item["email"])
                )
            ).mappings().first()

            if not existing_user:
                conn.execute(
                    insert(users).values(
                        username=user_item["username"],
                        email=user_item["email"],
                        password_hash=hash_password(user_item["password"]),
                        role=user_item["role"],
                    )
                )

    print("✅ Database initialized successfully")
    print("👉 Default logins:")
    print("   admin / admin123")
    print("   officer / officer123")
    print("   farmer / farmer123")


if __name__ == "__main__":
    init_database()