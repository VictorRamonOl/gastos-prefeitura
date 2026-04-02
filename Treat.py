import pandas as pd
import re
from pathlib import Path
import datetime as dt

# =========================================================
# CAMINHOS
# =========================================================
BASE_PATH = Path(r"D:\Documents\0. Automações\Gastos prefeitura - Maior Fornecedor")

ARQUIVO_2025 = BASE_PATH / "PLANILHA DE DESPESAS PAGAS 2025.xlsx"
ARQUIVO_2026 = BASE_PATH / "PLANILHA DE DESPESAS PAGAS 2026..xlsx"
ARQUIVO_SAIDA = BASE_PATH / "DESPESAS_PREFEITURA_TRATADAS.xlsx"

# =========================================================
# CONFIG
# =========================================================
MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "MARCO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

# =========================================================
# FUNÇÕES GERAIS
# =========================================================
def norm(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt).strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt

def norm_upper(txt):
    return norm(txt).upper()

def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    txt = str(valor).strip()
    txt = txt.replace("R$", "").replace("r$", "").strip()

    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    else:
        txt = txt

    txt = re.sub(r"[^0-9\.\-]", "", txt)

    if txt == "":
        return 0.0

    try:
        return float(txt)
    except:
        return 0.0

def tratar_data(valor):
    if pd.isna(valor):
        return pd.NaT

    if isinstance(valor, pd.Timestamp):
        return pd.to_datetime(valor, errors="coerce")

    if isinstance(valor, (dt.datetime, dt.date)):
        return pd.to_datetime(valor, errors="coerce")

    if isinstance(valor, (int, float)) and 20000 < float(valor) < 60000:
        try:
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(float(valor), unit="D")
        except:
            pass

    txt = str(valor).strip()
    if txt == "":
        return pd.NaT

    data = pd.to_datetime(txt, errors="coerce", dayfirst=True)
    if pd.notna(data):
        return data

    data = pd.to_datetime(txt, errors="coerce", format="%d/%m/%Y")
    if pd.notna(data):
        return data

    return pd.NaT

def aba_eh_mes(nome_aba):
    nome = norm_upper(nome_aba)
    return any(mes in nome for mes in MESES)

def extrair_mes_ano_aba(nome_aba):
    nome = norm_upper(nome_aba)

    mes = None
    for m in MESES:
        if m in nome:
            mes = m
            break

    ano = None
    m_ano = re.search(r"(20\d{2})", nome)
    if m_ano:
        ano = int(m_ano.group(1))

    return mes, ano

def mes_para_numero(mes):
    mapa = {
        "JANEIRO": 1,
        "FEVEREIRO": 2,
        "MARÇO": 3,
        "MARCO": 3,
        "ABRIL": 4,
        "MAIO": 5,
        "JUNHO": 6,
        "JULHO": 7,
        "AGOSTO": 8,
        "SETEMBRO": 9,
        "OUTUBRO": 10,
        "NOVEMBRO": 11,
        "DEZEMBRO": 12,
    }
    return mapa.get(norm_upper(mes), None)

# =========================================================
# LEITURA DAS ABAS
# =========================================================
def detectar_linha_cabecalho(df_raw):
    limite = min(20, len(df_raw))
    for i in range(limite):
        linha = " | ".join(norm_upper(x) for x in df_raw.iloc[i].tolist())
        if "ORD" in linha and "DATA" in linha and "RECURSO" in linha and "CONTA" in linha and "VALOR" in linha:
            return i
    return None

def localizar_indices_colunas(cabecalho):
    idx_ord = idx_data = idx_recurso = idx_conta = idx_valor = None

    for idx, item in enumerate(cabecalho):
        txt = norm_upper(item)

        if idx_ord is None and "ORD" in txt:
            idx_ord = idx
        elif idx_data is None and "DATA" in txt:
            idx_data = idx
        elif idx_recurso is None and "RECURSO" in txt:
            idx_recurso = idx
        elif idx_conta is None and "CONTA" in txt:
            idx_conta = idx
        elif idx_valor is None and "VALOR" in txt:
            idx_valor = idx

    return idx_ord, idx_data, idx_recurso, idx_conta, idx_valor

def extrair_favorecido(descricao):
    d = norm_upper(descricao)

    if d == "":
        return ""

    padroes = [
        r"^(?:PAGTO|PAGAMENTO)\s+(.+?)(?:\s+NF\b|\s+NFS\b|\s+REF\b|\s+DARF\b|\s+COD\b|\s+\d{1,2}/\d{4}\b|$)",
        r"^REPASSE\s+PARA\s+(.+?)(?:$)",
        r"^FOLHA\s+DE\s+PAGAMENTO\s+(.+?)(?:$)",
        r"^PAGAMENTO\s+DE\s+(.+?)(?:$)"
    ]

    for padrao in padroes:
        m = re.search(padrao, d, flags=re.IGNORECASE)
        if m:
            nome = m.group(1).strip()
            nome = re.sub(r"\s+", " ", nome)
            return nome

    m = re.search(r"^(.+?)(?:\s+NF\b|\s+REF\b|\s+DARF\b|$)", d, flags=re.IGNORECASE)
    if m:
        nome = m.group(1).strip()
        nome = re.sub(r"\s+", " ", nome)
        return nome

    return d

def montar_dataframe_aba(df_raw, nome_aba):
    linha_cab = detectar_linha_cabecalho(df_raw)
    if linha_cab is None:
        raise ValueError("Cabeçalho não encontrado na aba.")

    cabecalho = df_raw.iloc[linha_cab].tolist()
    idx_ord, idx_data, idx_recurso, idx_conta, idx_valor = localizar_indices_colunas(cabecalho)

    if idx_data is None or idx_recurso is None or idx_conta is None or idx_valor is None:
        raise ValueError("Não foi possível localizar todas as colunas principais.")

    desc_cols = list(range(idx_data + 1, idx_recurso))
    if not desc_cols:
        raise ValueError("Não foi possível localizar as colunas de descrição.")

    valor_cols = [idx_valor]
    for extra in [idx_valor + 1, idx_valor + 2]:
        if extra < df_raw.shape[1]:
            valor_cols.append(extra)

    linhas = []
    df_dados = df_raw.iloc[linha_cab + 1:].copy()

    mes_aba, ano_aba = extrair_mes_ano_aba(nome_aba)
    mes_num_aba = mes_para_numero(mes_aba)

    for _, row in df_dados.iterrows():
        valor_original_data = row.iloc[idx_data] if idx_data < len(row) else None
        recurso = norm_upper(row.iloc[idx_recurso]) if idx_recurso < len(row) else ""
        conta = norm(row.iloc[idx_conta]) if idx_conta < len(row) else ""

        desc_partes = []
        for c in desc_cols:
            if c < len(row):
                v = norm(row.iloc[c])
                if v != "":
                    desc_partes.append(v)
        descricao = " ".join(desc_partes).strip()

        valor_partes = []
        for c in valor_cols:
            if c < len(row):
                v = row.iloc[c]
                if pd.notna(v) and str(v).strip() != "":
                    valor_partes.append(v)

        if len(valor_partes) == 1 and isinstance(valor_partes[0], (int, float)):
            valor = float(valor_partes[0])
        else:
            valor_bruto = " ".join(str(v).strip() for v in valor_partes)
            valor = limpar_valor(valor_bruto)

        if descricao == "" and valor == 0:
            continue

        desc_upper = norm_upper(descricao)
        if "TOTAL" in desc_upper or "SUBTOTAL" in desc_upper:
            continue

        data = tratar_data(valor_original_data)

        ano = data.year if pd.notna(data) else ano_aba
        mes = data.month if pd.notna(data) else mes_num_aba

        linhas.append({
            "DATA": data,
            "ANO": ano,
            "MES": mes,
            "DESCRICAO": descricao,
            "FAVORECIDO": extrair_favorecido(descricao),
            "RECURSO": recurso,
            "CONTA": conta,
            "VALOR": valor,
            "ABA_ORIGEM": nome_aba
        })

    df = pd.DataFrame(linhas)

    if df.empty:
        return df

    df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce")
    df["MES"] = pd.to_numeric(df["MES"], errors="coerce")
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0)
    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    df = df[df["VALOR"] > 0].copy()

    return df

# =========================================================
# CONSOLIDAÇÃO
# =========================================================
def carregar_abas_mensais(caminho_arquivo):
    xl = pd.ExcelFile(caminho_arquivo)
    abas = [aba for aba in xl.sheet_names if aba_eh_mes(aba)]

    bases = []
    for aba in abas:
        try:
            df_raw = pd.read_excel(caminho_arquivo, sheet_name=aba, header=None)
            df_aba = montar_dataframe_aba(df_raw, aba)

            if not df_aba.empty:
                bases.append(df_aba)
                print(f"OK - {Path(caminho_arquivo).name} | {aba} | {len(df_aba)} linhas")
            else:
                print(f"AVISO - {Path(caminho_arquivo).name} | {aba} | sem linhas válidas")

        except Exception as e:
            print(f"ERRO - {aba} | {e}")

    if not bases:
        return pd.DataFrame()

    return pd.concat(bases, ignore_index=True)

# =========================================================
# MAIN
# =========================================================
def main():
    print("Lendo arquivos...")

    df_2025 = carregar_abas_mensais(ARQUIVO_2025)
    df_2026 = carregar_abas_mensais(ARQUIVO_2026)

    bases_validas = [df for df in [df_2025, df_2026] if not df.empty]
    if not bases_validas:
        raise ValueError("Nenhuma aba mensal válida foi processada.")

    base = pd.concat(bases_validas, ignore_index=True)

    base = base.sort_values(
        by=["ANO", "MES", "DATA", "RECURSO", "VALOR"],
        ascending=[True, True, True, True, False]
    ).reset_index(drop=True)

    resumo_favorecido = (
        base.groupby("FAVORECIDO", dropna=False)
        .agg(
            VALOR_TOTAL=("VALOR", "sum"),
            QTD_LANCAMENTOS=("VALOR", "count"),
            PRIMEIRA_DATA=("DATA", "min"),
            ULTIMA_DATA=("DATA", "max"),
            RECURSOS=("RECURSO", lambda x: " | ".join(sorted(set(i for i in x if str(i).strip() != ""))))
        )
        .reset_index()
        .sort_values("VALOR_TOTAL", ascending=False)
    )

    resumo_favorecido_recurso = (
        base.groupby(["FAVORECIDO", "RECURSO"], dropna=False)
        .agg(
            VALOR_TOTAL=("VALOR", "sum"),
            QTD_LANCAMENTOS=("VALOR", "count")
        )
        .reset_index()
        .sort_values("VALOR_TOTAL", ascending=False)
    )

    resumo_ano_favorecido = (
        base.groupby(["ANO", "FAVORECIDO"], dropna=False)
        .agg(
            VALOR_TOTAL=("VALOR", "sum"),
            QTD_LANCAMENTOS=("VALOR", "count")
        )
        .reset_index()
        .sort_values(["ANO", "VALOR_TOTAL"], ascending=[True, False])
    )

    resumo_recurso = (
        base.groupby("RECURSO", dropna=False)
        .agg(
            VALOR_TOTAL=("VALOR", "sum"),
            QTD_LANCAMENTOS=("VALOR", "count"),
            QTD_FAVORECIDOS=("FAVORECIDO", "nunique")
        )
        .reset_index()
        .sort_values("VALOR_TOTAL", ascending=False)
    )

    resumo_mes = (
        base.groupby(["ANO", "MES"], dropna=False)
        .agg(
            VALOR_TOTAL=("VALOR", "sum"),
            QTD_LANCAMENTOS=("VALOR", "count")
        )
        .reset_index()
        .sort_values(["ANO", "MES"])
    )

    with pd.ExcelWriter(ARQUIVO_SAIDA, engine="openpyxl", datetime_format="DD/MM/YYYY") as writer:
        base.to_excel(writer, sheet_name="BASE_GERAL", index=False)
        resumo_favorecido.to_excel(writer, sheet_name="RESUMO_FAVORECIDO", index=False)
        resumo_favorecido_recurso.to_excel(writer, sheet_name="FAV_X_RECURSO", index=False)
        resumo_ano_favorecido.to_excel(writer, sheet_name="ANO_X_FAVORECIDO", index=False)
        resumo_recurso.to_excel(writer, sheet_name="RESUMO_RECURSO", index=False)
        resumo_mes.to_excel(writer, sheet_name="RESUMO_MES", index=False)

    print("\nArquivo final gerado com sucesso:")
    print(ARQUIVO_SAIDA)

if __name__ == "__main__":
    main()