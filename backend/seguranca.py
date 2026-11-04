"""Senhas, tokens de login e controle de cargo."""
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import obter_conexao

ITERACOES = 200_000
VALIDADE_TOKEN = timedelta(days=365)  # login fica salvo no celular por 1 ano


def _carregar_chave() -> str:
    """Usa ESPORTFIT_CHAVE se definida; senão gera uma e guarda em .chave_secreta."""
    if chave := os.environ.get("ESPORTFIT_CHAVE"):
        return chave
    arquivo = Path(__file__).parent / ".chave_secreta"
    if not arquivo.exists():
        arquivo.write_text(secrets.token_urlsafe(48))
    return arquivo.read_text().strip()


CHAVE_SECRETA = _carregar_chave()


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
    return f"{ITERACOES}${sal.hex()}${dk.hex()}"


def conferir_senha(senha: str, guardado: str) -> bool:
    iteracoes, sal_hex, dk_hex = guardado.split("$")
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), int(iteracoes))
    return hmac.compare_digest(dk.hex(), dk_hex)


def criar_token(usuario_id: int) -> str:
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(usuario_id), "iat": agora, "exp": agora + VALIDADE_TOKEN}
    return jwt.encode(dados, CHAVE_SECRETA, algorithm="HS256")


_bearer = HTTPBearer(auto_error=False)


def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    con: sqlite3.Connection = Depends(obter_conexao),
) -> dict:
    erro = HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login novamente.")
    if cred is None:
        raise erro
    try:
        dados = jwt.decode(cred.credentials, CHAVE_SECRETA, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise erro
    linha = con.execute(
        "SELECT id, nome, email, cargo FROM usuarios WHERE id = ?", (int(dados["sub"]),)
    ).fetchone()
    if linha is None:
        raise erro
    return dict(linha)


def somente_professor(usuario: dict = Depends(usuario_atual)) -> dict:
    if usuario["cargo"] != "professor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas professores podem fazer isso.")
    return usuario
