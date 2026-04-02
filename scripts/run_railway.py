"""
Roda o ETL completo e salva o log em arquivo.
Execute: python scripts/run_railway.py
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = ROOT / "scripts" / "etl_railway.log"

def log(msg):
    print(msg, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

log("=== ETL Railway iniciado ===")

try:
    from etl.extract import ler_abas_excel
    from etl.transform import transformar
    from etl.load import carregar, hash_arquivo, arquivo_ja_importado

    uploads = ROOT / "data" / "uploads"
    arquivos = sorted(f for f in uploads.glob("*.xlsx") if not f.name.startswith("~$"))
    log(f"Arquivos encontrados: {[a.name for a in arquivos]}")

    for arq in arquivos:
        if not arq.exists():
            log(f"NAO ENCONTRADO: {arq.name}")
            continue

        hash_arq = hash_arquivo(arq)
        if arquivo_ja_importado(arq.name, hash_arq):
            log(f"[skip] '{arq.name}' já importado com este conteúdo — pulando.")
            continue

        log(f"\n--- {arq.name} ---")
        abas = ler_abas_excel(arq)
        df = transformar(abas, arq.name)
        log(f"Registros transformados: {len(df)}")
        r = carregar(df, arquivo_nome=arq.name, hash_arq=hash_arq)
        log(f"Resultado: {r}")

    log("\n=== ETL concluido com sucesso ===")

except Exception as e:
    log(f"ERRO GERAL: {e}")
    import traceback
    log(traceback.format_exc())
