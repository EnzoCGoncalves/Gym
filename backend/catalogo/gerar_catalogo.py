"""Gera catalogo/exercicios.json a partir do Free Exercise DB (domínio público).

Fonte: https://github.com/yuhonas/free-exercise-db  (licença Unlicense)
  - nomes traduzidos à mão:       nomes_pt_*.json
  - passo a passo:                tradução automática (Argos Translate) + glossário abaixo
  - 22 exercícios revisados:      seed_exercicios.py (texto escrito à mão, substitui a versão traduzida)

Uso (só precisa rodar de novo se quiser regenerar o catálogo):
  python gerar_catalogo.py <free.json> <instrucoes_pt.json> [mais_instrucoes.json ...]
"""
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))
from seed_exercicios import EXERCICIOS as REVISADOS  # noqa: E402

URL_IMAGENS = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"

GRUPOS = {
    "abdominals": "Abdômen", "hamstrings": "Posterior de coxa", "quadriceps": "Quadríceps",
    "glutes": "Glúteos", "calves": "Panturrilha", "adductors": "Adutores", "abductors": "Abdutores",
    "chest": "Peito", "lats": "Costas", "middle back": "Costas", "lower back": "Lombar",
    "traps": "Trapézio", "shoulders": "Ombros", "biceps": "Bíceps", "triceps": "Tríceps",
    "forearms": "Antebraço", "neck": "Pescoço",
}
EQUIPAMENTOS = {
    "barbell": "Barra", "dumbbell": "Halteres", "other": "Outros", "body only": "Peso corporal",
    "cable": "Polia (cabo)", "machine": "Máquina", "kettlebells": "Kettlebell", "bands": "Elástico",
    "medicine ball": "Medicine ball", "exercise ball": "Bola suíça", "foam roll": "Rolo de liberação",
    "e-z curl bar": "Barra W", None: "Outros",
}
CATEGORIAS = {
    "strength": "Força", "stretching": "Alongamento", "plyometrics": "Pliometria",
    "powerlifting": "Powerlifting", "olympic weightlifting": "Levantamento olímpico", "cardio": "Cardio",
}
NIVEIS = {"beginner": "Iniciante", "intermediate": "Intermediário", "expert": "Avançado"}

# Exercícios revisados à mão -> exercício equivalente no Free Exercise DB (para usar as fotos)
REVISADO_PARA_ID = {
    "Supino reto com barra": "Barbell_Bench_Press_-_Medium_Grip",
    "Supino inclinado com halteres": "Incline_Dumbbell_Press",
    "Crucifixo na máquina (voador / peck deck)": "Butterfly",
    "Puxada frontal (pulldown)": "Wide-Grip_Lat_Pulldown",
    "Remada baixa sentada": "Seated_Cable_Rows",
    "Remada curvada com barra": "Bent_Over_Barbell_Row",
    "Leg press 45°": "Leg_Press",
    "Cadeira extensora": "Leg_Extensions",
    "Mesa flexora": "Lying_Leg_Curls",
    "Agachamento livre": "Barbell_Squat",
    "Cadeira abdutora": "Thigh_Abductor",
    "Panturrilha em pé": "Standing_Calf_Raises",
    "Desenvolvimento com halteres": "Dumbbell_Shoulder_Press",
    "Elevação lateral": "Side_Lateral_Raise",
    "Rosca direta com barra": "Barbell_Curl",
    "Rosca alternada com halteres": "Dumbbell_Alternate_Bicep_Curl",
    "Tríceps na polia (pulley)": "Triceps_Pushdown",
    "Tríceps francês com halter": "Seated_Triceps_Press",
    "Abdominal supra": "Crunches",
    "Prancha": "Plank",
    "Esteira": "Walking_Treadmill",
    "Bicicleta ergométrica": "Bicycling_Stationary",
}

# Artigos/pronomes por gênero e número, para trocar palavras de gênero diferente sem erro de concordância
_DETERMINANTES = {
    # (masc, fem) singular e plural
    "s": [("o", "a"), ("um", "uma"), ("do", "da"), ("no", "na"), ("pelo", "pela"), ("este", "esta"),
          ("esse", "essa"), ("seu", "sua"), ("deste", "desta"), ("desse", "dessa"), ("ao", "à")],
    "p": [("os", "as"), ("uns", "umas"), ("dos", "das"), ("nos", "nas"), ("pelos", "pelas"), ("estes", "estas"),
          ("esses", "essas"), ("seus", "suas"), ("aos", "às")],
}


def _trocar_palavra(de, para, genero_de, genero_para, numero):
    """Gera regras que trocam 'de' por 'para' ajustando o artigo antes (ex.: 'da prateleira' -> 'do suporte')."""
    regras = []
    for masc, fem in _DETERMINANTES[numero]:
        art_de = masc if genero_de == "m" else fem
        art_para = masc if genero_para == "m" else fem
        regras.append((rf"\b{art_de} {de}\b", f"{art_para} {para}"))
    regras.append((rf"\b{de}\b", para))
    return regras


# Correções da tradução automática (regex -> substituição). Ordem importa.
GLOSSARIO = [
    *_trocar_palavra("campainhas", "barras", "f", "f", "p"), *_trocar_palavra("campainha", "barra", "f", "f", "s"),
    *_trocar_palavra("chaleiras", "kettlebells", "f", "m", "p"), *_trocar_palavra("chaleira", "kettlebell", "f", "m", "s"),
    *_trocar_palavra("bezerros", "panturrilhas", "m", "f", "p"), *_trocar_palavra("bezerro", "panturrilha", "m", "f", "s"),
    *_trocar_palavra("placas", "anilhas", "f", "f", "p"), *_trocar_palavra("placa", "anilha", "f", "f", "s"),
    *_trocar_palavra("prateleiras", "suportes", "f", "m", "p"), *_trocar_palavra("prateleira", "suporte", "f", "m", "s"),
    *_trocar_palavra("apertos", "pegadas", "m", "f", "p"), *_trocar_palavra("aperto", "pegada", "m", "f", "s"),
    *_trocar_palavra("aderência", "pegada", "f", "f", "s"),
    *_trocar_palavra("bandas", "elásticos", "f", "m", "p"), *_trocar_palavra("banda", "elástico", "f", "m", "s"),
    *_trocar_palavra("ancas", "quadris", "f", "m", "p"), *_trocar_palavra("anca", "quadril", "f", "m", "s"),
    *_trocar_palavra("omoplatas", "escápulas", "f", "f", "p"), *_trocar_palavra("omoplata", "escápula", "f", "f", "s"),
    *_trocar_palavra("bar", "barra", "m", "f", "s"),
    *_trocar_palavra("elevador", "movimento", "m", "m", "s"),
    *_trocar_palavra("esteira de exercício", "colchonete", "f", "m", "s"),
    *_trocar_palavra("tapete de exercício", "colchonete", "m", "m", "s"),
    *_trocar_palavra("tapete", "colchonete", "m", "m", "s"),
    (r"\bhaltere\b", "halter"), (r"\bdumbbells?\b", "halter"), (r"\bbarbells?\b", "barra"),
    (r"\brack agachamento\b", "rack de agachamento"),
    (r"\buma pega\b", "uma pegada"), (r"\bpega média\b", "pegada média"), (r"\bpega larga\b", "pegada aberta"),
    (r"\bpega estreita\b", "pegada fechada"),
    (r"\boverhand\b", "pronada"), (r"\bunderhand\b", "supinada"),
    (r"\benrole\b", "suba"), (r"\benrolar\b", "subir"), (r"\benrolando\b", "subindo"),
    (r"\blats\b", "dorsais"), (r"\bquads\b", "quadríceps"),
    (r"\bteus\b", "seus"), (r"\bteu\b", "seu"), (r"\btuas\b", "suas"), (r"\btua\b", "sua"),
    (r"Lentamente começar a trazer", "Lentamente, traga"),
    (r"\bcomo sua respiração\b", "enquanto inspira"),
    (r"Repetir para a quantidade recomendada de repetições\.?", "Repita pelo número de repetições indicado."),
    (r"Repita para a quantidade recomendada de repetições\.?", "Repita pelo número de repetições indicado."),
    (r"Repita o movimento para a quantidade prescrita de repetições\.?", "Repita pelo número de repetições indicado."),
    (r"Execute a quantidade de repetições prescritas no programa\.?", "Repita pelo número de repetições indicado."),
]


def _converter_medidas(texto: str) -> str:
    def pol(m):
        n = float(m.group(1).replace(",", "."))
        return f"{round(n * 2.54):g} cm"

    def pe(m):
        n = float(m.group(1).replace(",", "."))
        cm = n * 30.48
        return f"{round(cm):g} cm" if cm < 100 else f"{cm / 100:.1f} m".replace(".", ",")

    texto = re.sub(r"(\d+(?:[.,]\d+)?)\s*polegadas?\b", pol, texto)
    texto = re.sub(r"(\d+(?:[.,]\d+)?)\s*pés\b", pe, texto)
    return texto


def corrigir(texto: str) -> str:
    for padrao, novo in GLOSSARIO:
        def troca(m, novo=novo):
            original = m.group(0)
            return novo[0].upper() + novo[1:] if original[:1].isupper() else novo
        texto = re.sub(padrao, troca, texto, flags=re.IGNORECASE)
    return _converter_medidas(texto)


def main():
    free_path, *instr_paths = sys.argv[1:]
    free = json.load(open(free_path, encoding="utf-8"))
    por_id = {x["id"]: x for x in free}

    nomes = {}
    for p in sorted(AQUI.glob("nomes_pt_*.json")):
        nomes.update(json.load(open(p, encoding="utf-8")))
    instrucoes = {}
    for p in instr_paths:
        instrucoes.update(json.load(open(p, encoding="utf-8")))

    faltando = [i for i in REVISADO_PARA_ID.values() if i not in por_id]
    assert not faltando, f"IDs não encontrados no Free Exercise DB: {faltando}"

    saida = []

    def base(x):
        return {
            "codigo": x["id"],
            "nome_en": x["name"],
            "grupo_muscular": "Cardio" if x.get("category") == "cardio" else GRUPOS.get(x["primaryMuscles"][0], "Outros"),
            "musculos_secundarios": ", ".join(GRUPOS.get(m, m) for m in x.get("secondaryMuscles", [])),
            "equipamento": EQUIPAMENTOS.get(x.get("equipment"), "Outros"),
            "categoria": CATEGORIAS.get(x.get("category"), "Força"),
            "nivel": NIVEIS.get(x.get("level"), "Iniciante"),
            "imagens": [URL_IMAGENS + i for i in x.get("images", [])],
        }

    # 1) Revisados à mão (melhor texto)
    usados = set()
    for r in REVISADOS:
        x = por_id[REVISADO_PARA_ID[r["nome"]]]
        usados.add(x["id"])
        saida.append({
            **base(x),
            "nome": r["nome"],
            "aparelho": r["aparelho"],
            "como_usar": r["como_usar"],
            "dicas": r["dicas"],
            "traducao_automatica": 0,
        })

    # 2) Restante do banco (exceto strongman, pouco comum em academia)
    sem_traducao = []
    for x in free:
        if x["id"] in usados or x.get("category") == "strongman":
            continue
        passos = instrucoes.get(x["id"])
        if passos is None:
            # Sem tradução: entra com o texto original para não faltar no catálogo (o professor pode traduzir pelo app)
            sem_traducao.append(x["id"])
            passos = x["instructions"]
        else:
            passos = [corrigir(p) for p in passos]
        b = base(x)
        saida.append({
            **b,
            "nome": nomes.get(x["name"], x["name"]),
            "aparelho": b["equipamento"],
            "como_usar": "\n".join(f"{n}. {p.strip()}" for n, p in enumerate(passos, start=1)),
            "dicas": "",
            "traducao_automatica": 1,
        })

    destino = AQUI / "exercicios.json"
    json.dump(saida, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(saida)} exercícios gravados em {destino.name}; sem tradução: {len(sem_traducao)}")
    if sem_traducao:
        print("  ", sem_traducao[:20])


if __name__ == "__main__":
    main()
