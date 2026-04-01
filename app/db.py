"""
app/db.py
Conexão com o MySQL via SQLAlchemy + python-dotenv.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

# Carrega .env da raiz do projeto
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get_engine():
    from urllib.parse import quote_plus
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    db   = os.getenv("DB_NAME", "gastos_prefeitura")
    user = os.getenv("DB_USER", "root")
    pwd  = quote_plus(os.getenv("DB_PASSWORD", ""))   # codifica @ e caracteres especiais
    url  = f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


# Engine singleton (reutilizado entre chamadas)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


def get_connection():
    """Retorna conexão raw (para INSERT/UPDATE no ETL)."""
    import mysql.connector
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME", "gastos_prefeitura"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset="utf8mb4",
    )


def query_df(sql: str, params=None) -> pd.DataFrame:
    """Executa uma query e retorna um DataFrame (sem warnings)."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)
