"""Banco de dados SQLite: criação/atualização das tabelas, catálogo de exercícios e conexão."""
import json
import os
import sqlite3
from pathlib import Path

PASTA = Path(__file__).parent
CAMINHO_DB = Path(os.environ.get("ESPORTFIT_DB", PASTA / "esportfit.db"))
CATALOGO = PASTA / "catalogo" / "exercicios.json"

# No Render o disco é apagado a cada reinício: lá o banco fica no Turso (SQLite na nuvem).
# Sem essas variáveis (no seu PC), usa o arquivo esportfit.db normalmente.
TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    cargo       TEXT NOT NULL CHECK (cargo IN ('aluno', 'professor')),
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exercicios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    grupo_muscular  TEXT NOT NULL,
    aparelho        TEXT NOT NULL,
    como_usar       TEXT NOT NULL,
    dicas           TEXT NOT NULL DEFAULT '',
    video_url       TEXT
);

CREATE TABLE IF NOT EXISTS treinos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    professor_id  INTEGER NOT NULL REFERENCES usuarios(id),
    nome          TEXT NOT NULL,
    observacoes   TEXT NOT NULL DEFAULT '',
    ordem         INTEGER NOT NULL DEFAULT 0,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS treino_itens (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    treino_id     INTEGER NOT NULL REFERENCES treinos(id) ON DELETE CASCADE,
    exercicio_id  INTEGER NOT NULL REFERENCES exercicios(id) ON DELETE RESTRICT,
    ordem         INTEGER NOT NULL,
    series        INTEGER NOT NULL,
    repeticoes    TEXT NOT NULL,
    carga         TEXT NOT NULL DEFAULT '',
    descanso_seg  INTEGER NOT NULL DEFAULT 60,
    observacao    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS treinos_concluidos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    treino_id     INTEGER NOT NULL REFERENCES treinos(id) ON DELETE CASCADE,
    aluno_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    concluido_em  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS favoritos (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    exercicio_id  INTEGER NOT NULL REFERENCES exercicios(id) ON DELETE CASCADE,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (usuario_id, exercicio_id)
);
"""

# Colunas adicionadas depois da primeira versão (bancos antigos ganham essas colunas sozinhos)
COLUNAS_NOVAS_EXERCICIOS = {
    "codigo": "TEXT",                       # id no catálogo (Free Exercise DB); NULL = criado pelo professor
    "nome_en": "TEXT NOT NULL DEFAULT ''",
    "musculos_secundarios": "TEXT NOT NULL DEFAULT ''",
    "equipamento": "TEXT NOT NULL DEFAULT 'Outros'",
    "categoria": "TEXT NOT NULL DEFAULT 'Força'",
    "nivel": "TEXT NOT NULL DEFAULT 'Iniciante'",
    "imagens": "TEXT NOT NULL DEFAULT '[]'",  # lista JSON de URLs (fotos inicial/final do movimento)
    "video_arquivo": "TEXT",                # vídeo enviado pelo professor (pasta midia/)
    "traducao_automatica": "INTEGER NOT NULL DEFAULT 0",
    "editado": "INTEGER NOT NULL DEFAULT 0",  # 1 = professor alterou; o catálogo não sobrescreve mais
}


def conectar() -> sqlite3.Connection:
    if TURSO_URL:
        from turso import Conexao

        return Conexao(TURSO_URL, TURSO_TOKEN)
    con = sqlite3.connect(CAMINHO_DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def obter_conexao():
    """Dependência do FastAPI: abre uma conexão por requisição."""
    con = conectar()
    try:
        yield con
    finally:
        con.close()


# Como os treinos "feitos" do aluno voltam a ficar pendentes (configurado pelo professor, por aluno)
COLUNAS_NOVAS_USUARIOS = {
    "modo_reinicio": "TEXT NOT NULL DEFAULT 'semanal'",  # 'semanal' | 'ao_completar' | 'manual'
    "dia_reinicio": "INTEGER NOT NULL DEFAULT 0",          # 0 = segunda ... 6 = domingo (modo semanal)
    "reiniciado_em": "TEXT",                               # última vez que o professor clicou em "Reiniciar agora"
}


def _adicionar_colunas(con: sqlite3.Connection, tabela: str, colunas: dict) -> None:
    existentes = {r["name"] for r in con.execute(f"PRAGMA table_info({tabela})")}
    for coluna, tipo in colunas.items():
        if coluna not in existentes:
            con.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def _atualizar_estrutura(con: sqlite3.Connection) -> None:
    _adicionar_colunas(con, "exercicios", COLUNAS_NOVAS_EXERCICIOS)
    _adicionar_colunas(con, "usuarios", COLUNAS_NOVAS_USUARIOS)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_exercicios_codigo ON exercicios(codigo)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_concluidos_aluno ON treinos_concluidos(aluno_id, concluido_em)")


def sincronizar_catalogo(con: sqlite3.Connection) -> int:
    """Insere/atualiza os exercícios do catálogo. Exercícios editados pelo professor não são tocados."""
    if not CATALOGO.exists():
        return 0
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))

    # Bancos da versão 1: os 22 exercícios iniciais não tinham código -> liga pelo nome
    con.executemany(
        "UPDATE exercicios SET codigo = ? WHERE codigo IS NULL AND nome = ?",
        [(e["codigo"], e["nome"]) for e in catalogo if not e["traducao_automatica"]],
    )

    con.executemany(
        """INSERT INTO exercicios
             (codigo, nome, nome_en, grupo_muscular, musculos_secundarios, equipamento, aparelho,
              categoria, nivel, como_usar, dicas, imagens, traducao_automatica)
           VALUES (:codigo, :nome, :nome_en, :grupo_muscular, :musculos_secundarios, :equipamento, :aparelho,
                   :categoria, :nivel, :como_usar, :dicas, :imagens_json, :traducao_automatica)
           ON CONFLICT(codigo) DO UPDATE SET
             nome = excluded.nome, nome_en = excluded.nome_en, grupo_muscular = excluded.grupo_muscular,
             musculos_secundarios = excluded.musculos_secundarios, equipamento = excluded.equipamento,
             aparelho = excluded.aparelho, categoria = excluded.categoria, nivel = excluded.nivel,
             como_usar = excluded.como_usar, dicas = excluded.dicas, imagens = excluded.imagens,
             traducao_automatica = excluded.traducao_automatica
           WHERE exercicios.editado = 0""",
        [{**e, "imagens_json": json.dumps(e["imagens"])} for e in catalogo],
    )
    # Exercícios editados mantêm o texto do professor, mas ganham as fotos do catálogo
    con.executemany(
        "UPDATE exercicios SET imagens = ? WHERE codigo = ? AND editado = 1 AND imagens = '[]'",
        [(json.dumps(e["imagens"]), e["codigo"]) for e in catalogo],
    )
    return len(catalogo)


def iniciar_banco() -> None:
    from seguranca import gerar_hash_senha

    con = conectar()
    with con:
        con.executescript(ESQUEMA)
        _atualizar_estrutura(con)
        total = sincronizar_catalogo(con)

        # Primeiro professor (só se ainda não existir nenhum)
        tem_professor = con.execute(
            "SELECT 1 FROM usuarios WHERE cargo = 'professor' LIMIT 1"
        ).fetchone()
        if not tem_professor:
            email = os.environ.get("PROFESSOR_EMAIL", "professor@esportfit.com")
            senha = os.environ.get("PROFESSOR_SENHA", "esport123")
            con.execute(
                "INSERT INTO usuarios (nome, email, senha_hash, cargo) VALUES (?, ?, ?, 'professor')",
                ("Professor", email, gerar_hash_senha(senha)),
            )
            print(f"[Esport Fit] Professor inicial criado: {email} / {senha}  (troque a senha!)")
    con.close()
    print(f"[Esport Fit] Catálogo: {total} exercícios")
