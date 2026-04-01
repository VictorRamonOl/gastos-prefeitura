"""
etl/run_etl.py
Ponto de entrada do ETL.
Uso:
    python etl/run_etl.py
    python etl/run_etl.py data/uploads/PLANILHA2025.xlsx data/uploads/PLANILHA2026.xlsx
"""
import sys
from pathlib import Path

# Garante que o root do projeto está no path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl.extract import ler_abas_excel
from etl.transform import transformar
from etl.load import carregar

# Arquivos padrão (relativos à raiz do projeto)
ARQUIVOS_PADRAO = [
    ROOT / "data" / "uploads" / "PLANILHA DE DESPESAS PAGAS 2025.xlsx",
    ROOT / "data" / "uploads" / "PLANILHA DE DESPESAS PAGAS 2026..xlsx",
]


def processar_arquivo(caminho: Path):
    print(f"\n{'='*60}")
    print(f"Processando: {caminho.name}")
    print("="*60)

    abas = ler_abas_excel(caminho)
    if not abas:
        print("  Nenhuma aba mensal encontrada.")
        return

    df = transformar(abas, arquivo_origem=caminho.name)
    if df.empty:
        print("  Nenhum dado válido após transformação.")
        return

    print(f"  Total de registros transformados: {len(df)}")
    stats = carregar(df, arquivo_nome=caminho.name)
    print(f"  Resultado: {stats}")


def main():
    arquivos = [Path(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else ARQUIVOS_PADRAO

    print("ETL - Gastos Prefeitura")
    print(f"Arquivos a processar: {len(arquivos)}")

    for arq in arquivos:
        if not arq.exists():
            print(f"\nAVISO: arquivo não encontrado — {arq}")
            continue
        processar_arquivo(arq)

    print("\nETL concluído.")


if __name__ == "__main__":
    main()
