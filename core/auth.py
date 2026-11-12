"""Autenticação multiusuário: todos têm o mesmo nível de acesso."""
import os
from functools import wraps
from flask import session, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash

from .db import get_db, row_to_dict


def criar_usuario(username, senha):
    username = username.strip().lower()
    if not username or not senha:
        return False, "Usuário e senha são obrigatórios"
    if len(senha) < 6:
        return False, "Senha deve ter ao menos 6 caracteres"
    conn = get_db()
    existente = conn.execute("SELECT 1 FROM usuarios WHERE username=?", (username,)).fetchone()
    if existente:
        conn.close()
        return False, "Usuário já existe"
    senha_hash = generate_password_hash(senha)
    conn.execute("INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)", (username, senha_hash))
    conn.commit()
    conn.close()
    return True, None


def verificar_login(username, senha):
    username = username.strip().lower()
    conn = get_db()
    u = conn.execute("SELECT * FROM usuarios WHERE username=?", (username,)).fetchone()
    conn.close()
    if not u:
        return False
    u = row_to_dict(u)
    return check_password_hash(u['senha_hash'], senha)


def listar_usuarios():
    conn = get_db()
    r = [row_to_dict(x) for x in conn.execute("SELECT id, username, criado_em FROM usuarios ORDER BY username").fetchall()]
    conn.close()
    return r


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapper

def excluir_usuario(username):
    """Remove um usuário pelo username. Impede excluir o último usuário restante."""
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM usuarios").fetchone()
        total = total['c'] if hasattr(total, 'keys') else total[0]
        if total <= 1:
            conn.close()
            return False, "Não é possível excluir o único usuário do sistema"

        conn.execute("DELETE FROM usuarios WHERE LOWER(username) = LOWER(?)", (username.strip(),))
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        conn.close()
        return False, "Erro ao excluir usuário"
