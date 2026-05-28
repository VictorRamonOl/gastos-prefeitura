"""
app/views/base_detalhada.py
Aba "Base Detalhada" — tabela completa com busca rápida e exportação.
"""
import streamlit as st
import pandas as pd

from app.helpers import formatar_brl, formatar_data, excel_download
from app.ui import section_title


def render(base: pd.DataFrame):
    section_title("Base detalhada — todos os lançamentos")
    st.caption(
        "Tabela completa. Use a busca abaixo OU clique no cabeçalho de uma coluna para ordenar. "
        "Exporte com o botão Excel ao final."
    )

    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        busca_tab = st.text_input(
            "🔍 Busca rápida (favorecido ou descrição)",
            placeholder="ex: hospital, combustível, FKR…",
            key="busca_tab",
        )
    with col_f2:
        top_n = st.selectbox(
            "Linhas exibidas",
            [100, 500, 1000, 5000, 0],
            format_func=lambda x: "Todas" if x == 0 else f"{x:,}".replace(",", "."),
            help="Limita o número de linhas mostradas — a busca e o export continuam aplicando sobre todos os dados.",
        )

    base_view = base.copy()
    if busca_tab:
        b = busca_tab.lower()
        mask = (
            base_view["favorecido"].str.lower().str.contains(b, na=False)
            | base_view["descricao"].str.lower().str.contains(b, na=False)
        )
        base_view = base_view[mask]

    total_filtrado = base_view["valor"].sum()
    qtd_filtrado = len(base_view)

    if top_n:
        base_view = base_view.head(top_n)

    k1, k2, k3 = st.columns(3)
    k1.metric("Lançamentos no resultado", f"{qtd_filtrado:,}".replace(",", "."))
    k2.metric("Total no resultado", f"R$ {total_filtrado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    k3.metric("Exibindo", f"{len(base_view):,}".replace(",", "."))

    base_view["data_fmt"] = base_view["data"].apply(formatar_data)
    base_view["valor_fmt"] = base_view["valor"].apply(formatar_brl)

    st.dataframe(
        base_view[[
            "data_fmt", "ano", "mes_nome", "secretaria", "favorecido",
            "recurso", "valor_fmt", "descricao",
        ]].rename(columns={
            "data_fmt": "Data", "ano": "Ano", "mes_nome": "Mês",
            "secretaria": "Secretaria", "favorecido": "Favorecido",
            "recurso": "Recurso", "valor_fmt": "Valor", "descricao": "Descrição",
        }),
        hide_index=True, use_container_width=True, height=560,
    )

    st.download_button(
        "📥 Exportar Excel (dados filtrados)",
        data=excel_download(base),
        file_name="despesas_filtradas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
