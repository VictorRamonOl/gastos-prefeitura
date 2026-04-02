"""
app/helpers.py
Constantes, formatadores e funções compartilhadas pelo dashboard.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from io import BytesIO

from app.db import query_df

# -----------------------------------------------------------------
# Constantes de meses
# -----------------------------------------------------------------
MESES_NOMES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
MESES_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio",
    6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro",
    11: "Novembro", 12: "Dezembro",
}

# Paleta fixa por secretaria — consistente em todos os gráficos
CORES_FIXAS = [
    "#1565C0", "#E65100", "#2E7D32", "#6A1B9A",
    "#00695C", "#AD1457", "#37474F", "#F9A825",
]


# -----------------------------------------------------------------
# Formatadores
# -----------------------------------------------------------------
def formatar_brl(v: float) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def formatar_mi(v: float) -> str:
    try:
        if v >= 1_000_000:
            return f"R$ {v/1_000_000:,.1f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")
        if v >= 1_000:
            return f"R$ {v/1_000:,.1f} Mil".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatar_brl(v)
    except Exception:
        return "R$ 0,00"


def formatar_data(ts) -> str:
    """Formata Timestamp/NaT para string dd/mm/aaaa sem lançar exceção."""
    if pd.isna(ts):
        return "—"
    try:
        return ts.strftime("%d/%m/%Y")
    except Exception:
        return "—"


def excel_download(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()


# -----------------------------------------------------------------
# Helpers de gráfico (Plotly)
# -----------------------------------------------------------------
def build_color_map(df_base: pd.DataFrame) -> dict:
    secs = sorted(s for s in df_base["secretaria"].dropna().unique() if s.strip())
    return {s: CORES_FIXAS[i % len(CORES_FIXAS)] for i, s in enumerate(secs)}


def bar_layout(height: int = 400, legend: bool = True, font_size: int = 12) -> dict:
    layout = dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=font_size), showgrid=False),
        margin=dict(l=8, r=8, t=32, b=8),
        height=height,
    )
    if legend:
        layout["legend"] = dict(
            orientation="h", y=-0.12, x=0,
            font=dict(size=11), title_text="",
        )
    else:
        layout["showlegend"] = False
    return layout


def safe_periodo(mes_series: pd.Series, ano_series: pd.Series) -> pd.Series:
    """Constrói a coluna 'periodo' (ex: 'Jan/2025') sem lançar erro em NaN."""
    return pd.Series([
        f"{MESES_NOMES.get(int(m), '?')}/{int(a)}"
        if pd.notna(m) and pd.notna(a) else "—"
        for m, a in zip(mes_series, ano_series)
    ], index=mes_series.index)


# -----------------------------------------------------------------
# Carga e filtragem de dados
# -----------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_dados() -> pd.DataFrame:
    df = query_df("""
        SELECT data, ano, mes, descricao, favorecido, recurso, secretaria, conta, valor, aba_origem
        FROM pagamentos ORDER BY ano, mes, data
    """)
    if df.empty:
        return df

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for col in ["ano", "mes", "valor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["favorecido", "recurso", "secretaria", "descricao", "conta"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    # Remove linhas sem ano/mes — não exibíveis nos gráficos
    df = df.dropna(subset=["ano", "mes"])
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)

    df["mes_nome"] = df["mes"].map(MESES_FULL)
    df["periodo"] = safe_periodo(df["mes"], df["ano"])
    return df


def aplicar_filtros(
    df: pd.DataFrame,
    anos: list,
    meses: list,
    secretarias: list,
    recursos: list,
    favorecidos: list,
    busca: str,
) -> pd.DataFrame:
    base = df.copy()
    if anos:
        base = base[base["ano"].isin(anos)]
    if meses:
        base = base[base["mes"].isin(meses)]
    if secretarias:
        base = base[base["secretaria"].isin(secretarias)]
    if recursos:
        base = base[base["recurso"].isin(recursos)]
    if favorecidos:
        base = base[base["favorecido"].isin(favorecidos)]
    if busca:
        b = busca.strip().lower()
        mask = (
            base["favorecido"].str.lower().str.contains(b, na=False)
            | base["descricao"].str.lower().str.contains(b, na=False)
            | base["recurso"].str.lower().str.contains(b, na=False)
        )
        base = base[mask]
    return base
