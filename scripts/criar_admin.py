"""
scripts/criar_admin.py
Cria ou atualiza um usuário no banco.

Uso interativo:
    python scripts/criar_admin.py

Uso com args:
    python scripts/criar_admin.py <username> <senha> <nome> <perfil>
    python scripts/criar_admin.py walter senha123 "Walter Silva" viewer
"""
import sys
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection
from app.auth import hash_senha


def criar_usuario(username: str, senha: str, nome: str, perfil: str):
    h = hash_senha(senha)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO usuarios (username, nome, senha_hash, perfil)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nome        = VALUES(nome),
            senha_hash  = VALUES(senha_hash),
            perfil      = VALUES(perfil),
            ativo       = 1
        """,
        (username.lower(), nome, h, perfil),
    )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Usuário '{username}' ({perfil}) criado/atualizado com sucesso.")


def main():
    if len(sys.argv) == 5:
        username, senha, nome, perfil = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    else:
        print("=== Criar/Atualizar Usuário ===")
        username = input("Username: ").strip()
        senha    = getpass.getpass("Senha: ")
        nome     = input("Nome completo: ").strip()
        perfil   = input("Perfil (admin/viewer) [viewer]: ").strip() or "viewer"

    if perfil not in ("admin", "viewer"):
        print("Perfil inválido. Use 'admin' ou 'viewer'.")
        sys.exit(1)

    criar_usuario(username, senha, nome, perfil)


if __name__ == "__main__":
    main()
