"""
etl/transform.py
Toda a lógica de limpeza e normalização dos dados brutos do Excel.
Recebe {nome_aba: df_raw} e devolve um único DataFrame consolidado.
"""
import re
import datetime as dt
import pandas as pd


# -----------------------------------------------------------------
# Mapeamento RECURSO → SECRETARIA
# A ordem dos checks importa: mais específico primeiro.
# -----------------------------------------------------------------
def mapear_secretaria(recurso: str) -> str:
    r = str(recurso).upper().strip()

    # Educação
    if any(k in r for k in ["FUNDEB", "FME", "PDDE", "PNAE", "PNATE", "PROCAD", "QSE"]):
        return "EDUCAÇÃO"
    if re.search(r"\b70%|\bFOLHA 70|PESSOAL 70|PESSOAL FME|FME PESSOAL", r):
        return "EDUCAÇÃO"

    # Saúde
    if any(k in r for k in ["FMS", "CUSTEIO SUS", "INVEST SUS", "PAB", "PNAB",
                              "PISO ENF", "PISO ENFER", "E MAC", "EMEN MAC", "EMENDA MAC",
                              "SUS", "ATENÇÃO BAS", "PISO"]):
        return "SAÚDE"

    # Assistência Social
    if any(k in r for k in ["FMAS", "FNAS", "GBF", "IGDBF", "PSB", "PBS",
                              "SUAS", "CRIAN", "CREAS", "SNA", "MEDIA CR",
                              "GESTÃO SUAS", "ASSIST"]):
        return "ASSISTÊNCIA SOCIAL"

    # Meio Ambiente
    if "FMMA" in r:
        return "MEIO AMBIENTE"

    # Cultura
    if any(k in r for k in ["CULTUR", "FEC", "FUND CULT"]):
        return "CULTURA"

    # Recursos Próprios / Administração
    if any(k in r for k in [" RP", "RP ", "PESSOAL RP", "PESS RP", "PESOAL RP",
                              "PESSOALRP", "PESSOAL/RP", "REC PROP", "RECURSO P",
                              "FPM", "ICMS", "COSIP", "IRRF", "IR MUN", "ISS",
                              "TRIB", "FUNPEQ", "CUSTEIO", "CIDE", "EMENDA EST",
                              "EMENDA PAP", "ATM", "BENEF", "CONF BCOS", "FED BCOS",
                              "CAIXA", "BB", "FEP", "ADO", "RCIDAD", "INVEST"]):
        return "ADMINISTRAÇÃO/RP"
    if r in ("RP", "CUSTEIO", "FUNPEQ", "FPM", "ICMS", "ISS", "IRRF", "BB", "CAIXA"):
        return "ADMINISTRAÇÃO/RP"

    return "OUTROS"


# -----------------------------------------------------------------
# Helpers de normalização
# -----------------------------------------------------------------
MESES_NUM = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8,
    "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
}
MESES_LISTA = list(MESES_NUM.keys())


def norm(txt) -> str:
    if pd.isna(txt):
        return ""
    return re.sub(r"\s+", " ", str(txt).strip())


def norm_upper(txt) -> str:
    return norm(txt).upper()


def limpar_valor(valor) -> float:
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    txt = str(valor).strip().replace("R$", "").replace("r$", "").strip()
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    txt = re.sub(r"[^0-9.\-]", "", txt)
    try:
        return float(txt) if txt else 0.0
    except ValueError:
        return 0.0


def tratar_data(valor):
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (pd.Timestamp, dt.datetime, dt.date)):
        return pd.to_datetime(valor, errors="coerce")
    if isinstance(valor, (int, float)) and 20_000 < float(valor) < 60_000:
        try:
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(float(valor), unit="D")
        except Exception:
            pass
    txt = str(valor).strip()
    if not txt:
        return pd.NaT
    for fmt in [None, "%d/%m/%Y"]:
        parsed = pd.to_datetime(txt, errors="coerce", dayfirst=True, format=fmt)
        if pd.notna(parsed):
            return parsed
    return pd.NaT


def extrair_mes_ano_aba(nome_aba: str) -> tuple[str | None, int | None]:
    nome = norm_upper(nome_aba)
    mes = next((m for m in MESES_LISTA if m in nome), None)
    m_ano = re.search(r"(20\d{2})", nome)
    ano = int(m_ano.group(1)) if m_ano else None
    return mes, ano


def extrair_categoria_cabecalho(cabecalho_desc: str) -> str | None:
    """
    Extrai a secretaria/categoria a partir do nome da coluna de descrição.
    Ex: 'FORNECEDOR/ DESPESA PAGA EDUCAÇÃO' → 'EDUCAÇÃO'
        'FORNECEDOR/ DESPESAS PAGAS SAÚDE'  → 'SAÚDE'
    """
    txt = norm_upper(str(cabecalho_desc))
    # Remove o prefixo padrão
    txt = re.sub(r"FORNECEDOR[/\s]*", "", txt)
    txt = re.sub(r"DESPESAS?\s+PAGAS?\s*", "", txt).strip()
    if txt:
        return txt
    return None


def extrair_favorecido(descricao: str) -> str:
    d = norm_upper(descricao)
    if not d:
        return ""
    padroes = [
        r"^(?:PAGTO|PAGAMENTO)\s+(.+?)(?:\s+NF\b|\s+NFS\b|\s+REF\b|\s+DARF\b|\s+COD\b|\s+\d{1,2}/\d{4}\b|$)",
        r"^REPASSE\s+PARA\s+(.+?)$",
        r"^FOLHA\s+DE\s+PAGAMENTO\s+(.+?)$",
        r"^PAGAMENTO\s+DE\s+(.+?)$",
    ]
    for padrao in padroes:
        m = re.search(padrao, d, flags=re.IGNORECASE)
        if m:
            return re.sub(r"\s+", " ", m.group(1).strip())
    m = re.search(r"^(.+?)(?:\s+NF\b|\s+REF\b|\s+DARF\b|$)", d, flags=re.IGNORECASE)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())
    return d


# -----------------------------------------------------------------
# Detecção de estrutura da aba
# -----------------------------------------------------------------
def _eh_cabecalho(df_raw: pd.DataFrame, i: int) -> bool:
    linha = " | ".join(norm_upper(x) for x in df_raw.iloc[i].tolist())
    return all(kw in linha for kw in ("DATA", "RECURSO", "CONTA", "VALOR"))


def detectar_linha_cabecalho(df_raw: pd.DataFrame) -> int | None:
    """Retorna o índice do PRIMEIRO cabeçalho (compatibilidade)."""
    for i in range(min(20, len(df_raw))):
        if _eh_cabecalho(df_raw, i):
            return i
    return None


def detectar_todos_cabecalhos(df_raw: pd.DataFrame) -> list[int]:
    """Retorna índices de TODOS os cabeçalhos — para abas com múltiplas tabelas."""
    return [i for i in range(len(df_raw)) if _eh_cabecalho(df_raw, i)]


def localizar_colunas(cabecalho: list) -> tuple:
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


# -----------------------------------------------------------------
# Transformação de uma seção (bloco entre dois cabeçalhos)
# -----------------------------------------------------------------
def _processar_secao(df_secao: pd.DataFrame, cabecalho: list,
                     nome_aba: str, categoria_forcada: str | None = None) -> list[dict]:
    """Processa as linhas de dados entre um cabeçalho e o próximo."""
    _, idx_data, idx_recurso, idx_conta, idx_valor = localizar_colunas(cabecalho)
    if any(x is None for x in [idx_data, idx_recurso, idx_conta, idx_valor]):
        return []

    desc_cols = list(range(idx_data + 1, idx_recurso))
    if not desc_cols:
        return []

    categoria_cabecalho = categoria_forcada or extrair_categoria_cabecalho(str(cabecalho[desc_cols[0]]))
    mes_aba, ano_aba = extrair_mes_ano_aba(nome_aba)
    mes_num_aba = MESES_NUM.get(mes_aba)

    linhas = []
    for _, row in df_secao.iterrows():
        recurso = norm_upper(row.iloc[idx_recurso]) if idx_recurso < len(row) else ""
        conta   = norm(row.iloc[idx_conta])         if idx_conta  < len(row) else ""

        desc_partes = [norm(row.iloc[c]) for c in desc_cols if c < len(row) and norm(row.iloc[c])]
        descricao = " ".join(desc_partes).strip()

        if not descricao:
            continue
        desc_up = norm_upper(descricao)
        if any(kw in desc_up for kw in ("TOTAL", "SUBTOTAL")):
            continue

        val_raw = row.iloc[idx_valor] if idx_valor < len(row) else None
        valor   = limpar_valor(val_raw)
        if valor <= 0:
            continue

        data = tratar_data(row.iloc[idx_data] if idx_data < len(row) else None)
        ano  = data.year  if pd.notna(data) else ano_aba
        mes  = data.month if pd.notna(data) else mes_num_aba

        secretaria = categoria_cabecalho if categoria_cabecalho else mapear_secretaria(recurso)

        linhas.append({
            "DATA": data, "ANO": ano, "MES": mes,
            "DESCRICAO": descricao,
            "FAVORECIDO": extrair_favorecido(descricao),
            "RECURSO": recurso, "SECRETARIA": secretaria,
            "CONTA": conta, "VALOR": valor,
            "ABA_ORIGEM": nome_aba,
        })
    return linhas


# -----------------------------------------------------------------
# Transformação de uma aba (suporta múltiplas tabelas verticais)
# -----------------------------------------------------------------
def transformar_aba(df_raw: pd.DataFrame, nome_aba: str) -> pd.DataFrame:
    indices_cab = detectar_todos_cabecalhos(df_raw)
    if not indices_cab:
        raise ValueError(f"[{nome_aba}] Nenhum cabeçalho encontrado.")

    # Delimita seções: de cada cabeçalho até o próximo (ou fim do df)
    limites = indices_cab + [len(df_raw)]
    todas_linhas = []
    for k, i_cab in enumerate(indices_cab):
        cabecalho = df_raw.iloc[i_cab].tolist()
        i_fim = limites[k + 1]
        df_secao = df_raw.iloc[i_cab + 1 : i_fim]
        todas_linhas.extend(_processar_secao(df_secao, cabecalho, nome_aba))

    df = pd.DataFrame(todas_linhas)
    if df.empty:
        return df

    df["ANO"]   = pd.to_numeric(df["ANO"],   errors="coerce")
    df["MES"]   = pd.to_numeric(df["MES"],   errors="coerce")
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0)
    df["DATA"]  = pd.to_datetime(df["DATA"], errors="coerce")

    return df[df["VALOR"] > 0].copy()


# -----------------------------------------------------------------
# Consolida todas as abas
# -----------------------------------------------------------------
def transformar(abas: dict[str, pd.DataFrame], arquivo_origem: str = "") -> pd.DataFrame:
    bases = []
    for nome_aba, df_raw in abas.items():
        try:
            df_aba = transformar_aba(df_raw, nome_aba)
            if not df_aba.empty:
                df_aba["ARQUIVO_ORIGEM"] = arquivo_origem
                bases.append(df_aba)
                print(f"  [transform] '{nome_aba}' — {len(df_aba)} registros válidos")
            else:
                print(f"  [transform] '{nome_aba}' — sem registros válidos")
        except Exception as e:
            print(f"  [transform] ERRO em '{nome_aba}': {e}")

    if not bases:
        return pd.DataFrame()

    base = pd.concat(bases, ignore_index=True)
    return base.sort_values(
        ["ANO", "MES", "DATA", "RECURSO", "VALOR"],
        ascending=[True, True, True, True, False],
    ).reset_index(drop=True)
