"""
app/views/rankings.py
Aba "Rankings" — top favorecidos geral, por secretaria e por mês.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import MESES_NOMES, formatar_brl, safe_periodo


def render(base: pd.DataFrame):
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.subheader("🏆 Top 15 Favorecidos")
        top_fav = (
            base.groupby("favorecido", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False).head(15)
        )
        fig_top = px.bar(
            top_fav, x="valor", y="favorecido", orientation="h", text_auto=".3s",
            color_discrete_sequence=["#2ca02c"],
        )
        fig_top.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Valor (R$)", yaxis_title="",
            plot_bgcolor="white", height=500,
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with col_r2:
        st.subheader("📦 Top 15 Favorecidos × Secretaria")
        fav_sec_r = (
            base.groupby(["favorecido", "secretaria"], as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False).head(20)
        )
        fig_fsr = px.bar(
            fav_sec_r, x="valor", y="favorecido", color="secretaria",
            orientation="h", text_auto=".3s",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_fsr.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Valor (R$)", yaxis_title="",
            plot_bgcolor="white", height=500, legend_title="Secretaria",
        )
        st.plotly_chart(fig_fsr, use_container_width=True)

    st.subheader("📅 Top favorecido por mês")
    top_mes = (
        base.groupby(["ano", "mes", "favorecido"], as_index=False)["valor"].sum()
    )
    if not top_mes.empty:
        idx_max = top_mes.groupby(["ano", "mes"])["valor"].idxmax()
        top_mes_winner = top_mes.loc[idx_max].sort_values(["ano", "mes"]).copy()
        top_mes_winner["periodo"] = safe_periodo(top_mes_winner["mes"], top_mes_winner["ano"])
        top_mes_winner["valor_fmt"] = top_mes_winner["valor"].apply(formatar_brl)
        st.dataframe(
            top_mes_winner[["periodo", "favorecido", "valor_fmt"]].rename(
                columns={
                    "periodo": "Período",
                    "favorecido": "Maior Favorecido",
                    "valor_fmt": "Valor",
                }
            ),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("Sem dados para o ranking mensal.")
