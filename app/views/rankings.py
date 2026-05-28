"""
app/views/rankings.py
Aba "Rankings" — top favorecidos geral, por secretaria e por mês.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import (
    MESES_NOMES, formatar_brl, formatar_mi, safe_periodo, sem_transferencias,
    bar_layout,
)
from app.ui import section_title, PALETA_EXEC


def render(base: pd.DataFrame):
    base = sem_transferencias(base)

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        section_title("Top 15 favorecidos")
        st.caption("Os 15 que mais receberam no período (exclui transferências entre contas).")
        top_fav = (
            base.groupby("favorecido", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False).head(15)
        ).sort_values("valor", ascending=True)
        top_fav["label"] = top_fav["valor"].apply(formatar_mi)
        top_fav["nome_curto"] = top_fav["favorecido"].str[:45]
        fig_top = px.bar(
            top_fav, x="valor", y="nome_curto", orientation="h",
            text="label",
            color_discrete_sequence=[PALETA_EXEC[1]],
        )
        fig_top.update_traces(
            textposition="outside",
            textfont=dict(size=11, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=520, legend=False, font_size=11)
        if not top_fav.empty:
            layout["xaxis"]["range"] = [0, top_fav["valor"].max() * 1.20]
        fig_top.update_layout(**layout)
        st.plotly_chart(fig_top, use_container_width=True)

    with col_r2:
        section_title("Top 20 favorecidos × secretaria")
        st.caption("Combinações de quem recebeu de quem. Mesmo nome pode aparecer em secretarias diferentes.")
        fav_sec_r = (
            base.groupby(["favorecido", "secretaria"], as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False).head(20)
        ).sort_values("valor", ascending=True)
        fav_sec_r["label"] = fav_sec_r["valor"].apply(formatar_mi)
        fav_sec_r["nome_curto"] = fav_sec_r["favorecido"].str[:45]
        fig_fsr = px.bar(
            fav_sec_r, x="valor", y="nome_curto", color="secretaria",
            orientation="h",
            text="label",
            color_discrete_sequence=PALETA_EXEC,
        )
        fig_fsr.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=520, font_size=11)
        if not fav_sec_r.empty:
            layout["xaxis"]["range"] = [0, fav_sec_r["valor"].max() * 1.20]
        fig_fsr.update_layout(**layout)
        st.plotly_chart(fig_fsr, use_container_width=True)

    section_title("Maior favorecido por mês")
    st.caption("Quem foi o maior recebedor em cada mês do período.")
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
