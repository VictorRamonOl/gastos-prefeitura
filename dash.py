import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from pathlib import Path

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Dashboard de Fornecedores - Prefeitura",
    page_icon="📊",
    layout="wide"
)

ARQUIVO_DADOS = Path(r"D:\Documents\0. Automações\Gastos prefeitura - Maior Fornecedor\DESPESAS_PREFEITURA_TRATADAS.xlsx")

MESES_NOMES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

# =========================================================
# FUNÇÕES
# =========================================================
@st.cache_data
def carregar_dados():
    if not ARQUIVO_DADOS.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_DADOS}")

    # agora usa BASE_FORNECEDORES
    df = pd.read_excel(ARQUIVO_DADOS, sheet_name="BASE_FORNECEDORES")

    if "DATA" in df.columns:
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    for col in ["ANO", "MES", "VALOR"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["FORNECEDOR", "RECURSO", "DESCRICAO", "CONTA", "CLASSE", "ABA_ORIGEM"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["MES_NOME"] = df["MES"].map(MESES_NOMES)

    return df


def formatar_brl(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def criar_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="dados_filtrados", index=False)
    output.seek(0)
    return output


def aplicar_filtros(df, anos, meses, recursos, fornecedores, busca):
    base = df.copy()

    if anos:
        base = base[base["ANO"].isin(anos)]

    if meses:
        base = base[base["MES"].isin(meses)]

    if recursos:
        base = base[base["RECURSO"].isin(recursos)]

    if fornecedores:
        base = base[base["FORNECEDOR"].isin(fornecedores)]

    if busca:
        busca = busca.strip().lower()
        base = base[
            base["FORNECEDOR"].str.lower().str.contains(busca, na=False) |
            base["DESCRICAO"].str.lower().str.contains(busca, na=False) |
            base["RECURSO"].str.lower().str.contains(busca, na=False)
        ]

    return base

# =========================================================
# CARGA
# =========================================================
try:
    df = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
    st.stop()

# =========================================================
# TÍTULO
# =========================================================
st.title("📊 Dashboard de Fornecedores da Prefeitura")
st.caption("Análise apenas dos lançamentos classificados como fornecedor")

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Filtros")

anos_disp = sorted([int(x) for x in df["ANO"].dropna().unique()])
meses_disp = sorted([int(x) for x in df["MES"].dropna().unique()])
recursos_disp = sorted([x for x in df["RECURSO"].dropna().unique() if str(x).strip() != ""])
fornecedores_disp = sorted([x for x in df["FORNECEDOR"].dropna().unique() if str(x).strip() != ""])

anos_sel = st.sidebar.multiselect("Ano", anos_disp, default=anos_disp)
meses_sel = st.sidebar.multiselect(
    "Mês",
    meses_disp,
    default=[],
    format_func=lambda x: MESES_NOMES.get(x, str(x))
)
recursos_sel = st.sidebar.multiselect("Recurso", recursos_disp, default=[])
fornecedores_sel = st.sidebar.multiselect("Fornecedor", fornecedores_disp, default=[])
busca_texto = st.sidebar.text_input("Buscar texto")

# =========================================================
# FILTROS
# =========================================================
base = aplicar_filtros(
    df,
    anos=anos_sel,
    meses=meses_sel,
    recursos=recursos_sel,
    fornecedores=fornecedores_sel,
    busca=busca_texto
)

if base.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# =========================================================
# KPIs
# =========================================================
total_gasto = base["VALOR"].sum()
qtd_lancamentos = len(base)
qtd_fornecedores = base["FORNECEDOR"].nunique()
ticket_medio = base["VALOR"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor total", formatar_brl(total_gasto))
c2.metric("Lançamentos", f"{qtd_lancamentos:,}".replace(",", "."))
c3.metric("Fornecedores únicos", f"{qtd_fornecedores:,}".replace(",", "."))
c4.metric("Valor médio", formatar_brl(ticket_medio))

# =========================================================
# AGREGAÇÕES
# =========================================================
gasto_mensal = (
    base.groupby(["ANO", "MES"], as_index=False)["VALOR"]
    .sum()
    .sort_values(["ANO", "MES"])
)
gasto_mensal["PERIODO"] = gasto_mensal["MES"].map(MESES_NOMES) + "/" + gasto_mensal["ANO"].astype(int).astype(str)

top_fornecedores = (
    base.groupby("FORNECEDOR", as_index=False)["VALOR"]
    .sum()
    .sort_values("VALOR", ascending=False)
    .head(15)
)

gasto_recurso = (
    base.groupby("RECURSO", as_index=False)["VALOR"]
    .sum()
    .sort_values("VALOR", ascending=False)
)

fornecedor_recurso = (
    base.groupby(["FORNECEDOR", "RECURSO"], as_index=False)
    .agg(
        VALOR_TOTAL=("VALOR", "sum"),
        QTD=("VALOR", "count")
    )
    .sort_values("VALOR_TOTAL", ascending=False)
)

# =========================================================
# GRÁFICOS
# =========================================================
g1, g2 = st.columns(2)

with g1:
    fig1 = px.bar(
        gasto_mensal,
        x="PERIODO",
        y="VALOR",
        title="Gasto por mês",
        text_auto=".2s"
    )
    fig1.update_layout(xaxis_title="", yaxis_title="Valor")
    st.plotly_chart(fig1, use_container_width=True)

with g2:
    fig2 = px.pie(
        gasto_recurso.head(10),
        names="RECURSO",
        values="VALOR",
        title="Distribuição por recurso"
    )
    st.plotly_chart(fig2, use_container_width=True)

g3, g4 = st.columns(2)

with g3:
    fig3 = px.bar(
        top_fornecedores,
        x="VALOR",
        y="FORNECEDOR",
        orientation="h",
        title="Top 15 fornecedores",
        text_auto=".2s"
    )
    fig3.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

with g4:
    top_recursos_forn = (
        base.groupby("RECURSO", as_index=False)
        .agg(
            VALOR_TOTAL=("VALOR", "sum"),
            QTD_FORNECEDORES=("FORNECEDOR", "nunique")
        )
        .sort_values("VALOR_TOTAL", ascending=False)
    )

    fig4 = px.bar(
        top_recursos_forn,
        x="RECURSO",
        y="QTD_FORNECEDORES",
        title="Quantidade de fornecedores por recurso",
        text_auto=True
    )
    fig4.update_layout(xaxis_title="", yaxis_title="Qtd. fornecedores")
    st.plotly_chart(fig4, use_container_width=True)

# =========================================================
# ABAS
# =========================================================
tab1, tab2, tab3 = st.tabs(["Resumo", "Fornecedor x Recurso", "Base detalhada"])

with tab1:
    a, b = st.columns(2)

    with a:
        st.subheader("Resumo por fornecedor")
        resumo_fornecedor = (
            base.groupby("FORNECEDOR", as_index=False)
            .agg(
                QTD=("VALOR", "count"),
                VALOR_TOTAL=("VALOR", "sum")
            )
            .sort_values("VALOR_TOTAL", ascending=False)
        )
        resumo_fornecedor["VALOR_TOTAL_FMT"] = resumo_fornecedor["VALOR_TOTAL"].apply(formatar_brl)
        st.dataframe(
            resumo_fornecedor[["FORNECEDOR", "QTD", "VALOR_TOTAL_FMT"]],
            use_container_width=True,
            hide_index=True
        )

    with b:
        st.subheader("Resumo por recurso")
        resumo_recurso = (
            base.groupby("RECURSO", as_index=False)
            .agg(
                QTD=("VALOR", "count"),
                VALOR_TOTAL=("VALOR", "sum"),
                QTD_FORNECEDORES=("FORNECEDOR", "nunique")
            )
            .sort_values("VALOR_TOTAL", ascending=False)
        )
        resumo_recurso["VALOR_TOTAL_FMT"] = resumo_recurso["VALOR_TOTAL"].apply(formatar_brl)
        st.dataframe(
            resumo_recurso[["RECURSO", "QTD", "QTD_FORNECEDORES", "VALOR_TOTAL_FMT"]],
            use_container_width=True,
            hide_index=True
        )

with tab2:
    st.subheader("Fornecedor x Recurso")
    fornecedor_recurso["VALOR_TOTAL_FMT"] = fornecedor_recurso["VALOR_TOTAL"].apply(formatar_brl)
    st.dataframe(
        fornecedor_recurso[["FORNECEDOR", "RECURSO", "QTD", "VALOR_TOTAL_FMT"]],
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.subheader("Base detalhada")
    base_view = base.copy()
    if "DATA" in base_view.columns:
        base_view["DATA"] = base_view["DATA"].dt.strftime("%d/%m/%Y")
    base_view["VALOR_FMT"] = base_view["VALOR"].apply(formatar_brl)

    cols = [c for c in [
        "DATA", "ANO", "MES", "FORNECEDOR", "RECURSO",
        "CONTA", "VALOR_FMT", "DESCRICAO", "ABA_ORIGEM"
    ] if c in base_view.columns]

    st.dataframe(
        base_view[cols],
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# DOWNLOAD
# =========================================================
st.markdown("---")
st.subheader("Exportar dados filtrados")

arquivo_excel = criar_excel_download(base)
st.download_button(
    label="📥 Baixar Excel filtrado",
    data=arquivo_excel,
    file_name="fornecedores_filtrados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)