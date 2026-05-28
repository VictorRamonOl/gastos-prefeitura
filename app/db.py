"""
app/db.py
Conexão com MySQL via SQLAlchemy.
Suporta: .env local (desenvolvimento) e st.secrets (Streamlit Cloud).
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

# Carrega .env local (ignorado silenciosamente se não existir)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _secrets_file_exists() -> bool:
    """True se há um secrets.toml acessível (Streamlit Cloud ou ~/.streamlit)."""
    candidates = [
        Path.home() / ".streamlit" / "secrets.toml",
        Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml",
    ]
    return any(p.exists() for p in candidates)


def _cfg(key: str, default: str = "") -> str:
    """Lê variável do os.environ/.env (local) ou st.secrets (cloud).

    Só consulta st.secrets quando um secrets.toml realmente existe — evita
    o warning 'No secrets found' aparecer no UI quando rodando local com .env.
    """
    env_val = os.getenv(key)
    if env_val is not None:
        return env_val
    if _secrets_file_exists():
        try:
            import streamlit as st
            import streamlit.runtime
            if streamlit.runtime.exists():
                val = st.secrets.get(key)
                if val is not None:
                    return str(val)
        except Exception:
            pass
    return default


def _get_engine():
    from urllib.parse import quote_plus
    host = _cfg("DB_HOST", "localhost")
    port = _cfg("DB_PORT", "3306")
    db   = _cfg("DB_NAME", "gastos_prefeitura")
    user = _cfg("DB_USER", "root")
    pwd  = quote_plus(_cfg("DB_PASSWORD", ""))
    url  = f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        connect_args={"connect_timeout": 30},
    )


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


def get_connection():
    """Conexão raw para o ETL (INSERT/UPDATE)."""
    import mysql.connector
    return mysql.connector.connect(
        host=_cfg("DB_HOST", "localhost"),
        port=int(_cfg("DB_PORT", "3306")),
        database=_cfg("DB_NAME", "gastos_prefeitura"),
        user=_cfg("DB_USER", "root"),
        password=_cfg("DB_PASSWORD", ""),
        charset="utf8mb4",
    )


def query_df(sql: str, params=None) -> pd.DataFrame:
    """Executa uma query e retorna um DataFrame (sem warnings)."""
    global _engine
    try:
        with get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except Exception:
        # Descarta o engine cacheado e tenta reconectar uma vez
        _engine = None
        with get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
