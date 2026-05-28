"""
app/views/geral.py
Aba "Visão Geral" — despesas mensais, top fornecedores, secretarias e programas.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from app.helpers import MESES_NOMES, formatar_mi, bar_layout, time_layout, safe_periodo
from app.ui import section_title


def render(base: pd.DataFrame, cores_map: dict):
    # ── 1. Evolução mensal empilhada por secretaria ───────────────
    section_title("Evolução mensal — empilhado por secretaria")
    st.caption(
        "Como ler: a altura total de cada barra é o gasto do mês. "
        "Cada cor representa uma secretaria. Os rótulos no topo mostram os 6 maiores meses. "
        "Passe o mouse para ver o valor exato."
    )

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

    fig_evo = px.bar(
        gasto_mensal_sec, x="periodo", y="valor", color="secretaria",
        barmode="stack",
        category_orders={"periodo": ordem_periodos},
        color_discrete_map=cores_map,
        custom_data=["secretaria"],
    )
    y_max = total_por_periodo["valor"].max() or 1
    # Anota apenas o total no topo das barras com maior gasto (top 6) para evitar sobreposição.
    top_periodos = total_por_periodo.nlargest(6, "valor")
    for _, row in top_periodos.iterrows():
        if row["valor"] > 0:
            fig_evo.add_annotation(
                x=row["periodo"], y=row["valor"],
                text=f"<b>{formatar_mi(row['valor'])}</b>",
                showarrow=False, yshift=12,
                font=dict(size=10, color="#e6edf6"),
            )
    fig_evo.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>",
        selector=dict(type="bar"),
    )
    layout = time_layout(height=480, show_y_ticks=False)
    layout["yaxis"]["range"] = [0, y_max * 1.18]
    layout["xaxis"]["categoryorder"] = "array"
    layout["xaxis"]["categoryarray"] = ordem_periodos
    fig_evo.update_layout(**layout)
    st.plotly_chart(fig_evo, use_container_width=True)

    # ── 2. Top 15 Fornecedores + Gasto por Secretaria ─────────────
    col2a, col2b = st.columns([3, 2])

    with col2a:
        section_title("Top 15 fornecedores")
        st.caption("Empresas/pessoas que mais receberam pagamentos. Cor = secretaria que mais paga.")
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
            textposition="outside",
            textfont=dict(size=11, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=540, font_size=11)
        layout["xaxis"]["range"] = [0, top15["valor"].max() * 1.18]
        fig_forn.update_layout(**layout)
        st.plotly_chart(fig_forn, use_container_width=True)

    with col2b:
        section_title("Gasto por secretaria")
        st.caption("Total pago por cada secretaria, com o percentual sobre o total geral.")
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
            textposition="outside",
            textfont=dict(size=11, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=540, legend=False, font_size=12)
        layout["xaxis"]["range"] = [0, sec_tot["valor"].max() * 1.30]
        fig_sec.update_layout(**layout)
        st.plotly_chart(fig_sec, use_container_width=True)

    # ── 3. Top 15 Programas + Maior fornecedor por mês ─────────────
    col3a, col3b = st.columns([3, 2])

    with col3a:
        section_title("Top 15 fontes de recurso")
        st.caption("De onde veio o dinheiro pago — fundo federal, ICMS, recursos próprios etc.")
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
            textposition="outside",
            textfont=dict(size=11, color="#e6edf6"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
        layout = bar_layout(height=540, font_size=11)
        layout["xaxis"]["range"] = [0, top_rec["valor"].max() * 1.18]
        fig_rec.update_layout(**layout)
        st.plotly_chart(fig_rec, use_container_width=True)

    with col3b:
        section_title("Maior fornecedor por mês")
        st.caption("Quem recebeu o maior pagamento em cada mês.")

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
                height=540,
                column_config={
                    "Período":    st.column_config.TextColumn("Mês", width="small"),
                    "Fornecedor": st.column_config.TextColumn("Maior Fornecedor"),
                    "Valor":      st.column_config.TextColumn("Valor", width="small"),
                    "Secretaria": st.column_config.TextColumn("Secretaria", width="medium"),
                },
            )
        else:
            st.info("Sem dados para exibir.")
