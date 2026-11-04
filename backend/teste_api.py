"""Teste rápido do fluxo completo usando um banco temporário.

Rodar:  .venv\\Scripts\\python teste_api.py
Para testar a atualização de um banco antigo:  .venv\\Scripts\\python teste_api.py caminho\\do\\banco_antigo.db
"""
import os
import shutil
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")
pasta = tempfile.mkdtemp()
os.environ["ESPORTFIT_DB"] = os.path.join(pasta, "teste.db")
banco_antigo = sys.argv[1] if len(sys.argv) > 1 else None
if banco_antigo:
    shutil.copy(banco_antigo, os.environ["ESPORTFIT_DB"])

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

with TestClient(app) as c:
    # Professor inicial faz login
    r = c.post("/auth/login", json={"email": "professor@esportfit.com", "senha": "esport123"})
    assert r.status_code == 200, r.text
    prof = {"Authorization": f"Bearer {r.json()['token']}"}
    assert r.json()["usuario"]["cargo"] == "professor"

    # Aluno cria conta pelo app
    email_aluno = f"maria{os.getpid()}@email.com"
    r = c.post("/auth/cadastro", json={"nome": "Maria", "email": email_aluno.upper(), "senha": "123456"})
    assert r.status_code == 200, r.text
    aluno = {"Authorization": f"Bearer {r.json()['token']}"}
    aluno_id = r.json()["usuario"]["id"]
    assert r.json()["usuario"]["cargo"] == "aluno"

    # E-mail repetido é recusado; senha errada também
    assert c.post("/auth/cadastro", json={"nome": "Outra Maria", "email": email_aluno, "senha": "123456"}).status_code == 409
    assert c.post("/auth/login", json={"email": email_aluno, "senha": "errada"}).status_code == 401

    # Aluno não pode montar treino nem listar alunos
    assert c.get("/alunos", headers=aluno).status_code == 403
    assert c.get("/meus-treinos/indicado", headers=aluno).json() is None

    # ---------- Catálogo ----------
    exercicios = c.get("/exercicios", headers=prof).json()
    print(f"catálogo: {len(exercicios)} exercícios")
    assert len(exercicios) >= 22
    e = {x["nome"]: x["id"] for x in exercicios}
    assert all(x["imagem"] for x in exercicios if x["nome"] in ("Leg press 45°", "Supino reto com barra"))

    # Busca sem acento e por nome em inglês
    assert any(x["nome"] == "Tríceps na polia (pulley)" for x in c.get("/exercicios?q=triceps polia", headers=prof).json())
    assert any(x["nome"] == "Leg press 45°" for x in c.get("/exercicios?q=leg press", headers=prof).json())
    assert any(x["nome"] == "Supino reto com barra" for x in c.get("/exercicios?q=bench press", headers=prof).json())

    detalhe = c.get(f"/exercicios/{e['Leg press 45°']}", headers=prof).json()
    assert len(detalhe["imagens"]) == 2 and detalhe["imagens"][0].startswith("https://")

    # ---------- Favoritos: aparecem primeiro, e são de cada usuário ----------
    fav_id = e["Prancha"]
    assert c.put(f"/exercicios/{fav_id}/favorito", headers=prof).json() == {"favorito": True}
    lista = c.get("/exercicios", headers=prof).json()
    assert lista[0]["id"] == fav_id and lista[0]["favorito"]
    assert not c.get("/exercicios", headers=aluno).json()[0]["favorito"]  # aluno não vê os favoritos do professor
    c.delete(f"/exercicios/{fav_id}/favorito", headers=prof)
    assert not next(x for x in c.get("/exercicios", headers=prof).json() if x["id"] == fav_id)["favorito"]
    c.put(f"/exercicios/{fav_id}/favorito", headers=prof)

    # ---------- Vídeo enviado pelo professor ----------
    lp = e["Leg press 45°"]
    falso_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"0" * 1000
    assert c.post(f"/exercicios/{lp}/video", headers=aluno, files={"arquivo": ("v.mp4", falso_mp4, "video/mp4")}).status_code == 403
    r = c.post(f"/exercicios/{lp}/video", headers=prof, files={"arquivo": ("v.mp4", falso_mp4, "video/mp4")})
    assert r.status_code == 200, r.text
    video = r.json()["video"]
    assert video.startswith("/midia/videos/")
    assert c.get(video).status_code == 200
    assert c.post(f"/exercicios/{lp}/video", headers=prof, files={"arquivo": ("x.txt", b"oi", "text/plain")}).status_code == 400

    # ---------- Professor monta Treino A e Treino B ----------
    for nome, ordem, lista in [
        ("Treino A - Peito e Tríceps", 1, ["Supino reto com barra", "Tríceps na polia (pulley)"]),
        ("Treino B - Pernas", 2, ["Leg press 45°", "Cadeira extensora"]),
    ]:
        r = c.post("/treinos", headers=prof, json={
            "aluno_id": aluno_id, "nome": nome, "ordem": ordem,
            "itens": [{"exercicio_id": e[n], "series": 3, "repeticoes": "10-12"} for n in lista],
        })
        assert r.status_code == 200, r.text
    assert c.post("/treinos", headers=aluno, json={"aluno_id": aluno_id, "nome": "x", "itens": [
        {"exercicio_id": 1, "series": 3, "repeticoes": "10"}]}).status_code == 403

    # Aluno vê o treino indicado com instruções, fotos e vídeo do aparelho
    t = c.get("/meus-treinos/indicado", headers=aluno).json()
    assert t["nome"].startswith("Treino A"), t["nome"]
    assert "Deite no banco" in t["itens"][0]["como_usar"]
    assert len(t["itens"][0]["imagens"]) == 2

    # Descanso padrão = 2 minutos
    assert t["itens"][0]["descanso_seg"] == 120

    # Lista na ordem, nada feito ainda
    semana = c.get("/meus-treinos/semana", headers=aluno).json()
    assert [x["nome"][:8] for x in semana["treinos"]] == ["Treino A", "Treino B"]
    assert not any(x["feito"] for x in semana["treinos"]) and semana["treinos"][0]["proximo"]
    assert semana["ciclo"]["modo"] == "semanal" and "segunda" in semana["ciclo"]["descricao"]

    # Conclui A -> A fica feito, B é o próximo (com o vídeo do leg press)
    r = c.post(f"/treinos/{t['id']}/concluir", headers=aluno).json()
    assert r["proximo"]["nome"].startswith("Treino B")
    assert r["proximo"]["itens"][0]["video"] == video
    semana = c.get("/meus-treinos/semana", headers=aluno).json()
    assert semana["treinos"][0]["feito"] and semana["treinos"][0]["feito_em"]
    assert semana["treinos"][1]["proximo"]

    # Refazer A: não é bloqueado, continua feito
    assert c.post(f"/treinos/{t['id']}/concluir", headers=aluno).status_code == 200
    assert c.get(f"/treinos/{t['id']}", headers=aluno).json()["feito"]

    # Conclui B -> todos feitos
    r = c.post(f"/treinos/{r['proximo']['id']}/concluir", headers=aluno).json()
    assert r["todos_feitos"] and r["proximo"] is None
    assert c.get("/meus-treinos/semana", headers=aluno).json()["ciclo"]["total_feitos"] == 2

    # ---------- Reinício ----------
    import ciclo as ciclo_mod
    from datetime import timedelta
    from db import conectar as _conectar

    ids_treinos = [x["id"] for x in semana["treinos"]]

    def feitos_em(dias_depois):
        con = _conectar()
        try:
            return ciclo_mod.calcular(con, aluno_id, ids_treinos, ciclo_mod.agora() + timedelta(days=dias_depois))["total_feitos"]
        finally:
            con.close()

    # Semanal: daqui a 8 dias com certeza passou o dia de reinício
    assert feitos_em(0) == 2 and feitos_em(8) == 0

    # Ao completar: hoje continua tudo feito; amanhã recomeça
    c.put(f"/alunos/{aluno_id}/reinicio", headers=prof, json={"modo": "ao_completar"})
    assert feitos_em(0) == 2 and feitos_em(1) == 0

    # Manual: nunca reinicia sozinho...
    s = c.put(f"/alunos/{aluno_id}/reinicio", headers=prof, json={"modo": "manual"}).json()
    assert "professor" in s["ciclo"]["descricao"]
    assert feitos_em(30) == 2
    # ...até o professor clicar em "Reiniciar agora"
    assert c.post(f"/alunos/{aluno_id}/reiniciar", headers=aluno).status_code == 403
    s = c.post(f"/alunos/{aluno_id}/reiniciar", headers=prof).json()
    assert s["ciclo"]["total_feitos"] == 0 and s["treinos"][0]["proximo"]

    # Aplicar regra a todos os alunos
    r = c.put("/alunos/reinicio", headers=prof, json={"modo": "semanal", "dia_reinicio": 6}).json()
    assert r["alunos_atualizados"] >= 1 and "todo domingo" in r["descricao"]

    # Professor vê alunos e treinos
    alunos = {a["id"]: a for a in c.get("/alunos", headers=prof).json()}
    assert alunos[aluno_id]["total_treinos"] == 2 and "total_feitos" in alunos[aluno_id]
    assert len(c.get(f"/alunos/{aluno_id}/treinos", headers=prof).json()) == 2

    # Edição do professor é preservada quando o catálogo sincroniza de novo
    ext = c.get(f"/exercicios/{e['Cadeira extensora']}", headers=prof).json()
    ext["dicas"] = "Banco na posição 5 nesta academia."
    assert c.put(f"/exercicios/{ext['id']}", headers=prof, json=ext).status_code == 200
    from db import conectar, sincronizar_catalogo
    con = conectar()
    with con:
        sincronizar_catalogo(con)
    con.close()
    assert c.get(f"/exercicios/{ext['id']}", headers=prof).json()["dicas"] == "Banco na posição 5 nesta academia."

    # Exercício do catálogo não pode ser apagado; um criado pelo professor pode
    assert c.delete(f"/exercicios/{lp}", headers=prof).status_code == 409
    novo = c.post("/exercicios", headers=prof, json={
        "nome": "Máquina exclusiva Esport", "grupo_muscular": "Costas", "aparelho": "Remada articulada nova",
        "como_usar": "1. Ajuste o banco.\n2. Puxe.",
    }).json()
    assert c.delete(f"/exercicios/{novo['id']}", headers=prof).status_code == 204

    # Remover vídeo
    assert c.delete(f"/exercicios/{lp}/video", headers=prof).json()["video"] is None
    assert c.get(video).status_code == 404

    # Sem token -> 401
    assert c.get("/meus-treinos").status_code == 401

print("OK - todos os testes passaram")
