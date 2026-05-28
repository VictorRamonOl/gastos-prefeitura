"""
app/views/admin.py
Aba "Admin" — logs de importação, usuários, totais e downloads administrativos.
Restrito a perfil admin.
"""
import os
from pathlib import Path

import streamlit as st

from app.auth import is_admin
from app.db import query_df
from app.ui import section_title


# Localiza o template em diferentes contextos (local vs container)
def _localizar_template() -> Path | None:
    """Procura MODELO_DESPESAS_PREFEITURA.xlsx em locais conhecidos."""
    candidatos = [
        # Estrutura local dev
        Path(__file__).resolve().parent.parent.parent / "data" / "templates" / "MODELO_DESPESAS_PREFEITURA.xlsx",
        # Estrutura no container Docker
        Path("/app/data/templates/MODELO_DESPESAS_PREFEITURA.xlsx"),
        Path("/app/Gastos prefeitura - Maior Fornecedor/data/templates/MODELO_DESPESAS_PREFEITURA.xlsx"),
        Path("/app/gastos-prefeitura/data/templates/MODELO_DESPESAS_PREFEITURA.xlsx"),
    ]
    for p in candidatos:
        if p.exists() and p.is_file():
            return p
    return None


def render():
    if not is_admin():
        st.warning("Acesso restrito a administradores.")
        return

    # ── Download do template ─────────────────────────────────
    section_title("Template de preenchimento para a prefeitura")
    template_path = _localizar_template()
    if template_path:
        with open(template_path, "rb") as f:
            data = f.read()
        col_dl1, col_dl2 = st.columns([2, 3])
        with col_dl1:
            st.download_button(
                "📥 Baixar modelo Excel",
                data=data,
                file_name="MODELO_DESPESAS_PREFEITURA.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_template_admin",
            )
        with col_dl2:
            st.caption(
                "Arquivo padrão para a prefeitura preencher um pagamento por linha. "
                "Contém listas suspensas, validação de data/valor e abas de catálogo. "
                f"Tamanho: **{len(data) // 1024} KB**."
            )
    else:
        st.info(
            "Template ainda não foi gerado. Rode no servidor: "
            "`python scripts/gerar_template.py`"
        )

    st.markdown("")
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        section_title("Últimas importações")
        try:
            logs = query_df("""
                SELECT nome_arquivo, total_linhas, linhas_inseridas,
                       linhas_duplicadas, status,
                       DATE_FORMAT(importado_em, '%d/%m/%Y %H:%i') AS importado_em
                FROM arquivos_importados
                ORDER BY importado_em DESC
                LIMIT 20
            """)
            st.dataframe(logs, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar logs: {e}")

    with col_a2:
        section_title("Usuários")
        try:
            usuarios_df = query_df("""
                SELECT username, nome, perfil,
                       IF(ativo, 'Ativo', 'Inativo') AS status,
                       DATE_FORMAT(criado_em, '%d/%m/%Y') AS criado_em,
                       DATE_FORMAT(ultimo_acesso, '%d/%m/%Y %H:%i') AS ultimo_acesso
                FROM usuarios
                ORDER BY criado_em DESC
            """)
            st.dataframe(usuarios_df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")

    section_title("Totais por ano")
    try:
        tot_ano = query_df("""
            SELECT ano,
                   COUNT(*) AS lancamentos,
                   COUNT(DISTINCT favorecido) AS favorecidos,
                   ROUND(SUM(valor), 2) AS total_gasto
            FROM pagamentos
            GROUP BY ano
            ORDER BY ano
        """)
        st.dataframe(tot_ano, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao carregar totais: {e}")
