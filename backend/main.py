"""API do app Esport Fit.

Rodar:  .venv\\Scripts\\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Docs interativas: http://localhost:8000/docs
"""
import json
import secrets
import sqlite3
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import ciclo
from db import iniciar_banco, obter_conexao
from seguranca import (
    conferir_senha,
    criar_token,
    gerar_hash_senha,
    somente_professor,
    usuario_atual,
)

PASTA_MIDIA = Path(__file__).parent / "midia"
PASTA_VIDEOS = PASTA_MIDIA / "videos"
PASTA_VIDEOS.mkdir(parents=True, exist_ok=True)
TAMANHO_MAX_VIDEO = 200 * 1024 * 1024  # 200 MB
EXTENSOES_VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".3gp", ".mkv"}


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    iniciar_banco()
    yield


app = FastAPI(title="Esport Fit API", lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/midia", StaticFiles(directory=PASTA_MIDIA), name="midia")

Con = sqlite3.Connection


# ============================ MODELOS ============================

class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str
    senha: str = Field(min_length=6, max_length=100)

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("E-mail inválido")
        return v


class NovoUsuario(Cadastro):
    cargo: Literal["aluno", "professor"] = "aluno"


class Login(BaseModel):
    email: str
    senha: str


class ExercicioEntrada(BaseModel):
    nome: str = Field(min_length=2)
    grupo_muscular: str = Field(min_length=2)
    aparelho: str = Field(min_length=2)
    equipamento: str = "Outros"
    categoria: str = "Força"
    nivel: str = "Iniciante"
    musculos_secundarios: str = ""
    como_usar: str = Field(min_length=5)
    dicas: str = ""
    video_url: str | None = None


class ItemEntrada(BaseModel):
    exercicio_id: int
    series: int = Field(ge=1, le=20)
    repeticoes: str = Field(min_length=1, description="Ex.: '12', '10-12', '30s'")
    carga: str = ""
    descanso_seg: int = Field(default=120, ge=0, le=600)  # padrão: 2 minutos
    observacao: str = ""


class ReinicioEntrada(BaseModel):
    modo: Literal["semanal", "ao_completar", "manual"]
    dia_reinicio: int = Field(default=0, ge=0, le=6, description="0 = segunda ... 6 = domingo")


class TreinoEntrada(BaseModel):
    aluno_id: int
    nome: str = Field(min_length=1, description="Ex.: 'Treino A - Peito e Tríceps'")
    observacoes: str = ""
    ordem: int = 0
    itens: list[ItemEntrada] = Field(min_length=1)


# ============================ AUXILIARES ============================

def normalizar(texto: str) -> str:
    """Minúsculas e sem acento, para busca e ordenação ('Tríceps' == 'triceps')."""
    t = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def _midia_publica(arquivo: str | None) -> str | None:
    return f"/midia/{arquivo}" if arquivo else None


def _exercicio_completo(linha: sqlite3.Row, favorito: bool = False) -> dict:
    e = dict(linha)
    e["imagens"] = json.loads(e.get("imagens") or "[]")
    e["video"] = _midia_publica(e.pop("video_arquivo", None))
    e["favorito"] = favorito
    return e


def _resposta_login(usuario: dict) -> dict:
    return {"token": criar_token(usuario["id"]), "usuario": usuario}


def _buscar_usuario_publico(con: Con, usuario_id: int) -> dict:
    linha = con.execute(
        "SELECT id, nome, email, cargo FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return dict(linha)


def _inserir_usuario(con: Con, dados: Cadastro, cargo: str) -> dict:
    try:
        with con:
            cur = con.execute(
                "INSERT INTO usuarios (nome, email, senha_hash, cargo) VALUES (?, ?, ?, ?)",
                (dados.nome.strip(), dados.email, gerar_hash_senha(dados.senha), cargo),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com esse e-mail.")
    return _buscar_usuario_publico(con, cur.lastrowid)


def _montar_treino(con: Con, treino_id: int) -> dict | None:
    """Treino completo com os exercícios, fotos, vídeo e instruções de cada aparelho."""
    t = con.execute(
        """SELECT t.*, p.nome AS professor_nome, a.nome AS aluno_nome
           FROM treinos t
           JOIN usuarios p ON p.id = t.professor_id
           JOIN usuarios a ON a.id = t.aluno_id
           WHERE t.id = ?""",
        (treino_id,),
    ).fetchone()
    if t is None:
        return None
    itens = con.execute(
        """SELECT i.id, i.ordem, i.series, i.repeticoes, i.carga, i.descanso_seg, i.observacao,
                  e.id AS exercicio_id, e.nome, e.grupo_muscular, e.aparelho, e.equipamento, e.categoria,
                  e.como_usar, e.dicas, e.video_url, e.video_arquivo, e.imagens, e.traducao_automatica
           FROM treino_itens i JOIN exercicios e ON e.id = i.exercicio_id
           WHERE i.treino_id = ? ORDER BY i.ordem""",
        (treino_id,),
    ).fetchall()
    lista = []
    for i in itens:
        d = dict(i)
        d["imagens"] = json.loads(d["imagens"] or "[]")
        d["video"] = _midia_publica(d.pop("video_arquivo"))
        lista.append(d)
    ultima = con.execute(
        "SELECT MAX(concluido_em) FROM treinos_concluidos WHERE treino_id = ?", (treino_id,)
    ).fetchone()[0]
    return {**dict(t), "ultima_conclusao": ultima, "itens": lista}


def _treino_ou_404(con: Con, treino_id: int) -> dict:
    treino = _montar_treino(con, treino_id)
    if treino is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado.")
    return treino


def _checar_aluno(con: Con, aluno_id: int) -> None:
    ok = con.execute(
        "SELECT 1 FROM usuarios WHERE id = ? AND cargo = 'aluno'", (aluno_id,)
    ).fetchone()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado.")


def _exercicio_ou_404(con: Con, exercicio_id: int) -> sqlite3.Row:
    linha = con.execute("SELECT * FROM exercicios WHERE id = ?", (exercicio_id,)).fetchone()
    if linha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercício não encontrado.")
    return linha


def _salvar_itens(con: Con, treino_id: int, itens: list[ItemEntrada]) -> None:
    ids = {i.exercicio_id for i in itens}
    existentes = {
        r[0]
        for r in con.execute(
            f"SELECT id FROM exercicios WHERE id IN ({','.join('?' * len(ids))})", tuple(ids)
        )
    }
    if faltando := ids - existentes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Exercício inexistente: {sorted(faltando)}")
    con.execute("DELETE FROM treino_itens WHERE treino_id = ?", (treino_id,))
    con.executemany(
        """INSERT INTO treino_itens
           (treino_id, exercicio_id, ordem, series, repeticoes, carga, descanso_seg, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (treino_id, i.exercicio_id, n, i.series, i.repeticoes, i.carga, i.descanso_seg, i.observacao)
            for n, i in enumerate(itens, start=1)
        ],
    )


def _ids_treinos_do_aluno(con: Con, aluno_id: int) -> list[int]:
    return [
        r[0]
        for r in con.execute(
            "SELECT id FROM treinos WHERE aluno_id = ? ORDER BY ordem, id", (aluno_id,)
        )
    ]


def _semana_do_aluno(con: Con, aluno_id: int) -> dict:
    """Treinos do aluno na ordem, cada um marcado como feito (ou não) no ciclo atual."""
    ids = _ids_treinos_do_aluno(con, aluno_id)
    info = ciclo.calcular(con, aluno_id, ids)
    feitos = info.pop("feitos")
    treinos = []
    for i in ids:
        t = _montar_treino(con, i)
        t["feito_em"] = feitos.get(i)
        t["feito"] = t["feito_em"] is not None
        treinos.append(t)
    proximo = next((t["id"] for t in treinos if not t["feito"]), None)
    for t in treinos:
        t["proximo"] = t["id"] == proximo
    return {"ciclo": info, "treinos": treinos}


def _apagar_arquivo_video(arquivo: str | None) -> None:
    if arquivo:
        caminho = (PASTA_MIDIA / arquivo).resolve()
        if caminho.is_relative_to(PASTA_MIDIA.resolve()) and caminho.exists():
            caminho.unlink()


# ============================ LOGIN ============================

@app.post("/auth/cadastro", tags=["login"])
def cadastrar_aluno(dados: Cadastro, con: Con = Depends(obter_conexao)):
    """Qualquer pessoa pode criar conta, sempre como aluno."""
    return _resposta_login(_inserir_usuario(con, dados, "aluno"))


@app.post("/auth/login", tags=["login"])
def login(dados: Login, con: Con = Depends(obter_conexao)):
    linha = con.execute(
        "SELECT id, nome, email, cargo, senha_hash FROM usuarios WHERE email = ?",
        (dados.email.strip().lower(),),
    ).fetchone()
    if linha is None or not conferir_senha(dados.senha, linha["senha_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    usuario = {k: linha[k] for k in ("id", "nome", "email", "cargo")}
    return _resposta_login(usuario)


@app.get("/auth/eu", tags=["login"])
def eu(usuario: dict = Depends(usuario_atual)):
    return usuario


# ============================ PROFESSOR: USUÁRIOS ============================

@app.post("/usuarios", tags=["professor"])
def criar_usuario(
    dados: NovoUsuario, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    """Professor cadastra um aluno ou outro professor."""
    return _inserir_usuario(con, dados, dados.cargo)


@app.get("/alunos", tags=["professor"])
def listar_alunos(_p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)):
    linhas = con.execute(
        """SELECT u.id, u.nome, u.email, COUNT(t.id) AS total_treinos
           FROM usuarios u LEFT JOIN treinos t ON t.aluno_id = u.id
           WHERE u.cargo = 'aluno'
           GROUP BY u.id ORDER BY u.nome COLLATE NOCASE"""
    ).fetchall()
    resultado = []
    for l in linhas:
        info = ciclo.calcular(con, l["id"], _ids_treinos_do_aluno(con, l["id"]))
        resultado.append({**dict(l), "total_feitos": info["total_feitos"]})
    return resultado


@app.get("/alunos/{aluno_id}/treinos", tags=["professor"])
def treinos_do_aluno(
    aluno_id: int, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    _checar_aluno(con, aluno_id)
    return _semana_do_aluno(con, aluno_id)["treinos"]


@app.get("/alunos/{aluno_id}/semana", tags=["professor"])
def semana_do_aluno(aluno_id: int, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)):
    """Treinos do aluno com o que já foi feito + regra de reinício."""
    _checar_aluno(con, aluno_id)
    return _semana_do_aluno(con, aluno_id)


@app.put("/alunos/{aluno_id}/reinicio", tags=["professor"])
def configurar_reinicio(
    aluno_id: int, dados: ReinicioEntrada, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    """Define quando os treinos feitos desse aluno voltam a ficar pendentes."""
    _checar_aluno(con, aluno_id)
    with con:
        con.execute(
            "UPDATE usuarios SET modo_reinicio = ?, dia_reinicio = ? WHERE id = ?",
            (dados.modo, dados.dia_reinicio, aluno_id),
        )
    return _semana_do_aluno(con, aluno_id)


@app.put("/alunos/reinicio", tags=["professor"])
def configurar_reinicio_todos(
    dados: ReinicioEntrada, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    """Aplica a mesma regra de reinício a todos os alunos."""
    with con:
        cur = con.execute(
            "UPDATE usuarios SET modo_reinicio = ?, dia_reinicio = ? WHERE cargo = 'aluno'",
            (dados.modo, dados.dia_reinicio),
        )
    return {"alunos_atualizados": cur.rowcount, "descricao": ciclo.descrever(dados.modo, dados.dia_reinicio)}


@app.post("/alunos/{aluno_id}/reiniciar", tags=["professor"])
def reiniciar_agora(aluno_id: int, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)):
    """Todos os treinos do aluno voltam a ficar pendentes agora (o histórico continua guardado)."""
    _checar_aluno(con, aluno_id)
    with con:
        con.execute("UPDATE usuarios SET reiniciado_em = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE id = ?", (aluno_id,))
    return _semana_do_aluno(con, aluno_id)


# ============================ EXERCÍCIOS ============================

@app.get("/exercicios", tags=["exercícios"])
def listar_exercicios(
    q: str | None = None,
    grupo: str | None = None,
    equipamento: str | None = None,
    usuario: dict = Depends(usuario_atual),
    con: Con = Depends(obter_conexao),
):
    """Lista resumida (sem o passo a passo) para a busca. Favoritos do usuário vêm primeiro."""
    favoritos = {
        r[0] for r in con.execute("SELECT exercicio_id FROM favoritos WHERE usuario_id = ?", (usuario["id"],))
    }
    linhas = con.execute(
        """SELECT id, nome, nome_en, grupo_muscular, equipamento, categoria, nivel, aparelho, imagens,
                  video_arquivo IS NOT NULL OR video_url IS NOT NULL AS tem_video
           FROM exercicios"""
    ).fetchall()
    termo = normalizar(q).split() if q else []
    resultado = []
    for l in linhas:
        if grupo and l["grupo_muscular"] != grupo:
            continue
        if equipamento and l["equipamento"] != equipamento:
            continue
        if termo:
            alvo = normalizar(f"{l['nome']} {l['nome_en']} {l['grupo_muscular']} {l['equipamento']} {l['aparelho']}")
            if not all(t in alvo for t in termo):
                continue
        imagens = json.loads(l["imagens"] or "[]")
        resultado.append({
            "id": l["id"], "nome": l["nome"], "nome_en": l["nome_en"], "grupo_muscular": l["grupo_muscular"],
            "equipamento": l["equipamento"], "categoria": l["categoria"], "nivel": l["nivel"],
            "imagem": imagens[0] if imagens else None, "tem_video": bool(l["tem_video"]),
            "favorito": l["id"] in favoritos,
        })
    resultado.sort(key=lambda e: (not e["favorito"], normalizar(e["nome"])))
    return resultado


@app.get("/exercicios/{exercicio_id}", tags=["exercícios"])
def ver_exercicio(exercicio_id: int, usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    linha = _exercicio_ou_404(con, exercicio_id)
    fav = con.execute(
        "SELECT 1 FROM favoritos WHERE usuario_id = ? AND exercicio_id = ?", (usuario["id"], exercicio_id)
    ).fetchone()
    return _exercicio_completo(linha, bool(fav))


@app.post("/exercicios", tags=["exercícios"])
def criar_exercicio(
    dados: ExercicioEntrada, prof: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    with con:
        cur = con.execute(
            """INSERT INTO exercicios (nome, grupo_muscular, aparelho, equipamento, categoria, nivel,
                                       musculos_secundarios, como_usar, dicas, video_url, editado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (dados.nome, dados.grupo_muscular, dados.aparelho, dados.equipamento, dados.categoria, dados.nivel,
             dados.musculos_secundarios, dados.como_usar, dados.dicas, dados.video_url),
        )
    return ver_exercicio(cur.lastrowid, prof, con)


@app.put("/exercicios/{exercicio_id}", tags=["exercícios"])
def editar_exercicio(
    exercicio_id: int,
    dados: ExercicioEntrada,
    prof: dict = Depends(somente_professor),
    con: Con = Depends(obter_conexao),
):
    _exercicio_ou_404(con, exercicio_id)
    with con:
        con.execute(
            """UPDATE exercicios SET nome=?, grupo_muscular=?, aparelho=?, equipamento=?, categoria=?, nivel=?,
                                     musculos_secundarios=?, como_usar=?, dicas=?, video_url=?,
                                     editado=1, traducao_automatica=0
               WHERE id = ?""",
            (dados.nome, dados.grupo_muscular, dados.aparelho, dados.equipamento, dados.categoria, dados.nivel,
             dados.musculos_secundarios, dados.como_usar, dados.dicas, dados.video_url, exercicio_id),
        )
    return ver_exercicio(exercicio_id, prof, con)


@app.delete("/exercicios/{exercicio_id}", tags=["exercícios"], status_code=204)
def apagar_exercicio(
    exercicio_id: int, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    linha = _exercicio_ou_404(con, exercicio_id)
    if linha["codigo"]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Exercícios do catálogo não podem ser apagados (eles voltariam na próxima atualização). "
            "Você pode editá-los à vontade.",
        )
    try:
        with con:
            con.execute("DELETE FROM exercicios WHERE id = ?", (exercicio_id,))
    except sqlite3.IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esse exercício está em algum treino. Remova-o dos treinos antes."
        )
    _apagar_arquivo_video(linha["video_arquivo"])


# ---------- Favoritos (cada professor tem os seus) ----------

@app.put("/exercicios/{exercicio_id}/favorito", tags=["exercícios"])
def favoritar(exercicio_id: int, usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    _exercicio_ou_404(con, exercicio_id)
    with con:
        con.execute(
            "INSERT OR IGNORE INTO favoritos (usuario_id, exercicio_id) VALUES (?, ?)", (usuario["id"], exercicio_id)
        )
    return {"favorito": True}


@app.delete("/exercicios/{exercicio_id}/favorito", tags=["exercícios"])
def desfavoritar(exercicio_id: int, usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    with con:
        con.execute(
            "DELETE FROM favoritos WHERE usuario_id = ? AND exercicio_id = ?", (usuario["id"], exercicio_id)
        )
    return {"favorito": False}


# ---------- Vídeo do aparelho (gravado pelo professor) ----------

@app.post("/exercicios/{exercicio_id}/video", tags=["exercícios"])
async def enviar_video(
    exercicio_id: int,
    arquivo: UploadFile,
    prof: dict = Depends(somente_professor),
    con: Con = Depends(obter_conexao),
):
    linha = _exercicio_ou_404(con, exercicio_id)
    extensao = Path(arquivo.filename or "").suffix.lower() or ".mp4"
    if extensao not in EXTENSOES_VIDEO and not (arquivo.content_type or "").startswith("video/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie um arquivo de vídeo (mp4, mov...).")
    if extensao not in EXTENSOES_VIDEO:
        extensao = ".mp4"

    nome = f"{exercicio_id}_{secrets.token_hex(6)}{extensao}"
    destino = PASTA_VIDEOS / nome
    total = 0
    with open(destino, "wb") as f:
        while bloco := await arquivo.read(1024 * 1024):
            total += len(bloco)
            if total > TAMANHO_MAX_VIDEO:
                f.close()
                destino.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Vídeo maior que 200 MB.")
            f.write(bloco)

    with con:
        con.execute("UPDATE exercicios SET video_arquivo = ? WHERE id = ?", (f"videos/{nome}", exercicio_id))
    _apagar_arquivo_video(linha["video_arquivo"])
    return ver_exercicio(exercicio_id, prof, con)


@app.delete("/exercicios/{exercicio_id}/video", tags=["exercícios"])
def apagar_video(exercicio_id: int, prof: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)):
    linha = _exercicio_ou_404(con, exercicio_id)
    with con:
        con.execute("UPDATE exercicios SET video_arquivo = NULL WHERE id = ?", (exercicio_id,))
    _apagar_arquivo_video(linha["video_arquivo"])
    return ver_exercicio(exercicio_id, prof, con)


# ============================ PROFESSOR: TREINOS ============================

@app.post("/treinos", tags=["professor"])
def criar_treino(
    dados: TreinoEntrada, prof: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)
):
    _checar_aluno(con, dados.aluno_id)
    with con:
        cur = con.execute(
            "INSERT INTO treinos (aluno_id, professor_id, nome, observacoes, ordem) VALUES (?, ?, ?, ?, ?)",
            (dados.aluno_id, prof["id"], dados.nome, dados.observacoes, dados.ordem),
        )
        _salvar_itens(con, cur.lastrowid, dados.itens)
    return _montar_treino(con, cur.lastrowid)


@app.put("/treinos/{treino_id}", tags=["professor"])
def editar_treino(
    treino_id: int,
    dados: TreinoEntrada,
    prof: dict = Depends(somente_professor),
    con: Con = Depends(obter_conexao),
):
    _treino_ou_404(con, treino_id)
    _checar_aluno(con, dados.aluno_id)
    with con:
        con.execute(
            "UPDATE treinos SET aluno_id=?, professor_id=?, nome=?, observacoes=?, ordem=? WHERE id=?",
            (dados.aluno_id, prof["id"], dados.nome, dados.observacoes, dados.ordem, treino_id),
        )
        _salvar_itens(con, treino_id, dados.itens)
    return _montar_treino(con, treino_id)


@app.delete("/treinos/{treino_id}", tags=["professor"], status_code=204)
def apagar_treino(treino_id: int, _p: dict = Depends(somente_professor), con: Con = Depends(obter_conexao)):
    with con:
        cur = con.execute("DELETE FROM treinos WHERE id = ?", (treino_id,))
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado.")


# ============================ ALUNO ============================

@app.get("/meus-treinos", tags=["aluno"])
def meus_treinos(usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    """Treinos na ordem (A, B, C...), cada um com 'feito' / 'feito_em' no ciclo atual."""
    return _semana_do_aluno(con, usuario["id"])["treinos"]


@app.get("/meus-treinos/semana", tags=["aluno"])
def minha_semana(usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    """Igual a /meus-treinos, com a regra de reinício e quantos já foram feitos."""
    return _semana_do_aluno(con, usuario["id"])


@app.get("/meus-treinos/indicado", tags=["aluno"])
def treino_indicado(usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    """O primeiro treino da ordem que ainda não foi feito no ciclo (ou o primeiro, se todos já foram)."""
    treinos = _semana_do_aluno(con, usuario["id"])["treinos"]
    if not treinos:
        return None
    return next((t for t in treinos if not t["feito"]), treinos[0])


@app.get("/treinos/{treino_id}", tags=["aluno"])
def ver_treino(treino_id: int, usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    treino = _treino_ou_404(con, treino_id)
    if usuario["cargo"] != "professor" and treino["aluno_id"] != usuario["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado.")
    semana = _semana_do_aluno(con, treino["aluno_id"])
    return next(t for t in semana["treinos"] if t["id"] == treino_id)


@app.post("/treinos/{treino_id}/concluir", tags=["aluno"])
def concluir_treino(treino_id: int, usuario: dict = Depends(usuario_atual), con: Con = Depends(obter_conexao)):
    """Marca como feito. Pode ser repetido (refazer) — cada vez fica registrada no histórico."""
    treino = _treino_ou_404(con, treino_id)
    if treino["aluno_id"] != usuario["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado.")
    with con:
        con.execute(
            "INSERT INTO treinos_concluidos (treino_id, aluno_id, concluido_em) VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%f', 'now'))",
            (treino_id, usuario["id"]),
        )
    semana = _semana_do_aluno(con, usuario["id"])
    proximo = next((t for t in semana["treinos"] if not t["feito"]), None)
    return {"ok": True, "proximo": proximo, "ciclo": semana["ciclo"], "todos_feitos": proximo is None}
