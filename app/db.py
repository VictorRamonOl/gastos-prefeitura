"""
app/db.py
Conexão com o MySQL via python-dotenv + mysql-connector-python.
"""
import os
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

# Carrega .env da raiz do projeto
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME", "gastos_prefeitura"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset="utf8mb4",
    )


def query_df(sql: str, params=None) -> "pd.DataFrame":
    """Executa uma query e retorna um DataFrame."""
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()
    return df
