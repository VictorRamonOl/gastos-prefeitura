"""
etl/run_etl.py
Ponto de entrada do ETL.

Uso:
    python etl/run_etl.py
    python etl/run_etl.py data/uploads/PLANILHA2025.xlsx data/uploads/PLANILHA2026.xlsx

Proteção contra re-importação:
    Antes de processar cada arquivo, calcula o SHA-256 do seu conteúdo e
    verifica se já existe um registro 'ok' com esse hash no banco.
    Se sim, o arquivo é pulado. Se o arquivo foi modificado (novo mês adicionado),
    o hash muda e ele é reprocessado — mas linhas já existentes são ignoradas
    pelo UNIQUE constraint em hash_linha.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl.extract import ler_abas_excel
from etl.transform import transformar
from etl.load import carregar, hash_arquivo, arquivo_ja_importado

UPLOADS_DIR = ROOT / "data" / "uploads"


def obter_arquivos() -> list[Path]:
    if len(sys.argv) > 1:
        arquivos = [Path(a) for a in sys.argv[1:]]
    else:
        arquivos = sorted(UPLOADS_DIR.glob("*.xlsx"))
    # Ignora temporários do Excel
    return [a for a in arquivos if not a.name.startswith("~$")]


def processar_arquivo(caminho: Path):
    print(f"\n{'=' * 60}")
    print(f"Processando: {caminho.name}")
    print("=" * 60)

    # ── Proteção 1: verifica hash do arquivo ─────────────────────
    hash_arq = hash_arquivo(caminho)
    if arquivo_ja_importado(caminho.name, hash_arq):
        print(f"  [skip] '{caminho.name}' já foi importado com este conteúdo (hash={hash_arq[:12]}…).")
        print("  Para forçar re-importação, exclua o registro em arquivos_importados ou modifique o arquivo.")
        return

    try:
        abas = ler_abas_excel(caminho)
        if not abas:
            print("  Nenhuma aba mensal encontrada.")
            return

        df = transformar(abas, arquivo_origem=caminho.name)
        if df.empty:
            print("  Nenhum dado válido após transformação.")
            return

        print(f"  Total de registros transformados: {len(df)}")
        stats = carregar(df, arquivo_nome=caminho.name, hash_arq=hash_arq)
        print(f"  Resultado: {stats}")

    except Exception as e:
        print(f"  ERRO ao processar {caminho.name}: {e}")


def main():
    arquivos = obter_arquivos()

    print("ETL - Gastos Prefeitura")
    print(f"Pasta de uploads: {UPLOADS_DIR}")
    print(f"Arquivos encontrados: {len(arquivos)}")

    if not arquivos:
        print("\nNenhum arquivo .xlsx encontrado em data/uploads.")
        return

    for i, arq in enumerate(arquivos, start=1):
        print(f"  {i}. {arq.name}")

    for arq in arquivos:
        if not arq.exists():
            print(f"\nAVISO: arquivo não encontrado → {arq}")
            continue
        processar_arquivo(arq)

    print("\nETL concluído.")


if __name__ == "__main__":
    main()
