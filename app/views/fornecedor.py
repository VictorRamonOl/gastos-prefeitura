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
    bar_layout, time_layout,
)
from app.ui import section_title, page_header, PALETA_EXEC


def render(base: pd.DataFrame):
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
        "Selecione o fornecedor",
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

    page_header(forn_sel, f"{len(base_forn):,} pagamentos".replace(",", "."))
    st.caption(
        "Use o seletor acima para escolher outro fornecedor. "
        "A lista está ordenada do maior para o menor recebedor."
    )

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Total recebido", formatar_mi(base_forn["valor"].sum()))
    f2.metric("Lançamentos", f'{len(base_forn):,}'.replace(",", "."))
    f3.metric("Secretarias atendidas", str(base_forn["secretaria"].nunique()))
    f4.metric("Período", periodo_str)

    # ── Evolução anual e mensal ───────────────────────────────────
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        section_title("Recebido por ano")
        por_ano = base_forn.groupby("ano", as_index=False)["valor"].sum()
        por_ano["label"] = por_ano["valor"].apply(formatar_mi)
        fig_ano = px.bar(
            por_ano, x="ano", y="valor",
            text="label",
            color_discrete_sequence=[PALETA_EXEC[0]],
        )
        fig_ano.update_traces(
            textposition="outside",
            textfont=dict(size=11, color="#aab4c4"),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        )
        layout = time_layout(height=320, show_y_ticks=False)
        layout["xaxis"]["tickmode"] = "array"
        layout["xaxis"]["tickvals"] = por_ano["ano"].tolist()
        if not por_ano.empty:
            layout["yaxis"]["range"] = [0, por_ano["valor"].max() * 1.20]
        fig_ano.update_layout(**layout)
        st.plotly_chart(fig_ano, use_container_width=True)

    with col_f2:
        section_title("Recebido por mês")
        por_mes = (
            base_forn.groupby(["ano", "mes"], as_index=False)["valor"]
            .sum().sort_values(["ano", "mes"])
        )
        por_mes["periodo"] = safe_periodo(por_mes["mes"], por_mes["ano"])
        por_mes["label"] = por_mes["valor"].apply(formatar_mi)
        fig_mes_f = px.bar(
            por_mes, x="periodo", y="valor",
            text="label",
            color_discrete_sequence=[PALETA_EXEC[2]],
        )
        fig_mes_f.update_traces(
            textposition="outside",
            textfont=dict(size=10, color="#aab4c4"),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        )
        layout = time_layout(height=320, show_y_ticks=False)
        if not por_mes.empty:
            layout["yaxis"]["range"] = [0, por_mes["valor"].max() * 1.25]
        fig_mes_f.update_layout(**layout)
        st.plotly_chart(fig_mes_f, use_container_width=True)

    # ── Distribuição por secretaria e recurso ─────────────────────
    col_f3, col_f4 = st.columns(2)

    with col_f3:
        section_title("Distribuição por secretaria")
        st.caption("De quais secretarias este fornecedor recebe.")
        sec_forn = (
            base_forn.groupby("secretaria", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False)
        )
        fig_sec_f = px.pie(
            sec_forn, names="secretaria", values="valor",
            hole=0.55, color_discrete_sequence=PALETA_EXEC,
        )
        fig_sec_f.update_traces(
            textinfo="percent",
            textfont=dict(size=12, color="#ffffff"),
            marker=dict(line=dict(color="#0b0e14", width=2)),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}  (%{percent})<extra></extra>",
        )
        fig_sec_f.update_layout(
            font=dict(family="Inter", color="#e6edf6"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=360, margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(
                orientation="v", y=0.5, x=1.02,
                font=dict(size=11, color="#aab4c4"),
                bgcolor="rgba(0,0,0,0)",
            ),
            hoverlabel=dict(
                bgcolor="#1a1f2b", bordercolor="rgba(255,255,255,0.10)",
                font=dict(family="Inter", color="#e6edf6"),
            ),
        )
        st.plotly_chart(fig_sec_f, use_container_width=True)

    with col_f4:
        section_title("Top fontes de recurso")
        st.caption("De qual recurso (fundo, ICMS etc) saiu o dinheiro pago a este fornecedor.")
        rec_forn = (
            base_forn.groupby("recurso", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False).head(10)
        )
        rec_forn = rec_forn[rec_forn["recurso"].str.strip() != ""]
        rec_forn["label"] = rec_forn["valor"].apply(formatar_mi)
        fig_rec_f = px.bar(
            rec_forn.sort_values("valor", ascending=True),
            x="valor", y="recurso", orientation="h",
            text="label",
            color_discrete_sequence=[PALETA_EXEC[3]],
        )
        fig_rec_f.update_traces(
            textposition="outside",
            textfont=dict(size=11, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=360, legend=False, font_size=11)
        if not rec_forn.empty:
            layout["xaxis"]["range"] = [0, rec_forn["valor"].max() * 1.22]
        fig_rec_f.update_layout(**layout)
        st.plotly_chart(fig_rec_f, use_container_width=True)

    # ── Pagamentos por ano (expansíveis) ─────────────────────────
    section_title(f"Pagamentos detalhados — {forn_sel}")

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
