"""Prepara um banco de DEMONSTRAÇÃO a partir do banco original, sem tocar no original.

O que faz:
  1. Abre backend/esportfit.db só para leitura e calcula uma "impressão digital" (SHA-256) dele.
  2. Copia tudo para um arquivo separado (padrão: backend/esportfit_demo.db) usando o backup do SQLite.
  3. Na cópia: atualiza a estrutura/catálogo e, se pedido, adiciona alunos e treinos de exemplo.
  4. Valida a cópia (integridade, chaves estrangeiras, tabelas e dados do original presentes).
  5. Confere que o original continua idêntico (mesma impressão digital).

Uso (PowerShell, dentro da pasta backend):
  .venv\\Scripts\\python preparar_demo.py                 # só a cópia validada
  .venv\\Scripts\\python preparar_demo.py --exemplos      # cópia + dados de exemplo
  .venv\\Scripts\\python preparar_demo.py --forcar        # recria a cópia se já existir

Para usar o banco de demonstração no servidor:
  $env:ESPORTFIT_DB = "esportfit_demo.db"; .venv\\Scripts\\python -m uvicorn main:app --host 0.0.0.0 --port 8000
"""
import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ORIGINAL_PADRAO = PASTA / "esportfit.db"
DESTINO_PADRAO = PASTA / "esportfit_demo.db"
TABELAS_OBRIGATORIAS = {"usuarios", "exercicios", "treinos", "treino_itens", "treinos_concluidos", "favoritos"}

SENHA_DEMO = "demo123"
PROFESSOR_DEMO = ("Professor Demo", "demo.professor@esportfit.com")
ALUNOS_DEMO = [
    ("Ana Demo", "ana.demo@esportfit.com"),
    ("Bruno Demo", "bruno.demo@esportfit.com"),
    ("Carla Demo", "carla.demo@esportfit.com"),
]
TREINOS_DEMO = [
    ("Treino A - Peito e Tríceps", ["Supino reto com barra", "Crucifixo na máquina (voador / peck deck)", "Tríceps na polia (pulley)"]),
    ("Treino B - Pernas", ["Leg press 45°", "Cadeira extensora", "Mesa flexora"]),
    ("Treino C - Costas e Bíceps", ["Puxada frontal (pulldown)", "Remada baixa sentada", "Rosca direta com barra"]),
]


class ErroDemo(Exception):
    pass


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def abrir_somente_leitura(caminho: Path) -> sqlite3.Connection:
    # mode=ro: o SQLite recusa qualquer escrita nesta conexão
    return sqlite3.connect(f"{caminho.as_uri()}?mode=ro", uri=True)


def contar_linhas(con: sqlite3.Connection) -> dict[str, int]:
    tabelas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tabelas}


def copiar(original: Path, destino: Path) -> dict[str, int]:
    """Copia o banco com a API de backup (cópia consistente, inclusive se o servidor estiver aberto)."""
    origem = abrir_somente_leitura(original)
    try:
        resultado = origem.execute("PRAGMA integrity_check").fetchone()[0]
        if resultado != "ok":
            raise ErroDemo(f"O banco original já está com problema de integridade: {resultado}")
        contagem = contar_linhas(origem)
        copia = sqlite3.connect(destino)
        try:
            origem.backup(copia)
        finally:
            copia.close()
    finally:
        origem.close()
    return contagem


def atualizar_estrutura(destino: Path) -> None:
    """Aplica as atualizações de tabelas e o catálogo de exercícios — só na cópia."""
    os.environ["ESPORTFIT_DB"] = str(destino)
    sys.path.insert(0, str(PASTA))
    import db  # noqa: E402  (lê ESPORTFIT_DB ao ser importado)

    if Path(db.CAMINHO_DB).resolve() != destino.resolve():
        raise ErroDemo("Segurança: o módulo db não está apontando para a cópia. Nada foi alterado.")
    db.iniciar_banco()


def adicionar_exemplos(destino: Path) -> list[str]:
    from seguranca import gerar_hash_senha

    con = sqlite3.connect(destino)
    con.execute("PRAGMA foreign_keys = ON")
    resumo = []
    try:
        with con:
            def usuario(nome, email, cargo):
                linha = con.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
                if linha:
                    return linha[0], False
                cur = con.execute(
                    "INSERT INTO usuarios (nome, email, senha_hash, cargo) VALUES (?, ?, ?, ?)",
                    (nome, email, gerar_hash_senha(SENHA_DEMO), cargo),
                )
                return cur.lastrowid, True

            prof_id, novo = usuario(*PROFESSOR_DEMO, "professor")
            resumo.append(f"professor {PROFESSOR_DEMO[1]} ({'criado' if novo else 'já existia'})")

            exercicios = {nome: i for i, nome in con.execute("SELECT id, nome FROM exercicios")}
            faltando = {n for _, lista in TREINOS_DEMO for n in lista} - exercicios.keys()
            if faltando:
                raise ErroDemo(f"Exercícios do catálogo não encontrados na cópia: {sorted(faltando)}")

            for indice, (nome, email) in enumerate(ALUNOS_DEMO):
                aluno_id, novo = usuario(nome, email, "aluno")
                if not novo:
                    resumo.append(f"aluno {email} (já existia, mantido como está)")
                    continue
                for ordem, (nome_treino, lista) in enumerate(TREINOS_DEMO, start=1):
                    treino_id = con.execute(
                        "INSERT INTO treinos (aluno_id, professor_id, nome, ordem) VALUES (?, ?, ?, ?)",
                        (aluno_id, prof_id, nome_treino, ordem),
                    ).lastrowid
                    con.executemany(
                        """INSERT INTO treino_itens (treino_id, exercicio_id, ordem, series, repeticoes, descanso_seg)
                           VALUES (?, ?, ?, 3, '10-12', 120)""",
                        [(treino_id, exercicios[n], pos) for pos, n in enumerate(lista, start=1)],
                    )
                    # Variedade para a demonstração: aluno 1 fez 0 treinos, aluno 2 fez 1, aluno 3 fez 2
                    if ordem <= indice:
                        con.execute(
                            "INSERT INTO treinos_concluidos (treino_id, aluno_id, concluido_em) "
                            "VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%f', 'now'))",
                            (treino_id, aluno_id),
                        )
                resumo.append(f"aluno {email} com {len(TREINOS_DEMO)} treinos ({indice} feito(s))")
    finally:
        con.close()
    return resumo


def validar(destino: Path, contagem_original: dict[str, int]) -> list[str]:
    con = abrir_somente_leitura(destino)
    problemas = []
    try:
        resultado = con.execute("PRAGMA integrity_check").fetchone()[0]
        if resultado != "ok":
            problemas.append(f"integrity_check: {resultado}")
        fks = con.execute("PRAGMA foreign_key_check").fetchall()
        if fks:
            problemas.append(f"{len(fks)} referência(s) quebrada(s) entre tabelas: {fks[:5]}")
        contagem = contar_linhas(con)
        if faltam := TABELAS_OBRIGATORIAS - contagem.keys():
            problemas.append(f"tabelas faltando: {sorted(faltam)}")
        for tabela, qtd in contagem_original.items():
            if contagem.get(tabela, 0) < qtd:
                problemas.append(f"tabela {tabela}: original tinha {qtd} linhas, cópia tem {contagem.get(tabela, 0)}")
        if not contagem.get("exercicios"):
            problemas.append("catálogo de exercícios vazio")
        if not con.execute("SELECT 1 FROM usuarios WHERE cargo = 'professor' LIMIT 1").fetchone():
            problemas.append("nenhum professor no banco")
    finally:
        con.close()
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera uma cópia do banco para demonstração, sem alterar o original.")
    parser.add_argument("--origem", type=Path, default=ORIGINAL_PADRAO, help="banco original (padrão: esportfit.db)")
    parser.add_argument("--destino", type=Path, default=DESTINO_PADRAO, help="cópia de demonstração (padrão: esportfit_demo.db)")
    parser.add_argument("--exemplos", action="store_true", help="adiciona professor, alunos e treinos de exemplo na cópia")
    parser.add_argument("--forcar", action="store_true", help="recria a cópia se ela já existir")
    args = parser.parse_args()

    original = args.origem.resolve()
    destino = args.destino.resolve()

    if not original.exists():
        print(f"ERRO: banco original não encontrado: {original}")
        return 1
    if destino == original:
        print("ERRO: o destino não pode ser o próprio banco original.")
        return 1
    if destino.exists():
        if not args.forcar:
            print(f"ERRO: {destino.name} já existe. Use --forcar para recriar a cópia (o original nunca é tocado).")
            return 1
        for sufixo in ("", "-wal", "-shm", "-journal"):
            Path(str(destino) + sufixo).unlink(missing_ok=True)

    impressao_antes = sha256(original)
    print(f"Original : {original}")
    print(f"           SHA-256 {impressao_antes[:16]}…")

    try:
        contagem_original = copiar(original, destino)
        print(f"Cópia    : {destino}")
        print("           " + ", ".join(f"{t}={n}" for t, n in sorted(contagem_original.items())))

        atualizar_estrutura(destino)
        if args.exemplos:
            for linha in adicionar_exemplos(destino):
                print(f"Exemplo  : {linha}")

        problemas = validar(destino, contagem_original)
    except (ErroDemo, sqlite3.Error) as e:
        print(f"ERRO: {e}")
        print("A cópia pode estar incompleta; o original não foi alterado.")
        return 1

    impressao_depois = sha256(original)
    if impressao_depois != impressao_antes:
        print("ERRO GRAVE: o banco original mudou durante a execução (o servidor estava gravando nele?). Verifique.")
        return 2

    if problemas:
        print("VALIDAÇÃO FALHOU:")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print("Validação: OK (integridade, chaves estrangeiras, tabelas e dados do original presentes)")
    print("Original : intacto (mesma impressão digital)")
    if args.exemplos:
        print(f"Logins de exemplo: {PROFESSOR_DEMO[1]} e alunos *.demo@esportfit.com — senha {SENHA_DEMO}")
    print('\nPara usar no servidor:  $env:ESPORTFIT_DB = "esportfit_demo.db"; .venv\\Scripts\\python -m uvicorn main:app --host 0.0.0.0 --port 8000')
    return 0


if __name__ == "__main__":
    sys.exit(main())
