"""Create the configured MySQL database if it does not exist.

Typical use:

    python -m scripts.init_db      # verify / create the database
    python -m alembic upgrade head # create tables

If the database already exists and the configured user can connect to it,
this script succeeds even when the user has no global CREATE privilege.
The script uses the MYSQL_* settings; a DATABASE_URL override is ignored.
"""

import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _url(settings, database: str | None) -> URL:
    return URL.create(
        "mysql+pymysql",
        username=settings.mysql_user,
        password=settings.mysql_password,
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=database,
        query={
            "charset": settings.mysql_charset,
            "connect_timeout": str(settings.db_connect_timeout),
        },
    )


def _is_unknown_database(exc: OperationalError) -> bool:
    original = getattr(exc, "orig", None)
    code = original.args[0] if original is not None and getattr(original, "args", None) else None
    return code == 1049 or "Unknown database" in str(exc)


def _can_connect(settings, database: str) -> bool:
    engine = create_engine(_url(settings, database), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    finally:
        engine.dispose()


def main() -> int:
    settings = get_settings()
    database = settings.mysql_database

    if not SAFE_IDENTIFIER.fullmatch(database):
        print(f"[init_db] Invalid database name: {database!r}")
        return 2

    try:
        if _can_connect(settings, database):
            print(f"[init_db] Database `{database}` is reachable.")
            return 0
    except OperationalError as exc:
        if not _is_unknown_database(exc):
            print(f"[init_db] Cannot connect to MySQL: {exc}")
            return 1
    except Exception as exc:  # noqa: BLE001 - report and exit with a non-zero code
        print(f"[init_db] Cannot connect to MySQL: {exc}")
        return 1

    print(f"[init_db] Database `{database}` does not exist, trying to create it...")
    engine = create_engine(_url(settings, None), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                )
            )
    except Exception as exc:  # noqa: BLE001 - report and exit with a non-zero code
        print(
            "[init_db] Failed to create the database. Run deploy/mysql/init.sql "
            f"as an admin user instead. Error: {exc}"
        )
        return 1
    finally:
        engine.dispose()

    print(f"[init_db] Database `{database}` created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
