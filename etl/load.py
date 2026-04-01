"""
etl/load.py
Carrega o DataFrame transformado no MySQL, evitando duplicatas via hash.
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

# Adiciona a raiz do projeto ao path para importar app/db.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import get_connection


def _hash_linha(row: pd.Series) -> str:
    """Gera um hash SHA-256 único por linha para controle de duplicatas."""
    partes = "|".join([
        str(row.get("DATA", "")),
        str(row.get("FAVORECIDO", "")),
        str(row.get("VALOR", "")),
        str(row.get("RECURSO", "")),
        str(row.get("CONTA", "")),
        str(row.get("ARQUIVO_ORIGEM", "")),
        str(row.get("ABA_ORIGEM", "")),
    ])
    return hashlib.sha256(partes.encode("utf-8")).hexdigest()


def carregar(df: pd.DataFrame, arquivo_nome: str = "") -> dict:
    """
    Insere os dados no MySQL e retorna estatísticas da importação.
    Retorna: {"inseridos": int, "duplicados": int, "erros": int}
    """
    if df.empty:
        print("  [load] DataFrame vazio, nada a inserir.")
        return {"inseridos": 0, "duplicados": 0, "erros": 0}

    df = df.copy()
    df["hash_linha"] = df.apply(_hash_linha, axis=1)

    inseridos = 0
    duplicados = 0
    erros = 0

    conn = get_connection()
    cursor = conn.cursor()

    sql_insert = """
        INSERT INTO pagamentos
            (data, ano, mes, descricao, favorecido, recurso, conta, valor,
             aba_origem, arquivo_origem, hash_linha)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for _, row in df.iterrows():
        data_val = row["DATA"].date() if pd.notna(row.get("DATA")) else None
        try:
            cursor.execute(sql_insert, (
                data_val,
                int(row["ANO"]) if pd.notna(row.get("ANO")) else None,
                int(row["MES"]) if pd.notna(row.get("MES")) else None,
                str(row.get("DESCRICAO", ""))[:2000],
                str(row.get("FAVORECIDO", ""))[:500],
                str(row.get("RECURSO", ""))[:200],
                str(row.get("CONTA", ""))[:200],
                float(row.get("VALOR", 0)),
                str(row.get("ABA_ORIGEM", ""))[:100],
                str(row.get("ARQUIVO_ORIGEM", ""))[:200],
                row["hash_linha"],
            ))
            inseridos += 1
        except Exception as e:
            err_str = str(e)
            if "Duplicate entry" in err_str or "1062" in err_str:
                duplicados += 1
            else:
                erros += 1
                print(f"  [load] ERRO na linha: {e}")

    conn.commit()

    # Registra no log de importações
    cursor.execute(
        """INSERT INTO arquivos_importados
           (nome_arquivo, total_linhas, linhas_inseridas, linhas_duplicadas, status)
           VALUES (%s, %s, %s, %s, %s)""",
        (arquivo_nome, len(df), inseridos, duplicados, "ok" if erros == 0 else "parcial"),
    )
    conn.commit()
    cursor.close()
    conn.close()

    print(f"  [load] Inseridos: {inseridos} | Duplicados: {duplicados} | Erros: {erros}")
    return {"inseridos": inseridos, "duplicados": duplicados, "erros": erros}
