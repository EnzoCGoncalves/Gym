"""Ciclo de treinos do aluno: quais treinos já foram feitos e quando tudo volta a ficar pendente.

Modos (escolhidos pelo professor, para cada aluno):
  - semanal:      toda semana, no dia escolhido (meia-noite), os treinos voltam a ficar pendentes.
  - ao_completar: quando o aluno faz todos os treinos, eles voltam a ficar pendentes no dia seguinte.
  - manual:       só quando o professor clica em "Reiniciar agora".
Em qualquer modo, "Reiniciar agora" zera na hora.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

# Fuso da academia (Brasília = -3). Pode ser trocado com a variável ESPORTFIT_FUSO.
FUSO = timezone(timedelta(hours=int(os.environ.get("ESPORTFIT_FUSO", "-3"))))
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MODOS = ("semanal", "ao_completar", "manual")


def _de_banco(texto: str | None) -> datetime | None:
    """Datas do SQLite (datetime('now')) estão em UTC, no formato 'AAAA-MM-DD HH:MM:SS'."""
    if not texto:
        return None
    return datetime.fromisoformat(texto).replace(tzinfo=timezone.utc)


def _meia_noite(dt: datetime) -> datetime:
    local = dt.astimezone(FUSO)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def agora() -> datetime:
    return datetime.now(timezone.utc)


def calcular(con: sqlite3.Connection, aluno_id: int, ids_treinos: list[int], momento: datetime | None = None) -> dict:
    """Devolve as regras do ciclo atual e a data em que cada treino foi feito dentro dele."""
    momento = momento or agora()
    u = con.execute(
        "SELECT modo_reinicio, dia_reinicio, reiniciado_em FROM usuarios WHERE id = ?", (aluno_id,)
    ).fetchone()
    modo = u["modo_reinicio"] if u and u["modo_reinicio"] in MODOS else "semanal"
    dia = u["dia_reinicio"] if u and u["dia_reinicio"] is not None else 0
    reinicio_manual = _de_banco(u["reiniciado_em"]) if u else None

    conclusoes = [
        (r["treino_id"], _de_banco(r["concluido_em"]))
        for r in con.execute(
            "SELECT treino_id, concluido_em FROM treinos_concluidos WHERE aluno_id = ? ORDER BY concluido_em, id",
            (aluno_id,),
        )
    ]

    inicio = reinicio_manual
    proximo_reinicio = None

    if modo == "semanal":
        hoje = _meia_noite(momento)
        inicio_semana = hoje - timedelta(days=(hoje.weekday() - dia) % 7)
        inicio = max(filter(None, [inicio, inicio_semana]))
        proximo_reinicio = inicio_semana + timedelta(days=7)

    elif modo == "ao_completar" and ids_treinos:
        pendentes = set(ids_treinos)
        for treino_id, quando in conclusoes:
            if inicio and quando < inicio:
                continue
            pendentes.discard(treino_id)
            if not pendentes:
                recomeco = _meia_noite(quando) + timedelta(days=1)
                if recomeco > momento:
                    proximo_reinicio = recomeco  # completou tudo; recomeça amanhã
                    break
                inicio, pendentes = recomeco, set(ids_treinos)

    feitos: dict[int, datetime] = {}
    for treino_id, quando in conclusoes:
        if (inicio is None or quando >= inicio) and treino_id in ids_treinos:
            feitos[treino_id] = quando  # fica com a mais recente

    return {
        "modo": modo,
        "dia_reinicio": dia,
        "descricao": descrever(modo, dia),
        "inicio": inicio.isoformat() if inicio else None,
        "proximo_reinicio": proximo_reinicio.isoformat() if proximo_reinicio else None,
        "feitos": {tid: q.isoformat() for tid, q in feitos.items()},
        "total": len(ids_treinos),
        "total_feitos": len(feitos),
    }


def descrever(modo: str, dia: int) -> str:
    if modo == "semanal":
        return f"Os treinos reiniciam {'todo' if dia >= 5 else 'toda'} {DIAS[dia]}."
    if modo == "ao_completar":
        return "Os treinos reiniciam no dia seguinte a completar todos."
    return "O professor reinicia os treinos quando achar melhor."
