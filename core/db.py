"""
Camada de banco de dados com suporte dual:
- SQLite local (padrão, quando DATABASE_URL não está definida) -> database.db
- Postgres (Neon/Supabase) quando DATABASE_URL está definida -> usado em produção (Vercel)

Todas as queries no app.py usam placeholder '?' (estilo sqlite).
Esta camada converte automaticamente para '%s' quando o backend é Postgres.
"""
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USANDO_POSTGRES = bool(DATABASE_URL)

if USANDO_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')


class Conexao:
    """Wrapper que unifica a interface sqlite3/psycopg usada pelo app.py."""

    def __init__(self):
        if USANDO_POSTGRES:
            self._conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False)
        else:
            self._conn = sqlite3.connect(DB_PATH)
            self._conn.row_factory = sqlite3.Row

    def _adaptar_sql(self, sql):
        if USANDO_POSTGRES:
            return sql.replace('?', '%s')
        return sql

    def execute(self, sql, params=()):
        sql = self._adaptar_sql(sql)
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, sql):
        # Usado só para criação de tabelas sqlite; postgres tem script próprio em init_db.
        self._conn.executescript(sql)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db():
    return Conexao()


def row_to_dict(row):
    """Converte sqlite3.Row ou dict (psycopg dict_row) para dict puro."""
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return dict(row)


def init_db():
    """Cria tabelas e roda migrações. Idempotente. Funciona em sqlite e postgres."""
    conn = get_db()

    if USANDO_POSTGRES:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT NOW()
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pessoas (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                ddd TEXT,
                telefone TEXT,
                veiculo TEXT,
                observacao TEXT,
                criado_em TIMESTAMP DEFAULT NOW()
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS servicos (
                id SERIAL PRIMARY KEY,
                data_inicio TEXT NOT NULL,
                data_fim TEXT,
                status TEXT NOT NULL DEFAULT 'aberto',
                criado_em TIMESTAMP DEFAULT NOW()
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS relacao_dia (
                id SERIAL PRIMARY KEY,
                servico_id INTEGER NOT NULL REFERENCES servicos(id),
                pessoa_id INTEGER NOT NULL REFERENCES pessoas(id),
                cracha_tipo TEXT,
                cracha_numero TEXT,
                secao TEXT,
                motivo TEXT,
                observacao TEXT,
                horario_entrada TEXT,
                horario_saida TEXT,
                data_entrada TEXT,
                data_saida TEXT
            )
        ''')
        conn.commit()
    else:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS pessoas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                ddd TEXT,
                telefone TEXT,
                veiculo TEXT,
                observacao TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_inicio TEXT NOT NULL,
                data_fim TEXT,
                status TEXT NOT NULL DEFAULT 'aberto',
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS relacao_dia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servico_id INTEGER NOT NULL,
                pessoa_id INTEGER NOT NULL,
                cracha_tipo TEXT,
                cracha_numero TEXT,
                secao TEXT,
                motivo TEXT,
                observacao TEXT,
                horario_entrada TEXT,
                horario_saida TEXT,
                data_entrada TEXT,
                data_saida TEXT,
                FOREIGN KEY (pessoa_id) REFERENCES pessoas(id),
                FOREIGN KEY (servico_id) REFERENCES servicos(id)
            );
        ''')

        # ── Migrações legadas (SQLite apenas, preservadas do app original) ──
        colunas = [r[1] for r in conn.execute("PRAGMA table_info(pessoas)").fetchall()]
        if 'veiculo' not in colunas:
            conn.execute("ALTER TABLE pessoas ADD COLUMN veiculo TEXT DEFAULT ''")
            if 'placa_carro' in colunas or 'placa_moto' in colunas:
                conn.execute("""
                    UPDATE pessoas SET veiculo = TRIM(
                        TRIM(COALESCE(NULLIF(placa_carro,''),'') ||
                        CASE WHEN COALESCE(placa_carro,'') != '' AND COALESCE(placa_moto,'') != '' THEN ' / ' ELSE '' END ||
                        COALESCE(NULLIF(placa_moto,''),'') ||
                        CASE WHEN (COALESCE(placa_carro,'') != '' OR COALESCE(placa_moto,'') != '') AND COALESCE(modelo_veiculo,'') != '' THEN ' - ' ELSE '' END ||
                        COALESCE(NULLIF(modelo_veiculo,''),''))
                    )
                """)
            print("Migracao concluida: coluna 'veiculo' adicionada.")

        colunas_rel = [r[1] for r in conn.execute("PRAGMA table_info(relacao_dia)").fetchall()]
        if 'servico_id' not in colunas_rel:
            conn.execute("ALTER TABLE relacao_dia RENAME TO relacao_dia_old")
            conn.execute('''
                CREATE TABLE relacao_dia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    servico_id INTEGER NOT NULL,
                    pessoa_id INTEGER NOT NULL,
                    cracha_tipo TEXT,
                    cracha_numero TEXT,
                    secao TEXT,
                    motivo TEXT,
                    observacao TEXT,
                    horario_entrada TEXT,
                    horario_saida TEXT,
                    data_entrada TEXT,
                    data_saida TEXT,
                    FOREIGN KEY (pessoa_id) REFERENCES pessoas(id),
                    FOREIGN KEY (servico_id) REFERENCES servicos(id)
                )
            ''')
            old_cols = [r[1] for r in conn.execute("PRAGMA table_info(relacao_dia_old)").fetchall()]
            if 'data' in old_cols:
                datas = [r[0] for r in conn.execute("SELECT DISTINCT data FROM relacao_dia_old").fetchall()]
                for dt in datas:
                    cur = conn.execute("INSERT INTO servicos (data_inicio, data_fim, status) VALUES (?, ?, 'fechado')", (dt, dt))
                    sid = cur.lastrowid
                    conn.execute('''
                        INSERT INTO relacao_dia (servico_id, pessoa_id, cracha_tipo, cracha_numero, secao, motivo,
                            observacao, horario_entrada, horario_saida, data_entrada, data_saida)
                        SELECT ?, pessoa_id, cracha_tipo, cracha_numero, secao, motivo,
                            observacao, horario_entrada, horario_saida, data, data
                        FROM relacao_dia_old WHERE data = ?
                    ''', (sid, dt))
            conn.execute("DROP TABLE relacao_dia_old")
            print("Migracao concluida: tabela 'relacao_dia' atualizada para usar servicos.")

        tabelas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if '_migracoes' not in tabelas:
            conn.execute("CREATE TABLE _migracoes (nome TEXT PRIMARY KEY)")

        from .utils import formatar_documento, formatar_telefone

        ja_rodou = conn.execute("SELECT 1 FROM _migracoes WHERE nome='formatar_cpf_rg'").fetchone()
        if not ja_rodou:
            pessoas_existentes = conn.execute("SELECT id, cpf, nome FROM pessoas").fetchall()
            conflitos = []
            for row in pessoas_existentes:
                novo = formatar_documento(row['cpf'])
                if novo != row['cpf']:
                    try:
                        conn.execute("UPDATE pessoas SET cpf=? WHERE id=?", (novo, row['id']))
                    except sqlite3.IntegrityError:
                        conflitos.append((row['nome'], row['cpf'], novo))
            conn.execute("INSERT INTO _migracoes (nome) VALUES ('formatar_cpf_rg')")
            print("Migracao concluida: CPF/RG formatados.")
            if conflitos:
                print(f"AVISO: {len(conflitos)} registro(s) mantiveram CPF original por conflito de duplicidade:")
                for nome, antigo, novo in conflitos:
                    print(f"   - {nome}: '{antigo}' (formatado seria '{novo}', ja existe)")

        ja_rodou_tel = conn.execute("SELECT 1 FROM _migracoes WHERE nome='formatar_telefone'").fetchone()
        if not ja_rodou_tel:
            pessoas_existentes = conn.execute("SELECT id, telefone FROM pessoas").fetchall()
            for row in pessoas_existentes:
                novo = formatar_telefone(row['telefone'])
                if novo != row['telefone']:
                    try:
                        conn.execute("UPDATE pessoas SET telefone=? WHERE id=?", (novo, row['id']))
                    except sqlite3.IntegrityError:
                        pass
            conn.execute("INSERT INTO _migracoes (nome) VALUES ('formatar_telefone')")
            print("Migracao concluida: telefones formatados.")

        conn.commit()

    # Garante que existe ao menos um serviço aberto (sqlite e postgres)
    from .utils import hoje_recife
    aberto = conn.execute("SELECT id FROM servicos WHERE status='aberto'").fetchone()
    if not aberto:
        conn.execute("INSERT INTO servicos (data_inicio, status) VALUES (?, 'aberto')", (hoje_recife(),))
        conn.commit()

    conn.close()
