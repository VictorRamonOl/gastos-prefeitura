"""
app/views/base_detalhada.py
Aba "Base Detalhada" — tabela completa com busca rápida e exportação.
"""
import streamlit as st
import pandas as pd

from app.helpers import formatar_brl, formatar_data, excel_download


def render(base: pd.DataFrame):
    st.subheader("Base detalhada")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        busca_tab = st.text_input("Busca rápida", key="busca_tab")
    with col_f2:
        top_n = st.selectbox(
            "Exibir",
            [100, 500, 1000, 5000, 0],
            format_func=lambda x: "Todos" if x == 0 else str(x),
        )

    base_view = base.copy()
    if busca_tab:
        b = busca_tab.lower()
        mask = (
            base_view["favorecido"].str.lower().str.contains(b, na=False)
            | base_view["descricao"].str.lower().str.contains(b, na=False)
        )
        base_view = base_view[mask]

    if top_n:
        base_view = base_view.head(top_n)

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
        hide_index=True, use_container_width=True, height=500,
    )

    st.download_button(
        "📥 Exportar Excel (dados filtrados)",
        data=excel_download(base),
        file_name="despesas_filtradas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
