import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

from core.db import get_db, init_db, row_to_dict, USANDO_POSTGRES
from core.auth import login_required, criar_usuario, verificar_login, listar_usuarios
from core.utils import (
    formatar_documento, formatar_telefone, formatar_data_extenso,
    hoje_recife, hora_recife, SECOES, CRACHA_TIPOS,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-troque-em-producao")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("VERCEL") == "1",  # https só em produção
)

app.jinja_env.filters['doc'] = formatar_documento
app.jinja_env.filters['tel'] = formatar_telefone


@app.after_request
def noindex(resp):
    resp.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return resp


def get_servico_aberto(conn):
    s = conn.execute("SELECT * FROM servicos WHERE status='aberto' ORDER BY id DESC LIMIT 1").fetchone()
    return row_to_dict(s) if s else None


# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        senha = request.form.get('senha', '')
        if verificar_login(username, senha):
            session['username'] = username.strip().lower()
            destino = request.args.get('next') or url_for('relacao')
            return redirect(destino)
        return render_template('login.html', erro="Usuário ou senha inválidos")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    erro = None
    if request.method == 'POST':
        ok, msg = criar_usuario(request.form.get('username', ''), request.form.get('senha', ''))
        if not ok:
            erro = msg
    return render_template('usuarios.html', usuarios=listar_usuarios(), erro=erro)


# ── ROTAS ─────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    return redirect(url_for('relacao'))


@app.route('/relacao')
@login_required
def relacao():
    conn = get_db()
    servico = get_servico_aberto(conn)
    entradas = [row_to_dict(r) for r in conn.execute('''
        SELECT r.*, p.nome, p.cpf, p.ddd, p.telefone, p.veiculo
        FROM relacao_dia r JOIN pessoas p ON p.id = r.pessoa_id
        WHERE r.servico_id = ? ORDER BY r.id
    ''', (servico['id'],)).fetchall()]
    conn.close()
    return render_template('relacao.html', servico=servico, hoje=hoje_recife(), entradas=entradas,
                           secoes=SECOES, cracha_tipos=CRACHA_TIPOS)


@app.route('/cadastro')
@login_required
def cadastro():
    return render_template('cadastro.html')


@app.route('/pessoas')
@login_required
def pessoas():
    conn = get_db()
    lista = [row_to_dict(r) for r in conn.execute('SELECT * FROM pessoas ORDER BY nome').fetchall()]
    conn.close()
    return render_template('pessoas.html', pessoas=lista)


@app.route('/imprimir')
@app.route('/imprimir/<int:servico_id>')
@login_required
def imprimir(servico_id=None):
    conn = get_db()
    if servico_id is None:
        servico = get_servico_aberto(conn)
    else:
        s = conn.execute("SELECT * FROM servicos WHERE id=?", (servico_id,)).fetchone()
        servico = row_to_dict(s) if s else get_servico_aberto(conn)

    entradas = [row_to_dict(r) for r in conn.execute('''
        SELECT r.*, p.nome, p.cpf, p.ddd, p.telefone, p.veiculo
        FROM relacao_dia r JOIN pessoas p ON p.id = r.pessoa_id
        WHERE r.servico_id = ? ORDER BY r.id
    ''', (servico['id'],)).fetchall()]
    conn.close()

    info = formatar_data_extenso(servico['data_inicio'])
    return render_template('imprimir.html', entradas=entradas, servico=servico, **info)


@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    # Placeholder mantido do projeto original (assinatura Cmt da Guarda), se já existir no seu fluxo
    return render_template('config.html', cmt_guarda_nome='')


# ── API ───────────────────────────────────────────────────────────────────

@app.route('/api/buscar_pessoa')
@login_required
def buscar_pessoa():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    q_digits = ''.join(c for c in q if c.isdigit())
    conn = get_db()
    if q_digits and len(q_digits) >= 3:
        r = conn.execute(
            """SELECT * FROM pessoas WHERE nome LIKE ?
            OR cpf LIKE ?
            OR REPLACE(REPLACE(cpf,'.',''),'-','') LIKE ?
            ORDER BY nome LIMIT 10""",
            (f'%{q}%', f'%{q}%', f'%{q_digits}%')).fetchall()
    else:
        r = conn.execute(
            'SELECT * FROM pessoas WHERE nome LIKE ? OR cpf LIKE ? ORDER BY nome LIMIT 10',
            (f'%{q}%', f'%{q}%')).fetchall()
    conn.close()
    resultado = [row_to_dict(x) for x in r]
    for p in resultado:
        p['cpf'] = formatar_documento(p['cpf'])
        p['telefone'] = formatar_telefone(p['telefone'])
    return jsonify(resultado)


@app.route('/api/salvar_pessoa', methods=['POST'])
@login_required
def salvar_pessoa():
    d = request.json
    if not d.get('nome') or not d.get('cpf'):
        return jsonify({'ok': False, 'erro': 'Nome e CPF são obrigatórios'})
    cpf_formatado = formatar_documento(d['cpf'])
    tel_formatado = formatar_telefone(d.get('telefone', ''))
    conn = get_db()
    try:
        cur = conn.execute('INSERT INTO pessoas (nome,cpf,ddd,telefone,veiculo,observacao) VALUES (?,?,?,?,?,?)',
            (d['nome'], cpf_formatado, d.get('ddd', ''), tel_formatado, d.get('veiculo', ''), d.get('observacao', '')))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        conn.close()
        if 'UNIQUE' in str(e).upper() or 'DUPLICATE' in str(e).upper():
            return jsonify({'ok': False, 'erro': 'CPF já cadastrado'})
        return jsonify({'ok': False, 'erro': 'Erro ao salvar'})


@app.route('/api/editar_pessoa', methods=['POST'])
@login_required
def editar_pessoa():
    d = request.json
    cpf_formatado = formatar_documento(d['cpf'])
    tel_formatado = formatar_telefone(d.get('telefone', ''))
    conn = get_db()
    try:
        conn.execute('UPDATE pessoas SET nome=?,cpf=?,ddd=?,telefone=?,veiculo=?,observacao=? WHERE id=?',
            (d['nome'], cpf_formatado, d.get('ddd', ''), tel_formatado, d.get('veiculo', ''), d.get('observacao', ''), d['id']))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        conn.close()
        if 'UNIQUE' in str(e).upper() or 'DUPLICATE' in str(e).upper():
            return jsonify({'ok': False, 'erro': 'CPF já cadastrado para outro registro'})
        return jsonify({'ok': False, 'erro': 'Erro ao salvar'})


@app.route('/api/excluir_pessoa', methods=['POST'])
@login_required
def excluir_pessoa():
    conn = get_db()
    conn.execute('DELETE FROM pessoas WHERE id=?', (request.json.get('id'),))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/adicionar_relacao', methods=['POST'])
@login_required
def adicionar_relacao():
    d = request.json
    conn = get_db()
    servico = get_servico_aberto(conn)
    hoje = hoje_recife()
    conn.execute('''INSERT INTO relacao_dia
        (servico_id,pessoa_id,cracha_tipo,cracha_numero,secao,motivo,observacao,horario_entrada,horario_saida,data_entrada,data_saida)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (servico['id'], d['pessoa_id'], d.get('cracha_tipo', ''), d.get('cracha_numero', ''),
         d.get('secao', ''), d.get('motivo', ''), d.get('observacao', ''),
         d.get('horario_entrada', ''), d.get('horario_saida', ''),
         hoje, hoje if d.get('horario_saida') else None))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/atualizar_relacao', methods=['POST'])
@login_required
def atualizar_relacao():
    d = request.json
    conn = get_db()
    conn.execute('''UPDATE relacao_dia SET cracha_tipo=?,cracha_numero=?,secao=?,
        motivo=?,observacao=?,horario_entrada=?,horario_saida=? WHERE id=?''',
        (d.get('cracha_tipo', ''), d.get('cracha_numero', ''), d.get('secao', ''),
         d.get('motivo', ''), d.get('observacao', ''),
         d.get('horario_entrada', ''), d.get('horario_saida', ''), d['id']))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/remover_relacao', methods=['POST'])
@login_required
def remover_relacao():
    conn = get_db()
    conn.execute('DELETE FROM relacao_dia WHERE id=?', (request.json.get('id'),))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/registrar_saida', methods=['POST'])
@login_required
def registrar_saida():
    d = request.json
    conn = get_db()
    conn.execute('UPDATE relacao_dia SET horario_saida=?, data_saida=? WHERE id=?',
                 (d['horario_saida'], hoje_recife(), d['id']))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/fechar_servico', methods=['POST'])
@login_required
def fechar_servico():
    conn = get_db()
    servico = get_servico_aberto(conn)
    hoje = hoje_recife()
    conn.execute("UPDATE servicos SET status='fechado', data_fim=? WHERE id=?", (hoje, servico['id']))
    conn.execute("INSERT INTO servicos (data_inicio, status) VALUES (?, 'aberto')", (hoje,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── CLI: criação do primeiro usuário ────────────────────────────────────

def _comando_criar_usuario():
    init_db()
    print("\n=== Criar usuário (bootstrap) ===")
    username = input("Usuário: ").strip()
    senha = input("Senha (mín. 6 caracteres): ").strip()
    ok, msg = criar_usuario(username, senha)
    print("Usuário criado com sucesso!" if ok else f"Erro: {msg}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'criar-usuario':
        _comando_criar_usuario()
    else:
        init_db()
        print("\n Sistema 71 BI Mtz iniciado!")
        print(f"Banco: {'Postgres' if USANDO_POSTGRES else 'SQLite local'}")
        print("Acesse: http://localhost:5000\n")
        app.run(debug=False, port=5000)
