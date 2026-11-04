# Esport Fit — app de treinos

App de celular da academia **Esport Fit**: o professor monta o treino de cada aluno, e o aluno abre o app, toca no **play** e vê o treino indicado do dia, com animação, vídeo e passo a passo de cada aparelho.

```
Gym/
├── backend/   → servidor (Python + FastAPI + SQLite): login, cargos, exercícios, vídeos, treinos
└── mobile/    → app (React Native + Expo): roda no Android e no iPhone
```

## Como funciona

**Abrindo o app**
1. **Login** (só na primeira vez — depois fica salvo no celular por 1 ano, mesmo sem internet).
2. Tela com a **logo e o botão de play**.
3. Play → aluno vai para o treino do dia; professor vai para o painel.

**Aluno**
- O play abre a lista **Seus treinos**, na ordem (A, B, C…), com o próximo destacado.
- Treino concluído fica **meio transparente com ✓** e a data. Não fica bloqueado: o botão **↻ Refazer** abre de novo.
- Os treinos voltam a ficar pendentes conforme a regra que o professor escolheu (padrão: toda segunda-feira).
- Cada exercício mostra séries × repetições, carga, descanso (padrão 2 min) e a observação do professor.
- **Animação do movimento** aparece direto no cartão (as fotos de início e fim alternando, como um GIF).
- **🎬 Ver vídeo do aparelho** — quando o professor gravou um vídeo daquele aparelho.
- **📋 Como fazer** — passo a passo e cuidados. **⏱ Descansar** — cronômetro.
- Marca os feitos e toca em **Concluir treino** → o app passa a indicar o próximo.

**Professor**
- Lista de alunos; monta, edita e apaga os treinos de cada um, e vê quais já foram feitos.
- **Reinício dos treinos** (na ficha de cada aluno): *Toda semana* (escolhe o dia), *Quando fizer todos* (recomeça no dia seguinte) ou *Só quando eu reiniciar*. Tem **Reiniciar agora** e **Aplicar a todos os alunos**. O histórico nunca é apagado.
- **Catálogo com ~870 exercícios** (máquinas, polia, barra, halteres, kettlebell, peso corporal, alongamentos, cardio…).
  - Busca por nome sem precisar de acento (e também pelo nome em inglês).
  - Filtros por grupo muscular, equipamento e tipo.
  - **☆ Favoritos**: cada professor tem os seus, e eles aparecem sempre primeiro.
  - Toque no exercício para ver a animação e o passo a passo antes de adicionar; **+** adiciona direto.
- **Gravar vídeo do aparelho**: em Exercícios → abra um exercício → **🎥 Gravar agora** (ou **📁 Da galeria**). O vídeo aparece para todos os alunos que têm esse exercício no treino.
- Pode editar o texto de qualquer exercício e cadastrar exercícios novos (ex.: uma máquina específica da academia).
- Cadastra alunos e outros professores.

> Qualquer pessoa que cria conta pelo app vira **aluno**. Professor só pode ser cadastrado por outro professor.

**Primeiro professor (criado automaticamente):** `professor@esportfit.com` / `esport123` — troque antes de usar de verdade.

---

## Rodando no seu computador

### 1. Servidor (backend)

```powershell
cd backend
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Documentação interativa da API: http://localhost:8000/docs
- Teste automático do fluxo completo: `.venv\Scripts\python teste_api.py`
- Se o Windows perguntar sobre o firewall, **permita** em redes privadas (o celular precisa acessar o PC).

Se a pasta `.venv` não existir (ex.: em outro computador):
```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. App (mobile)

Em outro terminal:
```powershell
cd mobile
npx expo start
```

- **No celular:** instale o **Expo Go** (Play Store / App Store), conecte no **mesmo Wi-Fi** do computador e leia o QR code.
- **No navegador (teste rápido):** aperte `w` no terminal do Expo. (Gravar vídeo pela câmera só funciona no celular.)

O app encontra o servidor sozinho (usa o IP do computador que está rodando o Expo, porta 8000). O endereço aparece no rodapé da tela de login.

---

## De onde vêm os exercícios e as imagens

- **Free Exercise DB** — https://github.com/yuhonas/free-exercise-db — **domínio público** (Unlicense): pode ser usado no app comercialmente, sem custo. Cada exercício tem 2 fotos (posição inicial e final), que o app anima.
- **Nomes**: traduzidos para o português à mão (`backend/catalogo/nomes_pt_*.json`).
- **Passo a passo**: os 22 exercícios mais comuns foram escritos à mão; os demais foram traduzidos automaticamente (o app avisa isso) e o professor pode revisar qualquer um pelo app — a versão dele passa a valer e não é sobrescrita.
- **Vídeos**: gravados pelo professor no próprio app (ficam em `backend/midia/videos/`). Vídeo do aparelho real da academia é o mais claro para o aluno. Se quiser usar vídeos feitos em outro lugar (inclusive gerados por IA), é só enviar pelo botão **📁 Da galeria**.
- As fotos hoje são carregadas direto do GitHub. Antes de publicar, o ideal é copiá-las para o seu servidor.

Para regenerar o catálogo (as traduções ficam em `backend/catalogo/traducoes/`):
```powershell
cd backend\catalogo
python gerar_catalogo.py traducoes\free.json traducoes\instrucoes_pt.json traducoes\instr_a.json traducoes\instr_b.json
```
O servidor sincroniza o catálogo sozinho ao iniciar (sem apagar edições do professor nem treinos).

---

## Design

Visual escuro com a identidade da academia: preto + vermelho `#ef233c`, cantos retos, rótulos técnicos `[ 01 · TREINO ]`.

- **Fontes:** Manrope (títulos), Inter (textos), JetBrains Mono (rótulos e números).
- **Ícones:** Lucide (`lucide-react-native`).
- **Animações:** entrada suave das telas e listas, botão de play com feixe girando e pulso, gavetas com seta animada, cronômetro de descanso que vibra no fim.
- **Tudo fica em** [mobile/src/components/ui.js](mobile/src/components/ui.js): cores (`cores`), fontes (`fontes`) e componentes (`Botao`, `Campo`, `Cartao`, `Gaveta`, `Chip`, `Tag`, `Rotulo`, `Entrada`...). Mudando ali, muda o app todo.
- **Logo e ícone do app:** `mobile/assets/` — `logo.png` (telas), `icon.png` (iPhone), `android-icon-*.png` (Android), `splash-icon.png` (abertura), `favicon.png` (web).
  O ícone e a tela de abertura só aparecem no app instalado (no Expo Go aparece o ícone do Expo).

> Se uma mudança no código não aparecer no celular, pare o Expo e rode `npx expo start --clear` (a pasta no OneDrive às vezes atrapalha o recarregamento automático).

## Configurações

| O quê | Como |
|---|---|
| E-mail/senha do primeiro professor | Antes de rodar o servidor pela primeira vez: `$env:PROFESSOR_EMAIL="..."; $env:PROFESSOR_SENHA="..."`. |
| Servidor na nuvem | Crie `mobile/.env` com `EXPO_PUBLIC_API_URL=https://seu-servidor.com` |
| Chave dos logins | Gerada sozinha em `backend/.chave_secreta`. Em produção, defina `ESPORTFIT_CHAVE`. |

## Próximos passos (quando for publicar)

1. **Colocar o servidor na internet** (Render, Railway, uma VPS…), com HTTPS e armazenamento para os vídeos.
2. **Copiar as fotos dos exercícios** para o servidor (hoje vêm do GitHub).
3. **Gerar o app** para as lojas com o EAS: `npx eas-cli@latest build -p android` (é aí que o ícone e a tela de abertura com a logo aparecem).
4. Ideias: histórico de cargas, recuperação de senha, avaliação física.

## Estrutura do código

**backend/**
- `main.py` — todas as rotas da API (login, alunos, exercícios, favoritos, vídeos, treinos)
- `db.py` — tabelas, atualização de bancos antigos e sincronização do catálogo
- `ciclo.py` — regra de reinício (quais treinos estão feitos no ciclo atual)
- `seguranca.py` — senhas (PBKDF2), tokens de login (JWT) e regra de cargo
- `catalogo/` — `exercicios.json` (catálogo pronto), nomes traduzidos e o gerador
- `seed_exercicios.py` — os 22 exercícios com texto escrito à mão
- `teste_api.py` — teste do fluxo completo

**mobile/src/**
- `app/login.js` — primeira tela (entrar / criar conta)
- `app/index.js` — logo + play
- `app/treino.js` — treino do aluno · `app/meus-treinos.js` — todos os treinos
- `app/professor/` — painel, ficha do aluno, montar treino, exercícios, editar exercício/gravar vídeo, cadastrar pessoa
- `components/ListaExercicios.js` — busca, filtros e favoritos
- `components/midia.js` — animação do exercício, miniatura e player de vídeo
- `components/ItemExercicio.js` · `components/PreviaExercicio.js` · `components/ui.js`
- `lib/` — conexão com a API, envio de arquivos e login salvo
#   G y m  
 