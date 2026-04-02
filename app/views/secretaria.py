"""
app/views/secretaria.py
Aba "Por Secretaria" — panorama e detalhe por secretaria.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import MESES_NOMES, formatar_mi, formatar_brl, excel_download, safe_periodo


def render(base: pd.DataFrame, cores_map: dict):
    secretarias_presentes = sorted(
        s for s in base["secretaria"].dropna().unique() if str(s).strip()
    )

    if not secretarias_presentes:
        st.info("Nenhuma secretaria no filtro atual.")
        return

    # ── Panorama de todas as secretarias ─────────────────────────
    st.markdown("### Todas as Secretarias — Panorama")

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
                delta=f'{row["pct"]}% do total | {row["fornecedores"]} fornecedores',
                delta_color="off",
            )

    st.markdown("---")

    # ── Detalhe de uma secretaria ────────────────────────────────
    sec_escolhida = st.selectbox(
        "Detalhes de uma secretaria",
        secretarias_presentes,
        key="sec_detalhe",
    )
    base_sec = base[base["secretaria"] == sec_escolhida]

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total", formatar_mi(base_sec["valor"].sum()))
    s2.metric("Lançamentos", f'{len(base_sec):,}'.replace(",", "."))
    s3.metric("Fornecedores únicos", f'{base_sec["favorecido"].nunique():,}'.replace(",", "."))
    s4.metric("Recursos (fontes)", f'{base_sec["recurso"].nunique():,}'.replace(",", "."))

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown(f"**Evolução mensal — {sec_escolhida}**")
        mes_sec = (
            base_sec.groupby(["ano", "mes"], as_index=False)["valor"]
            .sum().sort_values(["ano", "mes"])
        )
        mes_sec["periodo"] = safe_periodo(mes_sec["mes"], mes_sec["ano"])
        fig_ms = px.bar(
            mes_sec, x="periodo", y="valor",
            text=mes_sec["valor"].apply(formatar_mi),
            color_discrete_sequence=["#2196F3"],
        )
        fig_ms.update_traces(textposition="outside")
        fig_ms.update_layout(
            xaxis_title="", yaxis_title="R$",
            plot_bgcolor="white", height=340,
            yaxis=dict(showticklabels=False, showgrid=False),
            margin=dict(t=30, b=10),
        )
        st.plotly_chart(fig_ms, use_container_width=True)

    with c2:
        st.markdown(f"**Recursos (fontes) — {sec_escolhida}**")
        rec_sec = (
            base_sec.groupby("recurso", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=True)
        )
        rec_sec = rec_sec[rec_sec["recurso"].str.strip() != ""].tail(12)
        rec_sec["valor_fmt"] = rec_sec["valor"].apply(formatar_mi)
        fig_rec = px.bar(
            rec_sec, x="valor", y="recurso", orientation="h",
            text="valor_fmt",
            color_discrete_sequence=["#4CAF50"],
        )
        fig_rec.update_traces(textposition="inside", insidetextanchor="middle")
        fig_rec.update_layout(
            xaxis_title="", yaxis_title="",
            plot_bgcolor="white", height=340,
            xaxis=dict(showticklabels=False, showgrid=False),
            margin=dict(t=30, b=10),
        )
        st.plotly_chart(fig_rec, use_container_width=True)

    st.markdown(f"**Top 20 Fornecedores — {sec_escolhida}**")
    top_fav_sec = (
        base_sec.groupby("favorecido", as_index=False)["valor"]
        .sum().sort_values("valor", ascending=True)
    )
    top_fav_sec = top_fav_sec[top_fav_sec["favorecido"].str.strip() != ""].tail(20)
    top_fav_sec["valor_fmt"] = top_fav_sec["valor"].apply(formatar_mi)

    fig_fav = px.bar(
        top_fav_sec, x="valor", y="favorecido", orientation="h",
        text="valor_fmt",
        color_discrete_sequence=["#FF9800"],
    )
    fig_fav.update_traces(textposition="inside", insidetextanchor="middle")
    fig_fav.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="", yaxis_title="",
        plot_bgcolor="white", height=520,
        xaxis=dict(showticklabels=False, showgrid=False),
        margin=dict(l=10, r=10),
    )
    st.plotly_chart(fig_fav, use_container_width=True)

    st.markdown("**Tabela completa de fornecedores**")
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
