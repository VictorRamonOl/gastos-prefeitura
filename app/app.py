"""
app/app.py
Dashboard principal — Gastos da Prefeitura.
Rodar com: streamlit run app/app.py
"""
import sys
from pathlib import Path

# Garante que a raiz do projeto está no sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

from app.auth import login_requerido, usuario_atual, is_admin, logout
from app.db import query_df

# -----------------------------------------------------------------
# Config da página
# -----------------------------------------------------------------
st.set_page_config(
    page_title="Gastos Prefeitura",
    page_icon="📊",
    layout="wide",
)

# -----------------------------------------------------------------
# Autenticação — bloqueia o app se não estiver logado
# -----------------------------------------------------------------
login_requerido()

MESES_NOMES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


# -----------------------------------------------------------------
# Carga de dados (com cache)
# -----------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_dados() -> pd.DataFrame:
    df = query_df("""
        SELECT
            data, ano, mes, descricao, favorecido, recurso, conta, valor, aba_origem
        FROM pagamentos
        ORDER BY ano, mes, data
    """)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for col in ["ano", "mes", "valor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["favorecido", "recurso", "descricao", "conta", "aba_origem"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    df["mes_nome"] = df["mes"].map(MESES_NOMES)
    return df


def formatar_brl(valor: float) -> str:
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def excel_download(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="dados_filtrados", index=False)
    return buf.getvalue()


def aplicar_filtros(df, anos, meses, recursos, favorecidos, busca) -> pd.DataFrame:
    base = df.copy()
    if anos:
        base = base[base["ano"].isin(anos)]
    if meses:
        base = base[base["mes"].isin(meses)]
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


# -----------------------------------------------------------------
# Cabeçalho e logout
# -----------------------------------------------------------------
usuario = usuario_atual()
col_titulo, col_usuario = st.columns([6, 1])
with col_titulo:
    st.title("📊 Dashboard de Despesas da Prefeitura")
with col_usuario:
    st.markdown(f"**{usuario.get('nome') or usuario.get('username')}**")
    if st.button("Sair", use_container_width=True):
        logout()

st.markdown("---")

# -----------------------------------------------------------------
# Carga
# -----------------------------------------------------------------
try:
    df = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if df.empty:
    st.warning("Nenhum dado no banco. Execute o ETL primeiro: `python etl/run_etl.py`")
    st.stop()

# -----------------------------------------------------------------
# Sidebar — Filtros
# -----------------------------------------------------------------
st.sidebar.header("Filtros")

anos_disp = sorted(df["ano"].dropna().unique().astype(int).tolist())
meses_disp = sorted(df["mes"].dropna().unique().astype(int).tolist())
recursos_disp = sorted(x for x in df["recurso"].dropna().unique() if x.strip())
favs_disp = sorted(x for x in df["favorecido"].dropna().unique() if x.strip())

anos_sel = st.sidebar.multiselect("Ano", anos_disp, default=anos_disp)
meses_sel = st.sidebar.multiselect(
    "Mês", meses_disp, default=[],
    format_func=lambda x: MESES_NOMES.get(x, str(x)),
)
recursos_sel = st.sidebar.multiselect("Recurso", recursos_disp, default=[])
favs_sel = st.sidebar.multiselect("Favorecido", favs_disp, default=[])
busca_texto = st.sidebar.text_input("Buscar texto")

base = aplicar_filtros(df, anos_sel, meses_sel, recursos_sel, favs_sel, busca_texto)

if base.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# -----------------------------------------------------------------
# KPIs
# -----------------------------------------------------------------
total = base["valor"].sum()
qtd = len(base)
qtd_favs = base["favorecido"].nunique()
media = base["valor"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor total", formatar_brl(total))
c2.metric("Lançamentos", f"{qtd:,}".replace(",", "."))
c3.metric("Favorecidos únicos", f"{qtd_favs:,}".replace(",", "."))
c4.metric("Valor médio", formatar_brl(media))

# -----------------------------------------------------------------
# Gráficos
# -----------------------------------------------------------------
gasto_mensal = (
    base.groupby(["ano", "mes"], as_index=False)["valor"]
    .sum()
    .sort_values(["ano", "mes"])
)
gasto_mensal["periodo"] = (
    gasto_mensal["mes"].map(MESES_NOMES) + "/" + gasto_mensal["ano"].astype(int).astype(str)
)

top_favs = (
    base.groupby("favorecido", as_index=False)["valor"]
    .sum()
    .sort_values("valor", ascending=False)
    .head(15)
)

gasto_recurso = (
    base.groupby("recurso", as_index=False)["valor"]
    .sum()
    .sort_values("valor", ascending=False)
)

g1, g2 = st.columns(2)
with g1:
    fig1 = px.bar(gasto_mensal, x="periodo", y="valor", title="Gasto por mês", text_auto=".2s")
    fig1.update_layout(xaxis_title="", yaxis_title="Valor (R$)")
    st.plotly_chart(fig1, use_container_width=True)

with g2:
    fig2 = px.pie(
        gasto_recurso.head(10), names="recurso", values="valor", title="Distribuição por recurso"
    )
    st.plotly_chart(fig2, use_container_width=True)

g3, g4 = st.columns(2)
with g3:
    fig3 = px.bar(
        top_favs, x="valor", y="favorecido", orientation="h",
        title="Top 15 favorecidos", text_auto=".2s"
    )
    fig3.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

with g4:
    rec_qtd = (
        base.groupby("recurso", as_index=False)
        .agg(valor_total=("valor", "sum"), qtd_favs=("favorecido", "nunique"))
        .sort_values("valor_total", ascending=False)
    )
    fig4 = px.bar(rec_qtd, x="recurso", y="qtd_favs",
                  title="Favorecidos únicos por recurso", text_auto=True)
    fig4.update_layout(xaxis_title="", yaxis_title="Qtd. favorecidos")
    st.plotly_chart(fig4, use_container_width=True)

# -----------------------------------------------------------------
# Abas de detalhe
# -----------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Resumo", "Favorecido × Recurso", "Base detalhada"])

with tab1:
    a, b = st.columns(2)
    with a:
        st.subheader("Por favorecido")
        res_fav = (
            base.groupby("favorecido", as_index=False)
            .agg(qtd=("valor", "count"), valor_total=("valor", "sum"))
            .sort_values("valor_total", ascending=False)
        )
        res_fav["valor_fmt"] = res_fav["valor_total"].apply(formatar_brl)
        st.dataframe(res_fav[["favorecido", "qtd", "valor_fmt"]], hide_index=True, use_container_width=True)
    with b:
        st.subheader("Por recurso")
        res_rec = (
            base.groupby("recurso", as_index=False)
            .agg(qtd=("valor", "count"), valor_total=("valor", "sum"), qtd_favs=("favorecido", "nunique"))
            .sort_values("valor_total", ascending=False)
        )
        res_rec["valor_fmt"] = res_rec["valor_total"].apply(formatar_brl)
        st.dataframe(res_rec[["recurso", "qtd", "qtd_favs", "valor_fmt"]], hide_index=True, use_container_width=True)

with tab2:
    fav_rec = (
        base.groupby(["favorecido", "recurso"], as_index=False)
        .agg(qtd=("valor", "count"), valor_total=("valor", "sum"))
        .sort_values("valor_total", ascending=False)
    )
    fav_rec["valor_fmt"] = fav_rec["valor_total"].apply(formatar_brl)
    st.dataframe(fav_rec[["favorecido", "recurso", "qtd", "valor_fmt"]], hide_index=True, use_container_width=True)

with tab3:
    base_view = base.copy()
    if "data" in base_view.columns:
        base_view["data_fmt"] = base_view["data"].dt.strftime("%d/%m/%Y")
    base_view["valor_fmt"] = base_view["valor"].apply(formatar_brl)
    cols = [c for c in ["data_fmt", "ano", "mes", "favorecido", "recurso", "conta", "valor_fmt", "descricao"] if c in base_view.columns]
    st.dataframe(base_view[cols], hide_index=True, use_container_width=True)

# -----------------------------------------------------------------
# Download
# -----------------------------------------------------------------
st.markdown("---")
st.subheader("Exportar dados filtrados")
st.download_button(
    label="📥 Baixar Excel filtrado",
    data=excel_download(base),
    file_name="despesas_filtradas.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# -----------------------------------------------------------------
# Painel admin (só para admins)
# -----------------------------------------------------------------
if is_admin():
    st.markdown("---")
    with st.expander("⚙️ Painel Admin"):
        st.subheader("Últimas importações")
        try:
            logs = query_df("""
                SELECT nome_arquivo, total_linhas, linhas_inseridas, linhas_duplicadas, status, importado_em
                FROM arquivos_importados
                ORDER BY importado_em DESC
                LIMIT 20
            """)
            st.dataframe(logs, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar logs: {e}")

        st.subheader("Usuários cadastrados")
        try:
            usuarios = query_df("""
                SELECT username, nome, perfil, ativo,
                       DATE_FORMAT(criado_em, '%d/%m/%Y') as criado_em,
                       DATE_FORMAT(ultimo_acesso, '%d/%m/%Y %H:%i') as ultimo_acesso
                FROM usuarios
                ORDER BY criado_em DESC
            """)
            st.dataframe(usuarios, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
