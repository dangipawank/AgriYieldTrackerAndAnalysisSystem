from sqlalchemy import text, select, insert

from models import engine, metadata, users, season_master
from services.auth_service import hash_password, ROLE_ADMIN, ROLE_FARMER, ROLE_OFFICER




def init_database():
    metadata.create_all(engine)

    alter_statements = [
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS created_by INTEGER NULL",
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS updated_by INTEGER NULL",
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()",
        "ALTER TABLE crop_master ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS created_by INTEGER NULL",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS updated_by INTEGER NULL",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()",
        "ALTER TABLE yielddata ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()",
    ]

    with engine.connect() as conn:
        for statement in alter_statements:
            conn.execute(text(statement))

        season_count = conn.execute(select(text("count(*)")).select_from(season_master)).scalar() or 0
        if season_count == 0:
            conn.execute(insert(season_master).values(seasonname="Spring"))
            conn.execute(insert(season_master).values(seasonname="Summer"))
            conn.execute(insert(season_master).values(seasonname="Winter"))

        default_users = [
            {
                "username": "admin",
                "email": "admin@agri.local",
                "password": "admin123",
                "role": ROLE_ADMIN,
            },
            {
                "username": "officer",
                "email": "officer@agri.local",
                "password": "officer123",
                "role": ROLE_OFFICER,
            },
            {
                "username": "farmer",
                "email": "farmer@agri.local",
                "password": "farmer123",
                "role": ROLE_FARMER,
            },
        ]

        for user_item in default_users:
            existing_user = conn.execute(
                select(users).where(
                    (users.c.username == user_item["username"]) | (users.c.email == user_item["email"])
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
        conn.commit()

    print(
        "Database tables initialized successfully. "
        "Default logins: admin/admin123, officer/officer123, farmer/farmer123"
    )


if __name__ == "__main__":
    init_database()
