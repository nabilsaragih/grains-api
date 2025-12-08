from sqlalchemy import create_engine, text

from app.core.config import settings

engine = create_engine(settings.tidb_conn_str, pool_pre_ping=True)


def verify_connection() -> None:
    """Ping TiDB to fail fast if credentials are wrong."""
    try:
        with engine.connect() as conn:
            print("Ping TiDB:", conn.execute(text("SELECT 1")).scalar())
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to TiDB: {exc}") from exc


print(f"[INFO] TiDB connection string ready. Connected DB = {settings.db_name}")
verify_connection()
