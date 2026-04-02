"""
app/views/geral.py
Aba "Visão Geral" — despesas mensais, top fornecedores, secretarias e programas.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import MESES_NOMES, formatar_mi, bar_layout, safe_periodo


def render(base: pd.DataFrame, cores_map: dict):
    # ── 1. Despesas mensais empilhadas por secretaria ─────────────
    st.markdown("#### Despesas Totais por Mês")

    gasto_mensal_sec = (
        base.groupby(["ano", "mes", "secretaria"], as_index=False)["valor"]
        .sum().sort_values(["ano", "mes"])
    )
    gasto_mensal_sec["periodo"] = safe_periodo(gasto_mensal_sec["mes"], gasto_mensal_sec["ano"])

    ordem_periodos = (
        gasto_mensal_sec[["ano", "mes", "periodo"]]
        .drop_duplicates().sort_values(["ano", "mes"])["periodo"].tolist()
    )
    total_por_periodo = (
        gasto_mensal_sec.groupby("periodo")["valor"]
        .sum().reindex(ordem_periodos).reset_index()
    )
    total_por_periodo.columns = ["periodo", "valor"]

    fig_evo = px.bar(
        gasto_mensal_sec, x="periodo", y="valor", color="secretaria",
        barmode="stack",
        category_orders={"periodo": ordem_periodos},
        color_discrete_map=cores_map,
        custom_data=["secretaria"],
    )
    y_max = total_por_periodo["valor"].max() or 1
    for _, row in total_por_periodo.iterrows():
        if row["valor"] > 0:
            fig_evo.add_annotation(
                x=row["periodo"], y=row["valor"],
                text=f"<b>{formatar_mi(row['valor'])}</b>",
                showarrow=False, yshift=10,
                font=dict(size=10, color="#cccccc"),
            )
    fig_evo.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>",
        selector=dict(type="bar"),
    )
    fig_evo.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            categoryorder="array", categoryarray=ordem_periodos,
            tickfont=dict(size=11), showgrid=False, zeroline=False,
        ),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False,
                   range=[0, y_max * 1.12]),
        legend=dict(orientation="h", y=-0.14, x=0, font=dict(size=11), title_text=""),
        margin=dict(l=8, r=8, t=20, b=60),
        height=420,
        bargap=0.18,
    )
    st.plotly_chart(fig_evo, use_container_width=True)

    st.markdown("---")

    # ── 2. Top 15 Fornecedores + Gasto por Secretaria ─────────────
    col2a, col2b = st.columns([3, 2])

    with col2a:
        st.markdown("#### Top 15 Fornecedores")
        top15_total = (
            base[base["favorecido"].str.strip() != ""]
            .groupby("favorecido", as_index=False)["valor"].sum()
            .sort_values("valor", ascending=False).head(15)
        )
        sec_pred = (
            base.groupby(["favorecido", "secretaria"], as_index=False)["valor"].sum()
            .sort_values("valor", ascending=False)
            .drop_duplicates("favorecido")[["favorecido", "secretaria"]]
        )
        top15 = top15_total.merge(sec_pred, on="favorecido", how="left")
        top15["label"] = top15["valor"].apply(formatar_mi)
        top15["nome_curto"] = top15["favorecido"].str[:45]
        top15 = top15.sort_values("valor", ascending=True)

        fig_forn = px.bar(
            top15, x="valor", y="nome_curto", orientation="h",
            color="secretaria", color_discrete_map=cores_map,
            text="label",
        )
        fig_forn.update_traces(
            textposition="inside", insidetextanchor="end",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        fig_forn.update_layout(**bar_layout(height=520, font_size=11))
        st.plotly_chart(fig_forn, use_container_width=True)

    with col2b:
        st.markdown("#### Gasto por Secretaria")
        sec_tot = (
            base[~base["secretaria"].str.contains("INTERNA|TRANSFER", na=False, case=False)]
            .groupby("secretaria", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=True)
        )
        total_geral = sec_tot["valor"].sum()
        sec_tot["pct"] = sec_tot["valor"] / total_geral * 100 if total_geral > 0 else 0
        sec_tot["label"] = sec_tot.apply(
            lambda r: f"  {formatar_mi(r['valor'])}  ({r['pct']:.1f}%)", axis=1
        )
        fig_sec = px.bar(
            sec_tot, x="valor", y="secretaria", orientation="h",
            color="secretaria", color_discrete_map=cores_map,
            text="label",
        )
        fig_sec.update_traces(
            textposition="inside", insidetextanchor="end",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        fig_sec.update_layout(**bar_layout(height=520, legend=False, font_size=13))
        st.plotly_chart(fig_sec, use_container_width=True)

    st.markdown("---")

    # ── 3. Top 15 Programas + Maior fornecedor por mês ─────────────
    col3a, col3b = st.columns([3, 2])

    with col3a:
        st.markdown("#### Top 15 Programas / Fontes de Recurso")
        top_rec = (
            base.groupby(["secretaria", "recurso"], as_index=False)["valor"].sum()
        )
        top_rec = (
            top_rec[top_rec["recurso"].str.strip() != ""]
            .sort_values("valor", ascending=True).tail(15)
        )
        top_rec["label"] = top_rec["valor"].apply(formatar_mi)

        fig_rec = px.bar(
            top_rec, x="valor", y="recurso", orientation="h",
            color="secretaria", color_discrete_map=cores_map,
            text="label",
        )
        fig_rec.update_traces(
            textposition="inside", insidetextanchor="end",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        fig_rec.update_layout(**bar_layout(height=520, font_size=11))
        st.plotly_chart(fig_rec, use_container_width=True)

    with col3b:
        st.markdown("#### Maior Fornecedor por Mês")

        rank_mes = (
            base.groupby(["ano", "mes", "favorecido", "secretaria"], as_index=False)["valor"].sum()
        )
        rank_mes = rank_mes[rank_mes["favorecido"].str.strip() != ""]

        if not rank_mes.empty:
            idx_max = rank_mes.groupby(["ano", "mes"])["valor"].idxmax()
            winner = rank_mes.loc[idx_max].sort_values(["ano", "mes"]).copy()
            winner["Período"] = safe_periodo(winner["mes"], winner["ano"])
            winner["Valor"] = winner["valor"].apply(formatar_mi)
            winner["Fornecedor"] = winner["favorecido"].str[:35]
            winner["Sec"] = winner["secretaria"].str[:14]

            st.dataframe(
                winner[["Período", "Fornecedor", "Valor", "Sec"]].rename(
                    columns={"Sec": "Secretaria"}
                ).reset_index(drop=True),
                hide_index=True,
                use_container_width=True,
                height=520,
                column_config={
                    "Período":    st.column_config.TextColumn("Mês", width="small"),
                    "Fornecedor": st.column_config.TextColumn("Maior Fornecedor"),
                    "Valor":      st.column_config.TextColumn("Valor", width="small"),
                    "Secretaria": st.column_config.TextColumn("Secretaria", width="medium"),
                },
            )
        else:
            st.info("Sem dados para exibir.")
