"""
app/app.py
Dashboard de Despesas da Prefeitura — Visão Executiva.
Rodar com: streamlit run app/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

from app.auth import login_requerido, usuario_atual, is_admin, logout
from app.db import query_df

# -----------------------------------------------------------------
# Page config
# -----------------------------------------------------------------
st.set_page_config(
    page_title="Gastos Prefeitura",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------
# Auth
# -----------------------------------------------------------------
login_requerido()

MESES_NOMES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
MESES_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio",
    6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro",
    11: "Novembro", 12: "Dezembro",
}


# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------
def formatar_brl(v: float) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def formatar_mi(v: float) -> str:
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:,.1f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if v >= 1_000:
        return f"R$ {v/1_000:,.1f} Mil".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatar_brl(v)


def excel_download(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()


# -----------------------------------------------------------------
# Carga de dados
# -----------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_dados() -> pd.DataFrame:
    df = query_df("""
        SELECT data, ano, mes, descricao, favorecido, recurso, secretaria, conta, valor, aba_origem
        FROM pagamentos ORDER BY ano, mes, data
    """)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for col in ["ano", "mes", "valor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["favorecido", "recurso", "secretaria", "descricao", "conta"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    df["mes_nome"] = df["mes"].map(MESES_FULL)
    df["periodo"] = df["mes"].map(MESES_NOMES) + "/" + df["ano"].astype("Int64").astype(str)
    return df


def aplicar_filtros(df, anos, meses, secretarias, recursos, favorecidos, busca) -> pd.DataFrame:
    base = df.copy()
    if anos:
        base = base[base["ano"].isin(anos)]
    if meses:
        base = base[base["mes"].isin(meses)]
    if secretarias:
        base = base[base["secretaria"].isin(secretarias)]
    if recursos:
        base = base[base["recurso"].isin(recursos)]
    if favorecidos:
        base = base[base["favorecido"].isin(favorecidos)]
    if busca:
        b = busca.strip().lower()
        mask = (
            base["favorecido"].str.lower().str.contains(b, na=False)
            | base["descricao"].str.lower().str.contains(b, na=False)
            | base["recurso"].str.lower().str.contains(b, na=False)
        )
        base = base[mask]
    return base


# -----------------------------------------------------------------
# Header
# -----------------------------------------------------------------
usuario = usuario_atual()
col_h1, col_h2 = st.columns([7, 1])
with col_h1:
    st.title("🏛️ Despesas da Prefeitura")
with col_h2:
    st.markdown(f"**{usuario.get('nome') or usuario.get('username')}**")
    if st.button("Sair", use_container_width=True):
        logout()

# -----------------------------------------------------------------
# Carga
# -----------------------------------------------------------------
try:
    df_full = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if df_full.empty:
    st.warning("Nenhum dado no banco. Execute: `python etl/run_etl.py`")
    st.stop()

# -----------------------------------------------------------------
# Sidebar — Filtros
# -----------------------------------------------------------------
st.sidebar.header("🔎 Filtros")

anos_disp = sorted(df_full["ano"].dropna().unique().astype(int).tolist())
meses_disp = sorted(df_full["mes"].dropna().unique().astype(int).tolist())
secs_disp = sorted(x for x in df_full["secretaria"].dropna().unique() if x.strip())
recursos_disp = sorted(x for x in df_full["recurso"].dropna().unique() if x.strip())
favs_disp = sorted(x for x in df_full["favorecido"].dropna().unique() if x.strip())

anos_sel = st.sidebar.multiselect("Ano", anos_disp, default=anos_disp)
meses_sel = st.sidebar.multiselect("Mês", meses_disp, default=[],
    format_func=lambda x: MESES_FULL.get(x, str(x)))
secs_sel = st.sidebar.multiselect("Secretaria", secs_disp, default=[])
recursos_sel = st.sidebar.multiselect("Recurso (fonte)", recursos_disp, default=[])
favs_sel = st.sidebar.multiselect("Favorecido", favs_disp, default=[])
busca = st.sidebar.text_input("Buscar texto")

base = aplicar_filtros(df_full, anos_sel, meses_sel, secs_sel, recursos_sel, favs_sel, busca)

if base.empty:
    st.warning("Nenhum dado com os filtros selecionados.")
    st.stop()

# -----------------------------------------------------------------
# KPIs gerais
# -----------------------------------------------------------------
total = base["valor"].sum()
qtd = len(base)
qtd_favs = base["favorecido"].nunique()
media = base["valor"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total gasto", formatar_mi(total))
k2.metric("📋 Lançamentos", f"{qtd:,}".replace(",", "."))
k3.metric("🏢 Favorecidos únicos", f"{qtd_favs:,}".replace(",", "."))
k4.metric("📊 Valor médio", formatar_brl(media))

st.markdown("---")

# =================================================================
# ABAS PRINCIPAIS
# =================================================================
tab_geral, tab_sec, tab_forn, tab_ranking, tab_detalhe, tab_admin = st.tabs([
    "📊 Visão Geral",
    "🏛️ Por Secretaria",
    "🏢 Por Fornecedor",
    "🏆 Rankings",
    "📋 Base Detalhada",
    "⚙️ Admin" if is_admin() else "⚙️ Admin (restrito)",
])

# =================================================================
# ABA 1 — VISÃO GERAL
# =================================================================
CORES_SEC = px.colors.qualitative.Set2   # paleta consistente entre todos os gráficos

with tab_geral:

    # ── Linha 1: Evolução mensal empilhada por secretaria ──────────
    st.markdown("### Evolução mensal de despesas por Secretaria")
    gasto_mensal_sec = (
        base.groupby(["ano", "mes", "secretaria"], as_index=False)["valor"]
        .sum().sort_values(["ano", "mes"])
    )
    gasto_mensal_sec["periodo"] = (
        gasto_mensal_sec["mes"].map(MESES_NOMES)
        + "/" + gasto_mensal_sec["ano"].astype(int).astype(str)
    )
    # Ordem dos períodos para o eixo X
    ordem_periodos = (
        gasto_mensal_sec[["ano", "mes", "periodo"]]
        .drop_duplicates().sort_values(["ano", "mes"])["periodo"].tolist()
    )
    total_por_periodo = (
        gasto_mensal_sec.groupby("periodo")["valor"].sum().reset_index()
    )

    fig_evo = px.bar(
        gasto_mensal_sec, x="periodo", y="valor", color="secretaria",
        barmode="stack",
        category_orders={"periodo": ordem_periodos},
        color_discrete_sequence=CORES_SEC,
        custom_data=["secretaria"],
    )
    # Linha do total por mês
    fig_evo.add_scatter(
        x=total_por_periodo["periodo"],
        y=total_por_periodo["valor"],
        mode="lines+markers",
        name="Total",
        line=dict(color="#333333", width=2, dash="dot"),
        marker=dict(size=6),
    )
    fig_evo.update_layout(
        xaxis_title="", yaxis_title="Valor (R$)",
        legend_title="Secretaria",
        plot_bgcolor="white",
        height=420,
        yaxis=dict(tickformat=",.0f", gridcolor="#eeeeee"),
        xaxis=dict(categoryorder="array", categoryarray=ordem_periodos),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(b=80),
    )
    fig_evo.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>",
        selector=dict(type="bar"),
    )
    st.plotly_chart(fig_evo, use_container_width=True)

    st.markdown("---")

    # ── Linha 2: Secretaria (barra horiz.) + Fornecedores (treemap) ──
    col_l2a, col_l2b = st.columns([1, 1])

    with col_l2a:
        st.markdown("### Gasto por Secretaria")
        sec_tot = (
            base.groupby("secretaria", as_index=False)["valor"]
            .sum().sort_values("valor", ascending=True)   # crescente p/ barras horizontais
        )
        sec_tot["pct"] = sec_tot["valor"] / sec_tot["valor"].sum() * 100
        sec_tot["label"] = sec_tot.apply(
            lambda r: f"{formatar_mi(r['valor'])} ({r['pct']:.1f}%)", axis=1
        )
        fig_sec_h = px.bar(
            sec_tot, x="valor", y="secretaria", orientation="h",
            color="secretaria",
            color_discrete_sequence=CORES_SEC,
            text="label",
        )
        fig_sec_h.update_traces(textposition="inside", insidetextanchor="middle")
        fig_sec_h.update_layout(
            xaxis_title="", yaxis_title="",
            plot_bgcolor="white",
            showlegend=False,
            height=360,
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=13)),
            margin=dict(l=10, r=10),
        )
        st.plotly_chart(fig_sec_h, use_container_width=True)

    with col_l2b:
        st.markdown("### Top Fornecedores")
        top20 = (
            base.groupby(["favorecido", "secretaria"], as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False)
        )
        top20 = top20[top20["favorecido"].str.strip() != ""].head(20)
        top20["valor_fmt"] = top20["valor"].apply(formatar_mi)

        fig_top_forn = px.bar(
            top20.sort_values("valor"),
            x="valor", y="favorecido", orientation="h",
            color="secretaria",
            color_discrete_sequence=CORES_SEC,
            text="valor_fmt",
        )
        fig_top_forn.update_traces(textposition="inside", insidetextanchor="middle")
        fig_top_forn.update_layout(
            xaxis_title="", yaxis_title="",
            plot_bgcolor="white",
            legend_title="Secretaria",
            height=560,
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.15),
            margin=dict(l=10, r=10, b=60),
        )
        st.plotly_chart(fig_top_forn, use_container_width=True)

    st.markdown("---")

    # ── Linha 3: Treemap secretaria → recurso + Top programas ──────
    col_l3a, col_l3b = st.columns([1, 1])

    with col_l3a:
        st.markdown("### Gasto por Programa/Recurso (Top 20)")
        top_rec = (
            base.groupby(["secretaria", "recurso"], as_index=False)["valor"]
            .sum().sort_values("valor", ascending=False)
        )
        top_rec = top_rec[top_rec["recurso"].str.strip() != ""].head(20)
        top_rec["valor_fmt"] = top_rec["valor"].apply(formatar_mi)

        fig_rec_bar = px.bar(
            top_rec.sort_values("valor"),
            x="valor", y="recurso", orientation="h",
            color="secretaria",
            color_discrete_sequence=CORES_SEC,
            text="valor_fmt",
        )
        fig_rec_bar.update_traces(textposition="inside", insidetextanchor="middle")
        fig_rec_bar.update_layout(
            xaxis_title="", yaxis_title="",
            plot_bgcolor="white",
            legend_title="Secretaria",
            height=520,
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.18),
            margin=dict(l=10, r=10, b=60),
        )
        st.plotly_chart(fig_rec_bar, use_container_width=True)

    with col_l3b:
        st.markdown("### Mapa de calor — Secretaria × Mês")
        heat_data = (
            base.groupby(["secretaria", "mes"], as_index=False)["valor"].sum()
        )
        heat_pivot = heat_data.pivot(index="secretaria", columns="mes", values="valor").fillna(0)
        heat_pivot.columns = [MESES_FULL.get(c, str(c)) for c in heat_pivot.columns]

        fig_heat = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=heat_pivot.columns.tolist(),
            y=heat_pivot.index.tolist(),
            colorscale="Blues",
            text=[[formatar_mi(v) for v in row] for row in heat_pivot.values],
            texttemplate="%{text}",
            hovertemplate="<b>%{y}</b><br>%{x}<br>R$ %{z:,.2f}<extra></extra>",
        ))
        fig_heat.update_layout(
            xaxis_title="", yaxis_title="",
            height=400,
            margin=dict(l=10, r=10),
            font=dict(size=10),
        )
        st.plotly_chart(fig_heat, use_container_width=True)


# =================================================================
# ABA 2 — POR SECRETARIA
# =================================================================
with tab_sec:
    secretarias_presentes = sorted(
        s for s in base["secretaria"].dropna().unique() if str(s).strip()
    )

    if not secretarias_presentes:
        st.info("Nenhuma secretaria no filtro atual.")
    else:
        # ── Visão consolidada de todas as secretarias ──────────────
        st.markdown("### Todas as Secretarias — Panorama")

        sec_resumo = (
            base.groupby("secretaria", as_index=False)
            .agg(total=("valor", "sum"), lancamentos=("valor", "count"),
                 fornecedores=("favorecido", "nunique"))
            .sort_values("total", ascending=False)
        )
        sec_resumo["total_fmt"] = sec_resumo["total"].apply(formatar_mi)
        sec_resumo["pct"] = (sec_resumo["total"] / sec_resumo["total"].sum() * 100).round(1)

        # Cards por secretaria
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

        # ── Detalhe por secretaria selecionada ──────────────────────
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
            mes_sec["periodo"] = mes_sec["mes"].map(MESES_NOMES) + "/" + mes_sec["ano"].astype(int).astype(str)
            fig_ms = px.bar(
                mes_sec, x="periodo", y="valor",
                text=mes_sec["valor"].apply(formatar_mi),
                color_discrete_sequence=["#2196F3"],
            )
            fig_ms.update_traces(textposition="outside")
            fig_ms.update_layout(
                xaxis_title="", yaxis_title="R$", plot_bgcolor="white",
                height=340, yaxis=dict(showticklabels=False, showgrid=False),
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
                xaxis_title="", yaxis_title="", plot_bgcolor="white",
                height=340,
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
                columns={"favorecido": "Fornecedor/Favorecido", "qtd": "Qtd. Lançamentos", "total_fmt": "Total"}
            ),
            hide_index=True, use_container_width=True,
        )

        st.download_button(
            f"📥 Exportar {sec_escolhida}",
            data=excel_download(base_sec),
            file_name=f"despesas_{sec_escolhida.lower().replace('/', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# =================================================================
# ABA 3 — POR FORNECEDOR
# =================================================================
with tab_forn:
    st.subheader("🏢 Análise por Fornecedor")

    # Ordenação: maior total primeiro
    rank_fav = (
        base.groupby("favorecido", as_index=False)["valor"]
        .sum().sort_values("valor", ascending=False)
    )
    rank_fav = rank_fav[rank_fav["favorecido"].str.strip() != ""]
    rank_fav["label"] = rank_fav.apply(
        lambda r: f"{r['favorecido']}  ({formatar_mi(r['valor'])})", axis=1
    )

    forn_sel = st.selectbox(
        "Selecione o Fornecedor",
        rank_fav["favorecido"].tolist(),
        format_func=lambda f: rank_fav.loc[rank_fav["favorecido"] == f, "label"].values[0],
        key="forn_sel",
    )

    base_forn = base[base["favorecido"] == forn_sel]

    # ── KPIs do fornecedor ──
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Total recebido", formatar_mi(base_forn["valor"].sum()))
    f2.metric("Lançamentos", f'{len(base_forn):,}'.replace(",", "."))
    f3.metric("Secretarias atendidas", str(base_forn["secretaria"].nunique()))
    f4.metric("Período", f'{base_forn["ano"].min():.0f} – {base_forn["ano"].max():.0f}' if not base_forn.empty else "—")

    st.markdown("---")

    # ── Evolução anual e mensal ──
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("**Recebido por Ano**")
        por_ano = (
            base_forn.groupby("ano", as_index=False)["valor"].sum()
        )
        fig_ano = px.bar(
            por_ano, x="ano", y="valor", text_auto=".3s",
            color_discrete_sequence=["#1f77b4"],
        )
        fig_ano.update_traces(texttemplate="R$ %{y:.3s}", textposition="outside")
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
        por_mes["periodo"] = por_mes["mes"].map(MESES_NOMES) + "/" + por_mes["ano"].astype(int).astype(str)
        fig_mes_f = px.bar(
            por_mes, x="periodo", y="valor", text_auto=".3s",
            color_discrete_sequence=["#ff7f0e"],
        )
        fig_mes_f.update_layout(
            xaxis_title="", yaxis_title="R$", plot_bgcolor="white",
        )
        st.plotly_chart(fig_mes_f, use_container_width=True)

    # ── Distribuição por secretaria ──
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
            rec_forn, x="valor", y="recurso", orientation="h", text_auto=".3s",
            color_discrete_sequence=["#9467bd"],
        )
        fig_rec_f.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="R$", yaxis_title="", plot_bgcolor="white",
        )
        st.plotly_chart(fig_rec_f, use_container_width=True)

    # ── Todos os pagamentos do fornecedor ──
    st.markdown("---")
    st.markdown(f"**Todos os pagamentos de _{forn_sel}_**")

    pag_forn = base_forn.copy().sort_values(["ano", "mes", "data"])
    pag_forn["data_fmt"] = pag_forn["data"].dt.strftime("%d/%m/%Y")
    pag_forn["valor_fmt"] = pag_forn["valor"].apply(formatar_brl)

    # Totais por ano como subtítulo
    for ano_val in sorted(pag_forn["ano"].dropna().unique().astype(int)):
        df_ano = pag_forn[pag_forn["ano"] == ano_val]
        total_ano = df_ano["valor"].sum()
        with st.expander(f"📅 {ano_val}  —  {formatar_mi(total_ano)}  ({len(df_ano)} lançamentos)", expanded=(ano_val == pag_forn["ano"].max())):
            # Resumo mensal do ano
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
        data=excel_download(pag_forn[[
            "data_fmt", "ano", "mes_nome", "secretaria",
            "recurso", "valor_fmt", "valor", "descricao",
        ]].rename(columns={
            "data_fmt": "Data", "ano": "Ano", "mes_nome": "Mês",
            "secretaria": "Secretaria", "recurso": "Recurso",
            "valor_fmt": "Valor Formatado", "valor": "Valor",
            "descricao": "Descrição",
        })),
        file_name=f"fornecedor_{forn_sel[:40].replace(' ','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_forn",
    )


# =================================================================
# ABA 4 — RANKINGS
# =================================================================
with tab_ranking:
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
        base.groupby(["ano", "mes", "favorecido"], as_index=False)["valor"]
        .sum()
    )
    # Pega o maior favorecido de cada mês
    idx_max = top_mes.groupby(["ano", "mes"])["valor"].idxmax()
    top_mes_winner = top_mes.loc[idx_max].sort_values(["ano", "mes"])
    top_mes_winner["periodo"] = (
        top_mes_winner["mes"].map(MESES_NOMES) + "/" + top_mes_winner["ano"].astype(int).astype(str)
    )
    top_mes_winner["valor_fmt"] = top_mes_winner["valor"].apply(formatar_brl)
    st.dataframe(
        top_mes_winner[["periodo", "favorecido", "valor_fmt"]].rename(
            columns={"periodo": "Período", "favorecido": "Maior Favorecido", "valor_fmt": "Valor"}
        ),
        hide_index=True, use_container_width=True,
    )


# =================================================================
# ABA 4 — BASE DETALHADA
# =================================================================
with tab_detalhe:
    st.subheader("Base detalhada")

    # Filtro rápido dentro da aba
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        busca_tab = st.text_input("Busca rápida", key="busca_tab")
    with col_f2:
        top_n = st.selectbox("Exibir", [100, 500, 1000, 5000, 0], format_func=lambda x: "Todos" if x == 0 else str(x))

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

    base_view["data_fmt"] = base_view["data"].dt.strftime("%d/%m/%Y")
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


# =================================================================
# ABA 5 — ADMIN
# =================================================================
with tab_admin:
    if not is_admin():
        st.warning("Acesso restrito a administradores.")
    else:
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.subheader("Últimas importações")
            try:
                logs = query_df("""
                    SELECT nome_arquivo, total_linhas, linhas_inseridas,
                           linhas_duplicadas, status,
                           DATE_FORMAT(importado_em, '%d/%m/%Y %H:%i') as importado_em
                    FROM arquivos_importados ORDER BY importado_em DESC LIMIT 20
                """)
                st.dataframe(logs, hide_index=True, use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {e}")

        with col_a2:
            st.subheader("Usuários")
            try:
                usuarios_df = query_df("""
                    SELECT username, nome, perfil,
                           IF(ativo, 'Ativo', 'Inativo') as status,
                           DATE_FORMAT(criado_em, '%d/%m/%Y') as criado_em,
                           DATE_FORMAT(ultimo_acesso, '%d/%m/%Y %H:%i') as ultimo_acesso
                    FROM usuarios ORDER BY criado_em DESC
                """)
                st.dataframe(usuarios_df, hide_index=True, use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {e}")

        st.markdown("---")
        st.subheader("Totais por ano")
        try:
            tot_ano = query_df("""
                SELECT ano, COUNT(*) as lancamentos,
                       COUNT(DISTINCT favorecido) as favorecidos,
                       ROUND(SUM(valor), 2) as total_gasto
                FROM pagamentos GROUP BY ano ORDER BY ano
            """)
            st.dataframe(tot_ano, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
