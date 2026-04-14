"""
etl/load.py
Carrega o DataFrame no MySQL em lotes (batch) para suportar conexões remotas.
Proteção dupla contra re-importação:
  1. hash_arquivo — pula o arquivo se o conteúdo já foi importado com sucesso.
  2. hash_linha (UNIQUE no banco) — INSERT IGNORE descarta linhas duplicadas.
"""
import hashlib
import time
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import get_connection

BATCH_SIZE = 100   # linhas por lote
MAX_RETRY  = 3     # tentativas por lote em caso de queda de conexão


# -----------------------------------------------------------------
# Hashes
# -----------------------------------------------------------------
def hash_arquivo(caminho: Path) -> str:
    """SHA-256 do conteúdo binário do arquivo Excel."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def arquivo_ja_importado(nome: str, hash_arq: str) -> bool:
    """
    Retorna True se já existe um registro 'ok' para este arquivo
    com exatamente o mesmo hash de conteúdo.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COUNT(*) FROM arquivos_importados
               WHERE nome_arquivo = %s AND hash_arquivo = %s AND status = 'ok'""",
            (nome, hash_arq),
        )
        return cursor.fetchone()[0] > 0
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def _hash_linha(row: pd.Series) -> str:
    partes = "|".join([
        str(row.get("DATA", "")),
        str(row.get("DESCRICAO", ""))[:100],
        str(row.get("VALOR", "")),
        str(row.get("RECURSO", "")),
        str(row.get("CONTA", "")),
        str(row.get("ARQUIVO_ORIGEM", "")),
        str(row.get("ABA_ORIGEM", "")),
    ])
    return hashlib.sha256(partes.encode("utf-8")).hexdigest()


def _row_tuple(row: pd.Series) -> tuple:
    data_val = row["DATA"].date() if pd.notna(row.get("DATA")) else None
    return (
        data_val,
        int(row["ANO"])   if pd.notna(row.get("ANO"))  else None,
        int(row["MES"])   if pd.notna(row.get("MES"))  else None,
        str(row.get("DESCRICAO",  ""))[:2000],
        str(row.get("FAVORECIDO", ""))[:500],
        str(row.get("RECURSO",    ""))[:200],
        str(row.get("SECRETARIA", ""))[:100],
        str(row.get("CONTA",      ""))[:200],
        float(row.get("VALOR", 0)),
        str(row.get("ABA_ORIGEM",      ""))[:100],
        str(row.get("ARQUIVO_ORIGEM",  ""))[:200],
        row["hash_linha"],
    )


# -----------------------------------------------------------------
# Carga principal
# -----------------------------------------------------------------
def _limpar_dados_anteriores(arquivo_nome: str) -> int:
    """
    Remove do banco todos os registros de importações anteriores do mesmo arquivo
    cujo hash ERA diferente (arquivo foi atualizado).
    Isso evita acúmulo de dados antigos quando o Excel é editado e reimportado.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM pagamentos WHERE arquivo_origem = %s",
            (arquivo_nome,),
        )
        removidos = cursor.rowcount
        conn.commit()
        if removidos:
            print(f"  [load] {removidos} registros anteriores de '{arquivo_nome}' removidos (arquivo atualizado).")
        return removidos
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def carregar(df: pd.DataFrame, arquivo_nome: str = "", hash_arq: str = "") -> dict:
    if df.empty:
        print("  [load] DataFrame vazio.")
        return {"inseridos": 0, "duplicados": 0, "erros": 0}

    df = df.copy()
    df["hash_linha"] = df.apply(_hash_linha, axis=1)

    # Limpa registros antigos do mesmo arquivo antes de inserir os novos.
    # Garante que correções no Excel substituam os dados, não se acumulem.
    _limpar_dados_anteriores(arquivo_nome)

    inseridos = duplicados = erros = 0

    sql = """
        INSERT IGNORE INTO pagamentos
            (data, ano, mes, descricao, favorecido, recurso, secretaria, conta, valor,
             aba_origem, arquivo_origem, hash_linha)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    rows = [_row_tuple(row) for _, row in df.iterrows()]

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]

        for tentativa in range(MAX_RETRY):
            conn = cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.executemany(sql, batch)
                conn.commit()
                lote_ins = cursor.rowcount
                lote_dup = len(batch) - lote_ins
                inseridos += lote_ins
                duplicados += lote_dup
                print(f"  [load] lote {start}–{start+len(batch)} | inseridos={lote_ins} dup={lote_dup}")
                break
            except Exception as e:
                err_str = str(e)
                if tentativa < MAX_RETRY - 1:
                    print(f"  [load] lote {start} tentativa {tentativa+1} falhou ({err_str[:60]}), aguardando...")
                    time.sleep(3)
                else:
                    erros += len(batch)
                    print(f"  [load] lote {start} DESISTIU após {MAX_RETRY} tentativas: {err_str[:80]}")
            finally:
                try:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                except Exception:
                    pass

    # Registra log de importação (inclui hash do arquivo)
    for tentativa in range(MAX_RETRY):
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO arquivos_importados
                   (nome_arquivo, hash_arquivo, total_linhas, linhas_inseridas,
                    linhas_duplicadas, status)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    arquivo_nome, hash_arq or None,
                    len(df), inseridos, duplicados,
                    "ok" if erros == 0 else "parcial",
                ),
            )
            conn.commit()
            break
        except Exception as e:
            if tentativa == MAX_RETRY - 1:
                print(f"  [load] AVISO: não foi possível registrar log: {e}")
            time.sleep(2)
        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    print(f"  [load] TOTAL — Inseridos: {inseridos} | Duplicados: {duplicados} | Erros: {erros}")
    return {"inseridos": inseridos, "duplicados": duplicados, "erros": erros}
