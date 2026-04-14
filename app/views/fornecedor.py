"""
app/views/fornecedor.py
Aba "Por Fornecedor" — análise detalhada de um fornecedor específico.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import (
    MESES_NOMES, MESES_FULL,
    formatar_brl, formatar_mi, formatar_data, excel_download,
    safe_periodo, sem_transferencias,
)


def render(base: pd.DataFrame):
    st.subheader("🏢 Análise por Fornecedor")

    base = sem_transferencias(base)

    rank_fav = (
        base.groupby("favorecido", as_index=False)["valor"]
        .sum().sort_values("valor", ascending=False)
    )
    rank_fav = rank_fav[rank_fav["favorecido"].str.strip() != ""]

    if rank_fav.empty:
        st.info("Nenhum fornecedor nos dados filtrados.")
        return

    rank_fav["label"] = rank_fav.apply(
        lambda r: f"{r['favorecido']}  ({formatar_mi(r['valor'])})", axis=1
    )
    label_map = dict(zip(rank_fav["favorecido"], rank_fav["label"]))

    forn_sel = st.selectbox(
        "Selecione o Fornecedor",
        rank_fav["favorecido"].tolist(),
        format_func=lambda f: label_map.get(f, f),
        key="forn_sel",
    )

    base_forn = base[base["favorecido"] == forn_sel]

    # ── KPIs ──────────────────────────────────────────────────────
    anos_forn = base_forn["ano"].dropna()
    if not anos_forn.empty:
        periodo_str = f"{int(anos_forn.min())} – {int(anos_forn.max())}"
    else:
        periodo_str = "—"

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Total recebido", formatar_mi(base_forn["valor"].sum()))
    f2.metric("Lançamentos", f'{len(base_forn):,}'.replace(",", "."))
    f3.metric("Secretarias atendidas", str(base_forn["secretaria"].nunique()))
    f4.metric("Período", periodo_str)

    st.markdown("---")

    # ── Evolução anual e mensal ───────────────────────────────────
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("**Recebido por Ano**")
        por_ano = base_forn.groupby("ano", as_index=False)["valor"].sum()
        fig_ano = px.bar(
            por_ano, x="ano", y="valor",
            color_discrete_sequence=["#1f77b4"],
        )
        fig_ano.update_traces(
            texttemplate="R$ %{y:.3s}", textposition="outside",
        )
        fig_ano.update_layout(
            xaxis_title="Ano", yaxis_title="R$",
            plot_bgcolor="white",
            xaxis=dict(tickmode="array", tickvals=por_ano["ano"].tolist()),
        )
        st.plotly_chart(fig_ano, use_container_width=True)

    with col_f2:
        st.markdown("**Recebido por Mês/Ano**")
        por_mes = (
            base_forn.groupby(["ano", "mes"], as_index=False)["valor"]
            .sum().sort_values(["ano", "mes"])
        )
        por_mes["periodo"] = safe_periodo(por_mes["mes"], por_mes["ano"])
        fig_mes_f = px.bar(
            por_mes, x="periodo", y="valor",
            color_discrete_sequence=["#ff7f0e"],
        )
        fig_mes_f.update_layout(
            xaxis_title="", yaxis_title="R$", plot_bgcolor="white",
        )
        st.plotly_chart(fig_mes_f, use_container_width=True)

    # ── Distribuição por secretaria e recurso ─────────────────────
    col_f3, col_f4 = st.columns(2)

    with col_f3:
        st.markdown("**Por Secretaria**")
        sec_forn = (
            base_forn.groupby("secretaria", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False)
        )
        fig_sec_f = px.pie(
            sec_forn, names="secretaria", values="valor",
            hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_sec_f.update_traces(textinfo="label+percent")
        st.plotly_chart(fig_sec_f, use_container_width=True)

    with col_f4:
        st.markdown("**Por Recurso (fonte)**")
        rec_forn = (
            base_forn.groupby("recurso", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False).head(10)
        )
        fig_rec_f = px.bar(
            rec_forn, x="valor", y="recurso", orientation="h",
            color_discrete_sequence=["#9467bd"],
        )
        fig_rec_f.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="R$", yaxis_title="", plot_bgcolor="white",
        )
        st.plotly_chart(fig_rec_f, use_container_width=True)

    # ── Pagamentos por ano (expansíveis) ─────────────────────────
    st.markdown("---")
    st.markdown(f"**Todos os pagamentos de _{forn_sel}_**")

    pag_forn = base_forn.copy().sort_values(["ano", "mes", "data"])
    pag_forn["data_fmt"] = pag_forn["data"].apply(formatar_data)
    pag_forn["valor_fmt"] = pag_forn["valor"].apply(formatar_brl)

    ano_max = int(pag_forn["ano"].max()) if not pag_forn.empty else None
    for ano_val in sorted(pag_forn["ano"].unique().astype(int)):
        df_ano = pag_forn[pag_forn["ano"] == ano_val]
        total_ano = df_ano["valor"].sum()
        with st.expander(
            f"📅 {ano_val}  —  {formatar_mi(total_ano)}  ({len(df_ano)} lançamentos)",
            expanded=(ano_val == ano_max),
        ):
            res_mes_ano = (
                df_ano.groupby("mes", as_index=False)["valor"]
                .sum().sort_values("mes")
            )
            res_mes_ano["mes_nome"] = res_mes_ano["mes"].map(MESES_FULL)
            res_mes_ano["total_fmt"] = res_mes_ano["valor"].apply(formatar_brl)

            st.dataframe(
                res_mes_ano[["mes_nome", "total_fmt"]].rename(
                    columns={"mes_nome": "Mês", "total_fmt": "Total"}
                ),
                hide_index=True, use_container_width=True, height=200,
            )

            st.markdown("**Lançamentos individuais**")
            st.dataframe(
                df_ano[[
                    "data_fmt", "mes_nome", "secretaria",
                    "recurso", "valor_fmt", "descricao",
                ]].rename(columns={
                    "data_fmt": "Data", "mes_nome": "Mês",
                    "secretaria": "Secretaria", "recurso": "Recurso",
                    "valor_fmt": "Valor", "descricao": "Descrição",
                }),
                hide_index=True, use_container_width=True,
            )

    st.download_button(
        f"📥 Exportar tudo de {forn_sel[:30]}",
        data=excel_download(
            pag_forn[[
                "data_fmt", "ano", "mes_nome", "secretaria",
                "recurso", "valor_fmt", "valor", "descricao",
            ]].rename(columns={
                "data_fmt": "Data", "ano": "Ano", "mes_nome": "Mês",
                "secretaria": "Secretaria", "recurso": "Recurso",
                "valor_fmt": "Valor Formatado", "valor": "Valor",
                "descricao": "Descrição",
            })
        ),
        file_name=f"fornecedor_{forn_sel[:40].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_forn",
    )
