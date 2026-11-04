"""Catálogo inicial de exercícios com instruções de uso dos aparelhos.

O professor pode editar, apagar ou cadastrar novos pelo app.
"""

EXERCICIOS = [
    # ---------------- PEITO ----------------
    {
        "nome": "Supino reto com barra",
        "grupo_muscular": "Peito",
        "aparelho": "Banco de supino reto",
        "como_usar": (
            "1. Deite no banco com os olhos logo abaixo da barra.\n"
            "2. Pés firmes no chão e escápulas (ombros) encaixadas para trás.\n"
            "3. Segure a barra um pouco mais aberto que a largura dos ombros.\n"
            "4. Tire a barra do suporte e desça controlando até perto do peito.\n"
            "5. Empurre a barra para cima até quase estender os cotovelos."
        ),
        "dicas": (
            "Não tire o quadril do banco. Não deixe a barra quicar no peito. "
            "Use um parceiro ou o professor para auxiliar em cargas altas."
        ),
    },
    {
        "nome": "Supino inclinado com halteres",
        "grupo_muscular": "Peito",
        "aparelho": "Banco inclinado + halteres",
        "como_usar": (
            "1. Ajuste o encosto do banco entre 30° e 45°.\n"
            "2. Sente com os halteres apoiados nas coxas e deite levando-os junto ao peito.\n"
            "3. Comece com os braços estendidos acima do peito.\n"
            "4. Desça os halteres abrindo os cotovelos até a linha do peito.\n"
            "5. Suba juntando os halteres no alto, sem bater um no outro."
        ),
        "dicas": "Mantenha os punhos retos. Inclinação maior que 45° trabalha mais o ombro do que o peito.",
    },
    {
        "nome": "Crucifixo na máquina (voador / peck deck)",
        "grupo_muscular": "Peito",
        "aparelho": "Peck deck (voador)",
        "como_usar": (
            "1. Regule a altura do banco para que as pegadas fiquem na linha do peito.\n"
            "2. Ajuste a amplitude para que os braços comecem levemente atrás do corpo.\n"
            "3. Encoste bem as costas no encosto.\n"
            "4. Junte as pegadas à frente do peito, com os cotovelos levemente flexionados.\n"
            "5. Volte devagar até a posição inicial."
        ),
        "dicas": "Não deixe o peso bater no final da volta. O movimento é dos braços, não projete o tronco.",
    },
    # ---------------- COSTAS ----------------
    {
        "nome": "Puxada frontal (pulldown)",
        "grupo_muscular": "Costas",
        "aparelho": "Polia alta (pulley)",
        "como_usar": (
            "1. Ajuste o apoio das coxas para que fiquem bem presas.\n"
            "2. Segure a barra com pegada aberta, palmas para frente.\n"
            "3. Sente com o tronco levemente inclinado para trás.\n"
            "4. Puxe a barra até a parte de cima do peito, levando os cotovelos para baixo.\n"
            "5. Suba a barra devagar até estender os braços."
        ),
        "dicas": "Nunca puxe a barra atrás da nuca. Evite balançar o tronco para ajudar o movimento.",
    },
    {
        "nome": "Remada baixa sentada",
        "grupo_muscular": "Costas",
        "aparelho": "Polia baixa / remada sentada",
        "como_usar": (
            "1. Sente com os pés apoiados na plataforma e joelhos levemente dobrados.\n"
            "2. Segure o triângulo (ou pegada) com os braços estendidos.\n"
            "3. Coluna reta, peito aberto.\n"
            "4. Puxe a pegada em direção ao abdômen, juntando as escápulas.\n"
            "5. Volte controlando, sem arredondar as costas."
        ),
        "dicas": "Não jogue o tronco para trás para puxar. Cotovelos passam rente ao corpo.",
    },
    {
        "nome": "Remada curvada com barra",
        "grupo_muscular": "Costas",
        "aparelho": "Barra livre",
        "como_usar": (
            "1. Em pé, pés na largura do quadril, segure a barra com as mãos na largura dos ombros.\n"
            "2. Dobre levemente os joelhos e incline o tronco à frente (cerca de 45°), coluna reta.\n"
            "3. Puxe a barra em direção ao umbigo.\n"
            "4. Desça a barra devagar até estender os braços."
        ),
        "dicas": "Mantenha o abdômen contraído e a coluna neutra o tempo todo. Comece com carga leve.",
    },
    # ---------------- PERNAS ----------------
    {
        "nome": "Leg press 45°",
        "grupo_muscular": "Pernas",
        "aparelho": "Leg press 45°",
        "como_usar": (
            "1. Sente com as costas e o quadril totalmente apoiados no encosto.\n"
            "2. Pés na plataforma, afastados na largura do quadril.\n"
            "3. Empurre a plataforma e solte as travas de segurança.\n"
            "4. Desça dobrando os joelhos até cerca de 90°.\n"
            "5. Empurre de volta sem travar totalmente os joelhos.\n"
            "6. Ao terminar, recoloque as travas antes de sair."
        ),
        "dicas": "Não deixe o quadril sair do banco na descida. Joelhos alinhados com a ponta dos pés.",
    },
    {
        "nome": "Cadeira extensora",
        "grupo_muscular": "Pernas",
        "aparelho": "Cadeira extensora",
        "como_usar": (
            "1. Ajuste o encosto para que o joelho fique alinhado com o eixo da máquina.\n"
            "2. Ajuste o rolo para ficar na parte de baixo da canela, acima do tornozelo.\n"
            "3. Segure as pegadas laterais.\n"
            "4. Estenda as pernas até ficarem retas.\n"
            "5. Desça devagar até a posição inicial."
        ),
        "dicas": "Evite chutar o peso. Segure 1 segundo no alto para melhor contração.",
    },
    {
        "nome": "Mesa flexora",
        "grupo_muscular": "Pernas",
        "aparelho": "Mesa flexora",
        "como_usar": (
            "1. Deite de bruços com o joelho logo após a borda do banco.\n"
            "2. Ajuste o rolo para ficar acima do calcanhar.\n"
            "3. Segure as pegadas e mantenha o quadril colado no banco.\n"
            "4. Dobre os joelhos trazendo o rolo em direção ao glúteo.\n"
            "5. Volte devagar."
        ),
        "dicas": "Se o quadril levantar, a carga está alta demais.",
    },
    {
        "nome": "Agachamento livre",
        "grupo_muscular": "Pernas",
        "aparelho": "Barra + rack (gaiola)",
        "como_usar": (
            "1. Ajuste o suporte da barra na altura do peito.\n"
            "2. Posicione a barra sobre o trapézio (parte de cima das costas), não no pescoço.\n"
            "3. Pés um pouco mais afastados que o quadril, pontas levemente para fora.\n"
            "4. Desça levando o quadril para trás e para baixo, peito aberto.\n"
            "5. Suba empurrando o chão com o pé inteiro."
        ),
        "dicas": (
            "Joelhos acompanham a direção dos pés, sem cair para dentro. "
            "Ajuste as travas de segurança do rack um pouco abaixo da sua profundidade."
        ),
    },
    {
        "nome": "Cadeira abdutora",
        "grupo_muscular": "Pernas",
        "aparelho": "Cadeira abdutora",
        "como_usar": (
            "1. Sente com as costas apoiadas e as pernas por dentro das almofadas.\n"
            "2. Ajuste a abertura inicial com as pernas juntas.\n"
            "3. Abra as pernas empurrando as almofadas para fora.\n"
            "4. Volte devagar sem deixar o peso bater."
        ),
        "dicas": "Mantenha o quadril parado no banco. Trabalha principalmente o glúteo médio.",
    },
    {
        "nome": "Panturrilha em pé",
        "grupo_muscular": "Pernas",
        "aparelho": "Máquina de panturrilha (gêmeos)",
        "como_usar": (
            "1. Encaixe os ombros sob as almofadas.\n"
            "2. Apoie só a ponta dos pés na plataforma, calcanhares para fora.\n"
            "3. Desça os calcanhares alongando a panturrilha.\n"
            "4. Suba o máximo possível na ponta dos pés.\n"
            "5. Repita devagar."
        ),
        "dicas": "Use toda a amplitude do movimento. Não dobre os joelhos para ajudar.",
    },
    # ---------------- OMBROS ----------------
    {
        "nome": "Desenvolvimento com halteres",
        "grupo_muscular": "Ombros",
        "aparelho": "Banco com encosto + halteres",
        "como_usar": (
            "1. Ajuste o encosto do banco a 90° (reto).\n"
            "2. Sente e leve os halteres na altura das orelhas, palmas para frente.\n"
            "3. Empurre os halteres para cima até quase estender os braços.\n"
            "4. Desça devagar até a altura das orelhas."
        ),
        "dicas": "Não arqueie a lombar. Mantenha o abdômen firme.",
    },
    {
        "nome": "Elevação lateral",
        "grupo_muscular": "Ombros",
        "aparelho": "Halteres",
        "como_usar": (
            "1. Em pé, halteres ao lado do corpo, cotovelos levemente dobrados.\n"
            "2. Eleve os braços para os lados até a altura dos ombros.\n"
            "3. Desça devagar."
        ),
        "dicas": "Use carga leve. Não balance o corpo e não suba acima da linha dos ombros.",
    },
    # ---------------- BÍCEPS ----------------
    {
        "nome": "Rosca direta com barra",
        "grupo_muscular": "Bíceps",
        "aparelho": "Barra reta ou W",
        "como_usar": (
            "1. Em pé, segure a barra com as palmas para frente, mãos na largura dos ombros.\n"
            "2. Cotovelos colados ao corpo.\n"
            "3. Dobre os cotovelos levando a barra até a altura do peito.\n"
            "4. Desça devagar até estender os braços."
        ),
        "dicas": "Não jogue o corpo para trás. Se precisar balançar, diminua a carga.",
    },
    {
        "nome": "Rosca alternada com halteres",
        "grupo_muscular": "Bíceps",
        "aparelho": "Halteres",
        "como_usar": (
            "1. Em pé ou sentado, halteres ao lado do corpo.\n"
            "2. Suba um halter de cada vez, girando a palma para cima durante a subida.\n"
            "3. Desça devagar e troque de braço."
        ),
        "dicas": "Cotovelo parado ao lado do corpo durante todo o movimento.",
    },
    # ---------------- TRÍCEPS ----------------
    {
        "nome": "Tríceps na polia (pulley)",
        "grupo_muscular": "Tríceps",
        "aparelho": "Polia alta com barra ou corda",
        "como_usar": (
            "1. De frente para a polia, segure a barra/corda com os cotovelos dobrados.\n"
            "2. Cotovelos colados ao corpo, tronco levemente inclinado à frente.\n"
            "3. Empurre para baixo até estender os braços.\n"
            "4. Volte até a altura do peito sem mexer os cotovelos."
        ),
        "dicas": "Só o antebraço se move. Com corda, abra as pontas no final do movimento.",
    },
    {
        "nome": "Tríceps francês com halter",
        "grupo_muscular": "Tríceps",
        "aparelho": "Halter + banco",
        "como_usar": (
            "1. Sentado, segure um halter com as duas mãos acima da cabeça.\n"
            "2. Desça o halter atrás da cabeça dobrando os cotovelos.\n"
            "3. Estenda os braços de volta para cima."
        ),
        "dicas": "Cotovelos apontados para frente/cima, sem abrir muito. Cuidado com a cabeça.",
    },
    # ---------------- ABDÔMEN ----------------
    {
        "nome": "Abdominal supra",
        "grupo_muscular": "Abdômen",
        "aparelho": "Colchonete",
        "como_usar": (
            "1. Deite de barriga para cima com os joelhos dobrados e pés no chão.\n"
            "2. Mãos atrás da cabeça ou cruzadas no peito.\n"
            "3. Suba o tronco tirando as escápulas do chão.\n"
            "4. Desça devagar."
        ),
        "dicas": "Não puxe o pescoço com as mãos. Solte o ar na subida.",
    },
    {
        "nome": "Prancha",
        "grupo_muscular": "Abdômen",
        "aparelho": "Colchonete",
        "como_usar": (
            "1. Apoie os antebraços no chão, cotovelos abaixo dos ombros.\n"
            "2. Estique as pernas apoiando a ponta dos pés.\n"
            "3. Mantenha o corpo reto, da cabeça aos calcanhares.\n"
            "4. Segure a posição pelo tempo indicado."
        ),
        "dicas": "Não deixe o quadril cair nem subir demais. Respire normalmente.",
    },
    # ---------------- CARDIO ----------------
    {
        "nome": "Esteira",
        "grupo_muscular": "Cardio",
        "aparelho": "Esteira",
        "como_usar": (
            "1. Suba com os pés nas laterais (fora da lona).\n"
            "2. Prenda a chave de segurança na roupa.\n"
            "3. Ligue em velocidade baixa e só então pise na lona.\n"
            "4. Aumente a velocidade/inclinação aos poucos.\n"
            "5. Para parar, reduza a velocidade antes de descer."
        ),
        "dicas": "Não segure no painel durante a corrida. Olhe para frente.",
    },
    {
        "nome": "Bicicleta ergométrica",
        "grupo_muscular": "Cardio",
        "aparelho": "Bicicleta ergométrica",
        "como_usar": (
            "1. Ajuste o banco na altura do quadril (em pé ao lado da bike).\n"
            "2. Sente e confira: com o pedal embaixo, o joelho fica levemente dobrado.\n"
            "3. Comece com carga leve e aumente aos poucos."
        ),
        "dicas": "Banco muito baixo força o joelho. Mantenha as costas retas.",
    },
]
