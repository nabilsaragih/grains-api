import os
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse

import certifi
from dotenv import load_dotenv

load_dotenv()


def _require_env(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise RuntimeError(f"Missing {var} in environment")
    return value


@dataclass(frozen=True)
class Settings:
    mistral_api_key: str
    tidb_user: str
    tidb_password: str
    tidb_host: str
    tidb_port: int
    tidb_db: str
    tidb_vector_table: str
    ollama_base_url: str
    ollama_embedding_model: str
    ollama_chat_model: str

    @property
    def tidb_conn_str(self) -> str:
        pw = quote_plus(self.tidb_password)
        ca = quote_plus(certifi.where())
        return (
            f"mysql+pymysql://{self.tidb_user}:{pw}@{self.tidb_host}:{self.tidb_port}/{self.tidb_db}"
            f"?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca={ca}"
        )

    @property
    def db_name(self) -> str:
        return urlparse(self.tidb_conn_str).path.lstrip("/") or "?"


def load_settings() -> Settings:
    return Settings(
        mistral_api_key=_require_env("MISTRAL_API_KEY"),
        tidb_user=_require_env("TIDB_USER"),
        tidb_password=_require_env("TIDB_PASSWORD"),
        tidb_host=_require_env("TIDB_HOST"),
        tidb_port=int(os.getenv("TIDB_PORT")),
        tidb_db=os.getenv("TIDB_DB"),
        tidb_vector_table=os.getenv("TIDB_VECTOR_TABLE"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL"),
        ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL"),
    )

settings = load_settings()
