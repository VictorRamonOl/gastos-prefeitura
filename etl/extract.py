"""
etl/extract.py
Lê as abas mensais dos arquivos Excel e retorna DataFrames brutos.
"""
import pandas as pd
from pathlib import Path

MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "MARCO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]


def aba_eh_mes(nome_aba: str) -> bool:
    nome = nome_aba.strip().upper()
    return any(mes in nome for mes in MESES)


def ler_abas_excel(caminho: str | Path) -> dict[str, pd.DataFrame]:
    """Retorna {nome_aba: df_raw} para todas as abas mensais do arquivo."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    xl = pd.ExcelFile(caminho)
    abas_mensais = [a for a in xl.sheet_names if aba_eh_mes(a)]

    resultado = {}
    for aba in abas_mensais:
        df_raw = pd.read_excel(caminho, sheet_name=aba, header=None)
        resultado[aba] = df_raw
        print(f"  [extract] lida aba '{aba}' — {len(df_raw)} linhas brutas")

    return resultado
