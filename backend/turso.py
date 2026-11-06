"""Conexão com o Turso (SQLite na nuvem) que imita o sqlite3.

Usada quando a variável TURSO_DATABASE_URL está definida (ex.: no Render), para os dados
não se perderem quando o servidor reinicia. Fala com o Turso pela API HTTP dele
(protocolo Hrana, POST /v2/pipeline). Como o Turso é SQLite, o SQL do app continua igual.

Imita só o que o app usa: execute, executemany, executescript, "with con:" (transação),
cursor com fetchone/fetchall/lastrowid/rowcount, linhas acessíveis por índice ou nome
e sqlite3.IntegrityError.
"""
import base64
import re
import sqlite3

import httpx

_cliente = httpx.Client(timeout=30.0)
_PRAGMA = "PRAGMA foreign_keys = ON"
_NOMEADOS = re.compile(r"[:@$][A-Za-z_]\w*")


# ---------- conversão de valores Python <-> Turso ----------

def _valor_para_turso(v) -> dict:
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"type": "blob", "base64": base64.b64encode(bytes(v)).decode().rstrip("=")}
    return {"type": "text", "value": str(v)}


def _valor_do_turso(v: dict):
    tipo = v["type"]
    if tipo == "null":
        return None
    if tipo == "integer":
        return int(v["value"])
    if tipo == "float":
        return float(v["value"])
    if tipo == "blob":
        b64 = v["base64"]
        return base64.b64decode(b64 + "=" * (-len(b64) % 4))
    return v["value"]


def _comando(sql: str, parametros=()) -> dict:
    stmt: dict = {"sql": sql, "want_rows": True}
    if isinstance(parametros, dict):
        # Só manda os nomes que aparecem no SQL (o sqlite3 ignora chaves sobrando)
        nomes = dict.fromkeys(_NOMEADOS.findall(sql))
        stmt["named_args"] = [
            {"name": n, "value": _valor_para_turso(parametros[n[1:]])} for n in nomes if n[1:] in parametros
        ]
    else:
        stmt["args"] = [_valor_para_turso(v) for v in parametros]
    return {"type": "execute", "stmt": stmt}


def _erro(resultado: dict) -> Exception:
    erro = resultado.get("error") or {}
    msg = erro.get("message", "erro desconhecido no Turso")
    codigo = erro.get("code") or ""
    if "CONSTRAINT" in codigo.upper() or "constraint failed" in msg.lower():
        return sqlite3.IntegrityError(msg)
    return sqlite3.OperationalError(msg)


# ---------- linha e cursor ----------

class Linha:
    """Igual ao sqlite3.Row: linha[0], linha["nome"], dict(linha), linha.keys()."""

    __slots__ = ("_colunas", "_valores", "_indice")

    def __init__(self, colunas: list[str], valores: tuple, indice: dict[str, int]):
        self._colunas, self._valores, self._indice = colunas, valores, indice

    def keys(self) -> list[str]:
        return list(self._colunas)

    def __getitem__(self, chave):
        if isinstance(chave, str):
            return self._valores[self._indice[chave]]
        return self._valores[chave]

    def __iter__(self):
        return iter(self._valores)

    def __len__(self) -> int:
        return len(self._valores)

    def __repr__(self) -> str:
        return f"Linha({dict(zip(self._colunas, self._valores))})"


class Cursor:
    def __init__(self, resultado: dict | None = None):
        self._linhas: list[Linha] = []
        self._pos = 0
        self.lastrowid = None
        self.rowcount = -1
        if resultado:
            colunas = [c.get("name") or "" for c in resultado.get("cols", [])]
            indice = {nome: i for i, nome in enumerate(colunas)}
            self._linhas = [
                Linha(colunas, tuple(_valor_do_turso(v) for v in linha), indice) for linha in resultado.get("rows", [])
            ]
            rowid = resultado.get("last_insert_rowid")
            self.lastrowid = int(rowid) if rowid is not None else None
            self.rowcount = resultado.get("affected_row_count", -1)

    def fetchone(self):
        if self._pos >= len(self._linhas):
            return None
        self._pos += 1
        return self._linhas[self._pos - 1]

    def fetchall(self) -> list[Linha]:
        resto = self._linhas[self._pos:]
        self._pos = len(self._linhas)
        return resto

    def __iter__(self):
        while (linha := self.fetchone()) is not None:
            yield linha


# ---------- conexão ----------

class Conexao:
    """Fora de "with con:" cada comando roda sozinho (autocommit), numa única chamada HTTP.
    Dentro de "with con:" abre uma transação (BEGIN ... COMMIT/ROLLBACK) num stream do Turso."""

    def __init__(self, url: str, token: str):
        url = url.strip().rstrip("/")
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self._url_inicial = url
        self._url = url
        self._token = token
        self._baton = None
        self._profundidade = 0
        self._em_transacao = False

    def _enviar(self, pedidos: list[dict]) -> list[dict]:
        resp = _cliente.post(
            f"{self._url}/v2/pipeline",
            json={"baton": self._baton, "requests": pedidos},
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if resp.status_code != 200:
            self._baton, self._url, self._em_transacao = None, self._url_inicial, False
            raise sqlite3.OperationalError(f"Turso respondeu {resp.status_code}: {resp.text[:300]}")
        dados = resp.json()
        self._baton = dados.get("baton")
        if dados.get("base_url"):
            self._url = dados["base_url"].rstrip("/")
        return dados["results"]

    def _fim_do_stream(self) -> None:
        self._baton, self._url, self._em_transacao = None, self._url_inicial, False

    def _rodar(self, pedidos: list[dict]) -> list[dict]:
        """Manda os pedidos e devolve o resultado de cada um (levanta erro se algum falhar)."""
        if self._profundidade > 0:
            prefixo = []
            if not self._em_transacao:
                prefixo = [_comando(_PRAGMA), _comando("BEGIN")]
            resultados = self._enviar(prefixo + pedidos)
            for r in resultados[: len(prefixo)]:
                if r["type"] != "ok":
                    self._enviar([{"type": "close"}])
                    self._fim_do_stream()
                    raise _erro(r)
            if prefixo:
                self._em_transacao = True
            resultados = resultados[len(prefixo):]
        else:
            resultados = self._enviar([_comando(_PRAGMA)] + pedidos + [{"type": "close"}])
            self._fim_do_stream()
            resultados = resultados[1:-1]
        for r in resultados:
            if r["type"] != "ok":
                raise _erro(r)
        return [r["response"] for r in resultados]

    # --- API igual à do sqlite3 ---

    def execute(self, sql: str, parametros=()) -> Cursor:
        if sql.strip().upper().startswith("PRAGMA FOREIGN_KEYS"):
            return Cursor()  # já é ligado em todo pedido
        resposta = self._rodar([_comando(sql, parametros)])[0]
        return Cursor(resposta.get("result"))

    def executemany(self, sql: str, lista_parametros) -> Cursor:
        lista = list(lista_parametros)
        cur = Cursor()
        cur.rowcount = 0
        for i in range(0, len(lista), 200):
            for resposta in self._rodar([_comando(sql, p) for p in lista[i:i + 200]]):
                cur.rowcount += resposta["result"].get("affected_row_count", 0)
        return cur

    def executescript(self, script: str) -> Cursor:
        self._rodar([{"type": "sequence", "sql": script}])
        return Cursor()

    def _terminar(self, sql: str) -> None:
        if not self._em_transacao:
            return
        try:
            resultados = self._enviar([_comando(sql), {"type": "close"}])
        finally:
            self._fim_do_stream()
        if resultados[0]["type"] != "ok":
            raise _erro(resultados[0])

    def commit(self) -> None:
        self._terminar("COMMIT")

    def rollback(self) -> None:
        self._terminar("ROLLBACK")

    def close(self) -> None:
        if self._em_transacao:
            try:
                self._terminar("ROLLBACK")
            except Exception:
                pass
        self._profundidade = 0

    def __enter__(self):
        self._profundidade += 1
        return self

    def __exit__(self, tipo_erro, _valor, _tb):
        self._profundidade = max(0, self._profundidade - 1)
        if self._profundidade == 0:
            if tipo_erro is None:
                self.commit()
            else:
                self.rollback()
        return False
