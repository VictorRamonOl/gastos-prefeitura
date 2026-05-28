"""
app/views/secretaria.py
Aba "Por Secretaria" — panorama e detalhe por secretaria.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import (
    MESES_NOMES, formatar_mi, formatar_brl, excel_download, safe_periodo,
    bar_layout, time_layout,
)
from app.ui import section_title, page_header


def render(base: pd.DataFrame, cores_map: dict):
    secretarias_presentes = sorted(
        s for s in base["secretaria"].dropna().unique() if str(s).strip()
    )

    if not secretarias_presentes:
        st.info("Nenhuma secretaria no filtro atual.")
        return

    # ── Panorama de todas as secretarias ─────────────────────────
    section_title("Panorama — todas as secretarias")
    st.caption("Resumo do gasto de cada secretaria no período filtrado. Use o seletor abaixo para ver detalhes.")

    sec_resumo = (
        base.groupby("secretaria", as_index=False)
        .agg(total=("valor", "sum"), lancamentos=("valor", "count"),
             fornecedores=("favorecido", "nunique"))
        .sort_values("total", ascending=False)
    )
    sec_resumo["total_fmt"] = sec_resumo["total"].apply(formatar_mi)
    total_geral = sec_resumo["total"].sum()
    sec_resumo["pct"] = (
        (sec_resumo["total"] / total_geral * 100).round(1)
        if total_geral > 0 else 0.0
    )

    n_cols = min(len(secretarias_presentes), 3)
    cols_cards = st.columns(n_cols)
    for i, (_, row) in enumerate(sec_resumo.iterrows()):
        with cols_cards[i % n_cols]:
            st.metric(
                label=row["secretaria"],
                value=row["total_fmt"],
                delta=f'{row["pct"]}% do total · {int(row["fornecedores"])} fornecedores',
                delta_color="off",
            )

    # ── Detalhe de uma secretaria ────────────────────────────────
    section_title("Detalhe de uma secretaria")

    sec_escolhida = st.selectbox(
        "Selecione a secretaria",
        secretarias_presentes,
        key="sec_detalhe",
    )
    base_sec = base[base["secretaria"] == sec_escolhida]
    cor_sec = cores_map.get(sec_escolhida, "#2563eb")

    page_header(sec_escolhida, f"{len(base_sec):,} lançamentos".replace(",", "."))

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total", formatar_mi(base_sec["valor"].sum()))
    s2.metric("Lançamentos", f'{len(base_sec):,}'.replace(",", "."))
    s3.metric("Fornecedores únicos", f'{base_sec["favorecido"].nunique():,}'.replace(",", "."))
    s4.metric("Fontes de recurso", f'{base_sec["recurso"].nunique():,}'.replace(",", "."))

    c1, c2 = st.columns([1, 1])

    with c1:
        section_title("Evolução mensal")
        mes_sec = (
            base_sec.groupby(["ano", "mes"], as_index=False)["valor"]
            .sum().sort_values(["ano", "mes"])
        )
        mes_sec["periodo"] = safe_periodo(mes_sec["mes"], mes_sec["ano"])
        mes_sec["label"] = mes_sec["valor"].apply(formatar_mi)
        fig_ms = px.bar(
            mes_sec, x="periodo", y="valor",
            text="label",
            color_discrete_sequence=[cor_sec],
        )
        fig_ms.update_traces(
            textposition="outside", textfont=dict(size=10, color="#aab4c4"),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        )
        layout = time_layout(height=360, show_y_ticks=False)
        if not mes_sec.empty:
            layout["yaxis"]["range"] = [0, mes_sec["valor"].max() * 1.20]
        fig_ms.update_layout(**layout)
        st.plotly_chart(fig_ms, use_container_width=True)

    with c2:
        section_title("Top fontes de recurso")
        rec_sec = (
            base_sec.groupby("recurso", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=True)
        )
        rec_sec = rec_sec[rec_sec["recurso"].str.strip() != ""].tail(12)
        rec_sec["valor_fmt"] = rec_sec["valor"].apply(formatar_mi)
        fig_rec = px.bar(
            rec_sec, x="valor", y="recurso", orientation="h",
            text="valor_fmt",
            color_discrete_sequence=[cor_sec],
        )
        fig_rec.update_traces(
            textposition="outside",
            textfont=dict(size=11, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=360, legend=False, font_size=11)
        if not rec_sec.empty:
            layout["xaxis"]["range"] = [0, rec_sec["valor"].max() * 1.22]
        fig_rec.update_layout(**layout)
        st.plotly_chart(fig_rec, use_container_width=True)

    section_title(f"Top 20 fornecedores — {sec_escolhida}")
    top_fav_sec = (
        base_sec.groupby("favorecido", as_index=False)["valor"]
        .sum().sort_values("valor", ascending=True)
    )
    top_fav_sec = top_fav_sec[top_fav_sec["favorecido"].str.strip() != ""].tail(20)
    top_fav_sec["valor_fmt"] = top_fav_sec["valor"].apply(formatar_mi)

    fig_fav = px.bar(
        top_fav_sec, x="valor", y="favorecido", orientation="h",
        text="valor_fmt",
        color_discrete_sequence=[cor_sec],
    )
    fig_fav.update_traces(
        textposition="outside",
        textfont=dict(size=11, color="#e6edf6"),
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
    )
    layout = bar_layout(height=540, legend=False, font_size=11)
    if not top_fav_sec.empty:
        layout["xaxis"]["range"] = [0, top_fav_sec["valor"].max() * 1.18]
    layout["yaxis"]["categoryorder"] = "total ascending"
    fig_fav.update_layout(**layout)
    st.plotly_chart(fig_fav, use_container_width=True)

    section_title("Tabela completa de fornecedores")
    res_sec = (
        base_sec.groupby("favorecido", as_index=False)
        .agg(qtd=("valor", "count"), total=("valor", "sum"))
        .sort_values("total", ascending=False)
    )
    res_sec["total_fmt"] = res_sec["total"].apply(formatar_brl)
    st.dataframe(
        res_sec[["favorecido", "qtd", "total_fmt"]].rename(
            columns={
                "favorecido": "Fornecedor/Favorecido",
                "qtd": "Qtd. Lançamentos",
                "total_fmt": "Total",
            }
        ),
        hide_index=True, use_container_width=True,
    )

    st.download_button(
        f"📥 Exportar {sec_escolhida}",
        data=excel_download(base_sec),
        file_name=f"despesas_{sec_escolhida.lower().replace('/', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
