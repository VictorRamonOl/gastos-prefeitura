"""
app/auth.py
Autenticação de usuários com bcrypt + MySQL.
"""
import bcrypt
import streamlit as st
from datetime import datetime

from app.db import get_connection


# -----------------------------------------------------------------
# Funções de banco — com fechamento garantido via try/finally
# -----------------------------------------------------------------
def _buscar_usuario(username: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, nome, senha_hash, perfil, ativo FROM usuarios WHERE username = %s",
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()
        return row
    finally:
        conn.close()


def _registrar_acesso(user_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET ultimo_acesso = %s WHERE id = %s",
            (datetime.now(), user_id),
        )
        conn.commit()
        cursor.close()
    finally:
        conn.close()


# -----------------------------------------------------------------
# Funções públicas
# -----------------------------------------------------------------
def verificar_login(username: str, senha: str) -> dict | None:
    """Verifica credenciais. Retorna dict com dados do usuário ou None."""
    if not username or not senha:
        return None
    usuario = _buscar_usuario(username.strip().lower())
    if not usuario or not usuario["ativo"]:
        return None
    senha_bytes = senha.encode("utf-8")
    hash_bytes  = usuario["senha_hash"].encode("utf-8")
    if bcrypt.checkpw(senha_bytes, hash_bytes):
        _registrar_acesso(usuario["id"])
        return usuario
    return None


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt para armazenar no banco."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# -----------------------------------------------------------------
# Controle de sessão Streamlit
# -----------------------------------------------------------------
def login_requerido():
    """Para o app inteiro se o usuário não estiver autenticado."""
    if "usuario" not in st.session_state:
        st.session_state["usuario"] = None

    if st.session_state["usuario"] is None:
        _tela_login()
        st.stop()


def _tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acesso ao Dashboard")
        st.markdown("---")
        with st.form("form_login"):
            username = st.text_input("Usuário", placeholder="seu.usuario")
            senha    = st.text_input("Senha", type="password")
            entrar   = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            try:
                usuario = verificar_login(username, senha)
            except Exception as e:
                st.error(f"Erro ao conectar ao banco: {e}")
                return
            if usuario:
                st.session_state["usuario"] = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")


def usuario_atual() -> dict:
    return st.session_state.get("usuario", {})


def is_admin() -> bool:
    return usuario_atual().get("perfil") == "admin"


def logout():
    st.session_state["usuario"] = None
    st.rerun()
